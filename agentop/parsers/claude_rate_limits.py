"""Fetch Claude Code quota usage via the Claude OAuth usage endpoint."""

import hashlib
import json
import os
import subprocess
import sys
import getpass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

from ..core.models import RateLimitSnapshot, RateLimitWindow


class ClaudeRateLimitClient:
    """Fetch Claude Code quota usage from the /api/oauth/usage endpoint."""

    _BETA_HEADER = "oauth-2025-04-20"

    def __init__(self, cache_ttl_seconds: int = 60) -> None:
        self.cache_ttl_seconds = max(10, cache_ttl_seconds)
        self._last_fetch: Optional[datetime] = None
        self._cache: Optional[RateLimitSnapshot] = None
        self._last_error: Optional[str] = None

    @property
    def last_error(self) -> Optional[str]:
        """Return the last fetch error, if any."""
        return self._last_error

    def get_rate_limits(self) -> Optional[RateLimitSnapshot]:
        """Return cached rate limits or fetch from the backend."""
        if self._cache and self._last_fetch:
            age = (datetime.now() - self._last_fetch).total_seconds()
            if age < self.cache_ttl_seconds:
                return self._cache

        oauth = self._load_oauth()
        if not oauth or not oauth.get("accessToken"):
            self._last_error = "Claude OAuth token not available"
            return None

        expires_at = oauth.get("expiresAt")
        if self._is_expired(expires_at):
            self._last_error = "Claude OAuth token expired"
            return None

        base_url = self._resolve_base_url()
        url = f"{base_url}/api/oauth/usage"
        headers = {
            "Authorization": f"Bearer {oauth['accessToken']}",
            "User-Agent": "agentop",
            "Content-Type": "application/json",
            "anthropic-beta": self._BETA_HEADER,
        }

        try:
            with httpx.Client(timeout=10.0, trust_env=self._trust_env()) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            self._last_error = self._format_proxy_error(exc, "Quota fetch failed")
            return None

        snapshot = self._parse_payload(payload)
        if snapshot:
            snapshot.captured_at = datetime.now()
            self._cache = snapshot
            self._last_fetch = snapshot.captured_at
            self._last_error = None
        else:
            self._last_error = "Quota payload missing or invalid"

        return snapshot

    def _resolve_base_url(self) -> str:
        base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        return base_url.strip().rstrip("/")

    def _trust_env(self) -> bool:
        return os.environ.get("AGENTOP_DISABLE_PROXY") != "1"

    def _format_proxy_error(self, exc: Exception, prefix: str) -> str:
        message = str(exc)
        if "Unknown scheme for proxy URL" in message or "unknown scheme for proxy URL" in message:
            return (
                f"{prefix}: proxy scheme not supported. "
                "Set AGENTOP_DISABLE_PROXY=1 or install httpx[socks]."
            )
        return f"{prefix}: {exc}"

    def _load_oauth(self) -> Optional[Dict[str, Any]]:
        env_token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
        if env_token:
            return {"accessToken": env_token, "expiresAt": None}

        fd_token = self._load_fd_token()
        if fd_token:
            return {"accessToken": fd_token, "expiresAt": None}

        credentials = self._read_credentials()
        if not credentials:
            return None

        oauth = credentials.get("claudeAiOauth")
        if not isinstance(oauth, dict):
            return None

        return oauth

    def _load_fd_token(self) -> Optional[str]:
        fd_value = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR")
        if not fd_value:
            return None
        try:
            fd = int(fd_value)
        except ValueError:
            return None
        try:
            return Path(f"/dev/fd/{fd}").read_text(encoding="utf-8").strip()
        except Exception:
            return None

    def _read_credentials(self) -> Optional[Dict[str, Any]]:
        credentials = self._read_keychain_credentials()
        if credentials:
            return credentials
        return self._read_plaintext_credentials()

    def _read_keychain_credentials(self) -> Optional[Dict[str, Any]]:
        if sys.platform != "darwin":
            return None
        service = self._keychain_service_name()
        account = os.environ.get("USER") or getpass.getuser()
        try:
            result = subprocess.run(
                ["security", "find-generic-password", "-a", account, "-w", "-s", service],
                check=False,
                capture_output=True,
                text=True,
            )
        except Exception:
            return None
        if result.returncode != 0:
            return None
        output = result.stdout.strip()
        if not output:
            return None
        try:
            return json.loads(output)
        except Exception:
            return None

    def _read_plaintext_credentials(self) -> Optional[Dict[str, Any]]:
        credentials_path = self._config_dir() / ".credentials.json"
        if not credentials_path.exists():
            return None
        try:
            return json.loads(credentials_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _config_dir(self) -> Path:
        return Path(os.environ.get("CLAUDE_CONFIG_DIR", "~/.claude")).expanduser()

    def _keychain_service_name(self) -> str:
        suffix = os.environ.get("CLAUDE_CODE_OAUTH_FILE_SUFFIX", "")
        config_dir = self._config_dir()
        extra = ""
        if os.environ.get("CLAUDE_CONFIG_DIR"):
            digest = hashlib.sha256(str(config_dir).encode("utf-8")).hexdigest()[:8]
            extra = f"-{digest}"
        return f"Claude Code{suffix}-credentials{extra}"

    def _is_expired(self, expires_at: Any) -> bool:
        if expires_at is None:
            return False
        try:
            expires_at_ms = float(expires_at)
        except (TypeError, ValueError):
            return False
        # Treat token as expired if within 5 minutes of expiry.
        return (datetime.utcnow().timestamp() * 1000 + 300000) >= expires_at_ms

    def _parse_payload(self, payload: Dict[str, Any]) -> Optional[RateLimitSnapshot]:
        if not isinstance(payload, dict):
            return None

        five_hour = self._parse_window(payload.get("five_hour"), 5 * 60)
        seven_day = self._parse_window(payload.get("seven_day"), 7 * 24 * 60)

        if not five_hour and not seven_day:
            return None

        return RateLimitSnapshot(primary=five_hour, secondary=seven_day)

    def _parse_window(
        self, window: Any, window_minutes: Optional[int]
    ) -> Optional[RateLimitWindow]:
        if not isinstance(window, dict):
            return None

        utilization = window.get("utilization")
        if utilization is None:
            return None
        try:
            used_percent = float(utilization)
        except (TypeError, ValueError):
            return None

        resets_at = window.get("resets_at")
        resets_at_dt = None
        if isinstance(resets_at, str) and resets_at:
            try:
                resets_at_dt = datetime.fromisoformat(resets_at.replace("Z", "+00:00"))
                if resets_at_dt.tzinfo is not None:
                    resets_at_dt = (
                        resets_at_dt.astimezone().replace(tzinfo=None)
                    )
            except ValueError:
                resets_at_dt = None

        return RateLimitWindow(
            used_percent=used_percent,
            window_minutes=window_minutes,
            resets_at=resets_at_dt,
        )
