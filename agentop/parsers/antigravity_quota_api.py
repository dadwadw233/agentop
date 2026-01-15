"""Antigravity quota API client.

Client for fetching quota data from Google Cloud Code API.
Based on Antigravity-Manager's quota.rs implementation.
"""

import httpx
from typing import Optional, Dict, Any, List
import logging
import os

logger = logging.getLogger(__name__)


class AntigravityQuotaAPI:
    """Client for Antigravity quota API."""
    
    QUOTA_API_URL = "https://cloudcode-pa.googleapis.com/v1internal:fetchAvailableModels"
    LOAD_PROJECT_URL = "https://cloudcode-pa.googleapis.com/v1internal:loadCodeAssist"
    USER_AGENT = "antigravity/1.11.3 Darwin/arm64"
    DEFAULT_PROJECT_ID = "bamboo-precept-lgxtn"
    TIMEOUT = 15.0
    
    def __init__(self, access_token: str):
        """
        Initialize API client.
        
        Args:
            access_token: Google access token for authentication
        """
        self.access_token = access_token
        self._project_id: Optional[str] = None
        self._subscription_tier: Optional[str] = None
    
    def fetch_project_info(self) -> tuple[Optional[str], Optional[str]]:
        """
        Fetch project ID and subscription tier.
        
        Returns:
            Tuple of (project_id, subscription_tier)
        """
        try:
            with httpx.Client(timeout=self.TIMEOUT, trust_env=self._trust_env()) as client:
                response = client.post(
                    self.LOAD_PROJECT_URL,
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json",
                        "User-Agent": "antigravity/windows/amd64",
                    },
                    json={"metadata": {"ideType": "ANTIGRAVITY"}}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    project_id = data.get('cloudaicompanionProject')
                    
                    # Get subscription tier (paid_tier preferred over current_tier)
                    paid_tier = data.get('paidTier', {})
                    current_tier = data.get('currentTier', {})
                    
                    tier = paid_tier.get('id') or current_tier.get('id')
                    
                    logger.info(f"Project info: ID={project_id}, Tier={tier}")
                    return project_id, tier
                else:
                    logger.warning(f"Failed to fetch project info: {response.status_code}")
                    return None, None
                    
        except Exception as e:
            logger.error(f"Error fetching project info: {e}")
            return None, None
    
    def fetch_quota(self, project_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch quota data from Google API.
        
        Args:
            project_id: Google Cloud project ID (uses cached or default if None)
            
        Returns:
            Quota data dictionary or None if failed
        """
        # Use provided project_id, cached, or default
        if not project_id:
            if not self._project_id:
                # Try to fetch project info first
                self._project_id, self._subscription_tier = self.fetch_project_info()
            project_id = self._project_id or self.DEFAULT_PROJECT_ID
        
        try:
            with httpx.Client(timeout=self.TIMEOUT, trust_env=self._trust_env()) as client:
                response = client.post(
                    self.QUOTA_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "User-Agent": self.USER_AGENT,
                        "Content-Type": "application/json",
                    },
                    json={"project": project_id}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info("Successfully fetched quota data")
                    return data
                elif response.status_code == 403:
                    logger.warning("Forbidden (403) - account may not have access")
                    return {"forbidden": True}
                else:
                    logger.error(f"API error: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching quota data: {e}")
            return None
    
    def parse_quota_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse raw quota data into structured format.
        
        Args:
            data: Raw API response
            
        Returns:
            Parsed quota data with models list
        """
        if data.get('forbidden'):
            return {
                'forbidden': True,
                'models': [],
                'subscription_tier': self._subscription_tier,
            }
        
        models = []
        raw_models = data.get('models', {})
        
        for model_name, model_info in raw_models.items():
            quota_info = model_info.get('quotaInfo')
            if not quota_info:
                continue
            
            # Only keep Gemini and Claude models
            if 'gemini' in model_name.lower() or 'claude' in model_name.lower():
                remaining_fraction = quota_info.get('remainingFraction', 0)
                percentage = int(remaining_fraction * 100)
                reset_time = quota_info.get('resetTime', '')
                
                models.append({
                    'name': model_name,
                    'percentage': percentage,
                    'reset_time': reset_time,
                })
        
        return {
            'forbidden': False,
            'models': models,
            'subscription_tier': self._subscription_tier,
        }

    def _trust_env(self) -> bool:
        return os.environ.get("AGENTOP_DISABLE_PROXY") != "1"
