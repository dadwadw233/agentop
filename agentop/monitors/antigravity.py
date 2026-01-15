"""Antigravity monitor module.

Monitors Antigravity/Gemini quota by calling Google Cloud Code API.
"""

from typing import Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import logging

from ..parsers.google_auth import GoogleAuthExtractor
from ..parsers.antigravity_quota_api import AntigravityQuotaAPI

logger = logging.getLogger(__name__)


@dataclass
class ModelQuota:
    """Quota information for a single model."""
    name: str
    percentage: int  # Remaining quota percentage (0-100)
    reset_time: str


@dataclass
class AntigravityMetrics:
    """Antigravity quota metrics."""
    
    # Authentication status
    is_authenticated: bool = False
    auth_error: Optional[str] = None
    
    # Subscription info
    subscription_tier: Optional[str] = None
    
    # Forbidden status
    is_forbidden: bool = False
    
    # Model quotas
    models: List[ModelQuota] = field(default_factory=list)
    
    # Last update time
    last_updated: Optional[datetime] = None


class AntigravityMonitor:
    """Monitor for Antigravity quota."""
    
    def __init__(self, cache_ttl_seconds: int = 60):
        """Initialize Antigravity monitor."""
        self.auth_extractor = GoogleAuthExtractor()
        self.api_client: Optional[AntigravityQuotaAPI] = None
        self._access_token: Optional[str] = None
        self.cache_ttl_seconds = max(10, cache_ttl_seconds)
        self._last_fetch: Optional[datetime] = None
        self._cached_metrics: Optional[AntigravityMetrics] = None
    
    def _initialize_auth(self) -> bool:
        """
        Initialize authentication.
        
        Returns:
            True if authenticated, False otherwise
        """
        access_token = self.auth_extractor.get_access_token()
        if not access_token:
            logger.warning("No access token found")
            return False

        if access_token != self._access_token:
            self._access_token = access_token
            self.api_client = AntigravityQuotaAPI(self._access_token)
            logger.info("Antigravity auth initialized")

        return True
    
    def get_metrics(self) -> AntigravityMetrics:
        """
        Get current Antigravity metrics.
        
        Returns:
            AntigravityMetrics object with current data
        """
        if self._cached_metrics and self._last_fetch:
            age = (datetime.now() - self._last_fetch).total_seconds()
            if age < self.cache_ttl_seconds:
                return self._cached_metrics

        metrics = AntigravityMetrics()
        
        # Check authentication
        if not self._initialize_auth():
            metrics.auth_error = "Not authenticated - please login to Antigravity"
            self._cache_metrics(metrics)
            return metrics
        
        metrics.is_authenticated = True
        
        # Fetch quota data
        try:
            quota_data = self.api_client.fetch_quota()
            
            if not quota_data:
                metrics.auth_error = "Failed to fetch quota data"
                self._cache_metrics(metrics)
                return metrics
            
            # Parse quota data
            parsed = self.api_client.parse_quota_data(quota_data)
            
            metrics.is_forbidden = parsed.get('forbidden', False)
            metrics.subscription_tier = parsed.get('subscription_tier')
            
            # Convert models to ModelQuota objects
            for model_data in parsed.get('models', []):
                metrics.models.append(ModelQuota(
                    name=model_data['name'],
                    percentage=model_data['percentage'],
                    reset_time=model_data['reset_time'],
                ))
            
            metrics.last_updated = datetime.now()
        except Exception as e:
            logger.error(f"Error fetching Antigravity metrics: {e}")
            metrics.auth_error = str(e)

        self._cache_metrics(metrics)
        return metrics

    def _cache_metrics(self, metrics: AntigravityMetrics) -> None:
        self._cached_metrics = metrics
        self._last_fetch = datetime.now()
