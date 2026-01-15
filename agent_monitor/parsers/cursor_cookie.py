"""Cursor cookie extraction helpers (macOS-focused).

Attempts to auto-detect Cursor session cookies from the Cursor app or browsers.
Falls back to CURSOR_DASHBOARD_COOKIE env var when provided.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class CursorCookieProvider:
    """Provide Cursor dashboard cookies with light caching."""

    def __init__(self, cache_ttl_seconds: int = 600) -> None:
        self.cache_ttl_seconds = max(60, cache_ttl_seconds)
        self._cached_cookie: Optional[str] = None
        self._cached_at: Optional[float] = None
        self.last_error: Optional[str] = None

    def get_cookie(self) -> Optional[str]:
        """Return cookie header string for cursor.com, if available."""
        candidates = self.get_candidate_cookies()
        if not candidates:
            return None
        return candidates[0]

    def get_candidate_cookies(self) -> list[str]:
        """Return a list of candidate cookie headers in priority order."""
        env_cookie = os.getenv("CURSOR_DASHBOARD_COOKIE")
        if env_cookie:
            self.last_error = None
            return [env_cookie]

        if self._cached_cookie and self._cached_at:
            age = time.time() - self._cached_at
            if age < self.cache_ttl_seconds:
                return [self._cached_cookie]

        candidates = []
        app_cookie = self._load_from_cursor_app()
        if app_cookie:
            candidates.append(app_cookie)

        browser_cookies = self._load_from_browsers_all()
        candidates.extend(browser_cookies)

        # De-duplicate while preserving order
        seen = set()
        unique = []
        for cookie in candidates:
            if cookie in seen:
                continue
            seen.add(cookie)
            unique.append(cookie)

        if not unique:
            hint = self.last_error or "no cursor.com cookie found"
            self.last_error = (
                f"{hint}; set CURSOR_DASHBOARD_COOKIE or install browser-cookie3"
            )
            return []

        self._cached_cookie = unique[0]
        self._cached_at = time.time()
        self.last_error = None
        return unique

    def _load_from_cursor_app(self) -> Optional[str]:
        """Try to read Cursor app cookie database (plaintext values only)."""
        candidates = [
            Path.home() / "Library" / "Application Support" / "Cursor" / "Cookies",
            Path.home()
            / "Library"
            / "Application Support"
            / "Cursor"
            / "Default"
            / "Cookies",
        ]
        for path in candidates:
            if not path.exists():
                continue
            cookies = self._read_cookie_db(path)
            cookie_header = self._cookie_header_from_map(cookies)
            if cookie_header:
                return cookie_header
        return None

    def _load_from_browsers_all(self) -> list[str]:
        """Try to read cursor.com cookies from supported browsers."""
        try:
            import browser_cookie3
        except Exception:
            self.last_error = "browser-cookie3 not installed"
            return []

        loaders = []
        for name in ("chrome", "chromium", "edge", "safari", "firefox"):
            loader = getattr(browser_cookie3, name, None)
            if loader:
                loaders.append((name, loader))

        cookies_found: list[str] = []
        for _, loader in loaders:
            jar = None
            try:
                jar = loader(domain_name="cursor.com")
            except TypeError:
                try:
                    jar = loader()
                except Exception:
                    jar = None
            except Exception:
                jar = None

            if not jar:
                continue

            cookies = {}
            for cookie in jar:
                if "cursor.com" not in cookie.domain:
                    continue
                cookies[cookie.name] = cookie.value
            header = self._cookie_header_from_map(cookies)
            if header:
                cookies_found.append(header)

        if not cookies_found:
            self.last_error = "no browser cookies found"
        return cookies_found

    def _read_cookie_db(self, path: Path) -> dict[str, str]:
        cookies: dict[str, str] = {}
        try:
            conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name, value FROM cookies WHERE host_key LIKE '%cursor.com'"
            )
            for name, value in cursor.fetchall():
                if value:
                    cookies[name] = value
            conn.close()
        except Exception:
            return {}
        return cookies

    def _cookie_header_from_map(self, cookies: dict[str, str]) -> Optional[str]:
        if not cookies:
            return None
        if "WorkosCursorSessionToken" not in cookies:
            return None
        preferred = [
            "WorkosCursorSessionToken",
            "cursor_anonymous_id",
            "htjs_anonymous_id",
            "htjs_sesh",
        ]
        ordered = []
        for name in preferred:
            if name in cookies:
                ordered.append(f"{name}={cookies[name]}")
        for name, value in cookies.items():
            if name in preferred:
                continue
            ordered.append(f"{name}={value}")
        return "; ".join(ordered)
