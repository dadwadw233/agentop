"""Fetch OpenAI Codex rate limit usage via the Codex backend."""

import base64
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import httpx

from ..core.models import CreditsSnapshot, RateLimitSnapshot, RateLimitWindow


class CodexRateLimitClient:
    """Fetch Codex rate-limit usage from the backend /usage endpoint."""

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

        token, account_id, codex_home = self._load_auth()
        if not token:
            self._last_error = "Codex ChatGPT auth not available"
            return None

        base_url = self._resolve_base_url(codex_home)
        if not base_url:
            self._last_error = "Codex base URL not available"
            return None

        url = self._usage_url(base_url)
        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "agentop",
        }
        if account_id:
            headers["ChatGPT-Account-Id"] = account_id

        try:
            with httpx.Client(timeout=10.0, trust_env=self._trust_env()) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            self._last_error = self._format_proxy_error(exc, "Rate limit fetch failed")
            return None

        snapshot = self._parse_payload(payload)
        if snapshot:
            snapshot.captured_at = datetime.now()
            self._cache = snapshot
            self._last_fetch = snapshot.captured_at
            self._last_error = None
        else:
            self._last_error = "Rate limit payload missing or invalid"
        return snapshot

    def _load_auth(self) -> Tuple[Optional[str], Optional[str], Path]:
        codex_home = self._find_codex_home()
        auth_path = codex_home / "auth.json"
        if not auth_path.exists():
            return None, None, codex_home

        try:
            with auth_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return None, None, codex_home

        tokens = data.get("tokens") or {}
        access_token = tokens.get("access_token") or tokens.get("accessToken")
        if not access_token:
            return None, None, codex_home

        account_id = tokens.get("account_id")
        if not account_id:
            account_id = self._extract_account_id_from_id_token(tokens.get("id_token"))

        return access_token, account_id, codex_home

    def _extract_account_id_from_id_token(self, id_token: Optional[str]) -> Optional[str]:
        if not id_token or not isinstance(id_token, str):
            return None

        parts = id_token.split(".")
        if len(parts) < 2:
            return None

        payload = parts[1]
        padding = "=" * (-len(payload) % 4)
        try:
            decoded = base64.urlsafe_b64decode(payload + padding)
            claims = json.loads(decoded.decode("utf-8"))
        except Exception:
            return None

        auth_claims = claims.get("https://api.openai.com/auth") or {}
        account_id = auth_claims.get("chatgpt_account_id")
        if isinstance(account_id, str) and account_id:
            return account_id
        return None

    def _find_codex_home(self) -> Path:
        env_home = os.environ.get("CODEX_HOME")
        if env_home:
            return Path(env_home).expanduser()
        return Path("~/.codex").expanduser()

    def _resolve_base_url(self, codex_home: Path) -> Optional[str]:
        env_override = os.environ.get("CODEX_CHATGPT_BASE_URL")
        if env_override:
            return env_override.strip().rstrip("/")

        config_path = codex_home / "config.toml"
        if not config_path.exists():
            return "https://chatgpt.com/backend-api"

        chatgpt_base_url = self._read_chatgpt_base_url(config_path)
        if not chatgpt_base_url:
            return "https://chatgpt.com/backend-api"

        base_url = chatgpt_base_url.strip().rstrip("/")
        if base_url.startswith("https://chatgpt.com") or base_url.startswith(
            "https://chat.openai.com"
        ):
            if "/backend-api" not in base_url:
                base_url = f"{base_url}/backend-api"
        return base_url

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

    def _read_chatgpt_base_url(self, path: Path) -> Optional[str]:
        try:
            contents = path.read_text(encoding="utf-8")
        except Exception:
            return None

        for line in contents.splitlines():
            line = line.split("#", 1)[0].strip()
            if not line or "chatgpt_base_url" not in line:
                continue
            match = re.match(r'chatgpt_base_url\s*=\s*["\']([^"\']+)["\']', line)
            if match:
                return match.group(1)
        return None

    def _usage_url(self, base_url: str) -> str:
        base_url = base_url.rstrip("/")
        if "/backend-api" in base_url:
            return f"{base_url}/wham/usage"
        return f"{base_url}/api/codex/usage"

    def _parse_payload(self, payload: Dict[str, Any]) -> Optional[RateLimitSnapshot]:
        if not isinstance(payload, dict):
            return None

        rate_limit = payload.get("rate_limit")
        if rate_limit is None:
            return RateLimitSnapshot(
                primary=None,
                secondary=None,
                credits=self._parse_credits(payload.get("credits")),
                plan_type=payload.get("plan_type"),
            )

        primary = self._parse_window(rate_limit.get("primary_window"))
        secondary = self._parse_window(rate_limit.get("secondary_window"))
        return RateLimitSnapshot(
            primary=primary,
            secondary=secondary,
            credits=self._parse_credits(payload.get("credits")),
            plan_type=payload.get("plan_type"),
        )

    def _parse_window(self, window: Any) -> Optional[RateLimitWindow]:
        if not isinstance(window, dict):
            return None

        used_percent = window.get("used_percent")
        if used_percent is None:
            return None

        try:
            used_percent = float(used_percent)
        except (TypeError, ValueError):
            return None

        window_seconds = window.get("limit_window_seconds")
        window_minutes = None
        if isinstance(window_seconds, (int, float)):
            window_minutes = int(window_seconds // 60)

        resets_at = window.get("reset_at")
        resets_at_dt = None
        if isinstance(resets_at, (int, float)) and resets_at > 0:
            resets_at_dt = datetime.fromtimestamp(int(resets_at))

        return RateLimitWindow(
            used_percent=used_percent,
            window_minutes=window_minutes,
            resets_at=resets_at_dt,
        )

    def _parse_credits(self, credits: Any) -> Optional[CreditsSnapshot]:
        if not isinstance(credits, dict):
            return None
        has_credits = credits.get("has_credits")
        unlimited = credits.get("unlimited")
        if not isinstance(has_credits, bool) or not isinstance(unlimited, bool):
            return None
        balance = credits.get("balance")
        if isinstance(balance, dict):
            balance = balance.get("value")
        if balance is not None and not isinstance(balance, str):
            balance = str(balance)
        return CreditsSnapshot(
            has_credits=has_credits,
            unlimited=unlimited,
            balance=balance,
        )
