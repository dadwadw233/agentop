"""Google Auth token extractor for Antigravity.

Extracts access token from Antigravity's SQLite database and refreshes when needed.
Based on Antigravity-Manager's db.rs and protobuf.rs implementations.
"""

import base64
import logging
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx
import psutil

logger = logging.getLogger(__name__)


@dataclass
class OAuthToken:
    """OAuth token data extracted from Antigravity state."""

    access_token: Optional[str]
    refresh_token: Optional[str]
    expiry_timestamp: Optional[int]  # seconds since epoch


class GoogleAuthExtractor:
    """Extract Google auth tokens from Antigravity state database."""

    # Antigravity database paths (from Antigravity-Manager's db.rs)
    DB_PATHS = [
        Path.home() / "Library/Application Support/Antigravity/User/globalStorage/state.vscdb",
        Path.home() / ".config/Antigravity/User/globalStorage/state.vscdb",
        Path(f"{Path.home()}/AppData/Roaming/Antigravity/User/globalStorage/state.vscdb"),
    ]

    STATE_KEY = "jetskiStateSync.agentManagerInitState"

    CLIENT_ID = "1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com"
    TOKEN_URL = "https://oauth2.googleapis.com/token"

    def __init__(self):
        """Initialize auth extractor."""
        self.db_path = self._find_db()
        self._cached_token: Optional[OAuthToken] = None

    def _find_db(self) -> Optional[Path]:
        """Find Antigravity state database."""
        db_path = self._find_db_from_process()
        if db_path:
            return db_path

        portable_path = self._find_portable_db()
        if portable_path:
            return portable_path

        for path in self.DB_PATHS:
            if path.exists():
                logger.info("Found Antigravity DB at: %s", path)
                return path

        logger.warning("Antigravity database not found")
        return None

    def _find_db_from_process(self) -> Optional[Path]:
        """Detect DB path from Antigravity process --user-data-dir."""
        for proc in psutil.process_iter(["name", "cmdline", "exe"]):
            try:
                name = (proc.info.get("name") or "").lower()
                cmdline = proc.info.get("cmdline") or []
                cmdline_str = " ".join(cmdline).lower()
                if "antigravity" not in name and "antigravity" not in cmdline_str:
                    continue
                user_dir = self._extract_user_data_dir(cmdline)
                if user_dir:
                    candidate = (
                        Path(user_dir)
                        / "User"
                        / "globalStorage"
                        / "state.vscdb"
                    )
                    if candidate.exists():
                        logger.info("Found Antigravity DB via process args: %s", candidate)
                        return candidate
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None

    def _find_portable_db(self) -> Optional[Path]:
        """Detect portable Antigravity DB location relative to the executable."""
        for proc in psutil.process_iter(["name", "exe", "cmdline"]):
            try:
                name = (proc.info.get("name") or "").lower()
                cmdline = proc.info.get("cmdline") or []
                cmdline_str = " ".join(cmdline).lower()
                if "antigravity" not in name and "antigravity" not in cmdline_str:
                    continue
                exe_path = proc.info.get("exe")
                if not exe_path:
                    continue
                candidate = (
                    Path(exe_path)
                    .resolve()
                    .parent
                    / "data"
                    / "user-data"
                    / "User"
                    / "globalStorage"
                    / "state.vscdb"
                )
                if candidate.exists():
                    logger.info("Found Antigravity portable DB: %s", candidate)
                    return candidate
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None

    def _extract_user_data_dir(self, cmdline: list[str]) -> Optional[str]:
        for idx, arg in enumerate(cmdline):
            if arg.startswith("--user-data-dir="):
                return arg.split("=", 1)[1]
            if arg == "--user-data-dir" and idx + 1 < len(cmdline):
                return cmdline[idx + 1]
        return None

    def get_access_token(self) -> Optional[str]:
        """
        Get a fresh Google access token from Antigravity database.

        Returns:
            Access token string or None if not found
        """
        if not self.db_path or not self.db_path.exists():
            self.db_path = self._find_db()

        if self._cached_token and not self._is_expired(self._cached_token.expiry_timestamp):
            return self._cached_token.access_token

        if self._cached_token and self._is_expired(self._cached_token.expiry_timestamp):
            if self._cached_token.refresh_token:
                refreshed = self._refresh_access_token(self._cached_token.refresh_token)
                if refreshed:
                    self._cache_token(refreshed)
                    return refreshed.access_token

        token = self._read_token_from_db()
        if not token:
            return None

        if token.access_token and not self._is_expired(token.expiry_timestamp):
            self._cache_token(token)
            return token.access_token

        if token.refresh_token:
            refreshed = self._refresh_access_token(token.refresh_token)
            if refreshed:
                self._cache_token(refreshed)
                return refreshed.access_token

        self._cache_token(token)
        return token.access_token

    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return self.db_path is not None and self.get_access_token() is not None

    def _cache_token(self, token: OAuthToken) -> None:
        self._cached_token = token
        self._cached_at = time.time()

    def _read_token_from_db(self) -> Optional[OAuthToken]:
        if not self.db_path:
            return None

        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute(
                "SELECT value FROM ItemTable WHERE key = ?",
                (self.STATE_KEY,),
            )
            row = cursor.fetchone()
            conn.close()
            if not row:
                logger.warning("No data found for key: %s", self.STATE_KEY)
                return None
            encoded_data = row[0]
            protobuf_data = base64.b64decode(encoded_data)
        except Exception as exc:
            logger.error("Error reading from database: %s", exc)
            return None

        return self._parse_oauth_from_protobuf(protobuf_data)

    def _parse_oauth_from_protobuf(self, data: bytes) -> Optional[OAuthToken]:
        oauth_data = self._find_length_delimited_field(data, 6)
        if not oauth_data:
            return None

        access_token = self._find_string_field(oauth_data, 1)
        refresh_token = self._find_string_field(oauth_data, 3)
        expiry_blob = self._find_length_delimited_field(oauth_data, 4)
        expiry_timestamp = None
        if expiry_blob:
            expiry_timestamp = self._find_varint_field(expiry_blob, 1)

        if not access_token and not refresh_token:
            return None

        return OAuthToken(
            access_token=access_token,
            refresh_token=refresh_token,
            expiry_timestamp=int(expiry_timestamp) if expiry_timestamp else None,
        )

    def _refresh_access_token(self, refresh_token: str) -> Optional[OAuthToken]:
        client_id = os.getenv("ANTIGRAVITY_OAUTH_CLIENT_ID", self.CLIENT_ID)
        client_secret = os.getenv("ANTIGRAVITY_OAUTH_CLIENT_SECRET")
        if not client_secret:
            logger.warning("Antigravity OAuth client secret not set; skipping refresh")
            return None

        try:
            response = httpx.post(
                self.TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
                timeout=15.0,
            )
        except Exception as exc:
            logger.error("Token refresh request failed: %s", exc)
            return None

        if response.status_code != 200:
            logger.error("Token refresh failed: %s", response.text)
            return None

        try:
            data = response.json()
        except Exception as exc:
            logger.error("Token refresh JSON parse failed: %s", exc)
            return None

        access_token = data.get("access_token")
        expires_in = data.get("expires_in")
        if not access_token or not expires_in:
            return None

        expiry_timestamp = int(time.time()) + int(expires_in)
        return OAuthToken(
            access_token=access_token,
            refresh_token=refresh_token,
            expiry_timestamp=expiry_timestamp,
        )

    def _is_expired(self, expiry_timestamp: Optional[int]) -> bool:
        if not expiry_timestamp:
            return False
        now = int(time.time())
        return expiry_timestamp <= now + 300

    def _read_varint(self, data: bytes, offset: int) -> tuple[int, int]:
        result = 0
        shift = 0
        pos = offset
        while pos < len(data):
            byte = data[pos]
            result |= (byte & 0x7F) << shift
            pos += 1
            if byte & 0x80 == 0:
                return result, pos
            shift += 7
        raise ValueError("Incomplete varint")

    def _skip_field(self, data: bytes, offset: int, wire_type: int) -> int:
        if wire_type == 0:
            _, new_offset = self._read_varint(data, offset)
            return new_offset
        if wire_type == 1:
            return offset + 8
        if wire_type == 2:
            length, content_offset = self._read_varint(data, offset)
            return content_offset + length
        if wire_type == 5:
            return offset + 4
        raise ValueError(f"Unknown wire type: {wire_type}")

    def _find_length_delimited_field(self, data: bytes, field_num: int) -> Optional[bytes]:
        offset = 0
        while offset < len(data):
            try:
                tag, offset = self._read_varint(data, offset)
            except ValueError:
                return None
            wire_type = tag & 7
            current_field = tag >> 3
            if wire_type == 2:
                length, content_offset = self._read_varint(data, offset)
                content = data[content_offset : content_offset + length]
                offset = content_offset + length
                if current_field == field_num:
                    return content
            else:
                offset = self._skip_field(data, offset, wire_type)
        return None

    def _find_varint_field(self, data: bytes, field_num: int) -> Optional[int]:
        offset = 0
        while offset < len(data):
            try:
                tag, offset = self._read_varint(data, offset)
            except ValueError:
                return None
            wire_type = tag & 7
            current_field = tag >> 3
            if wire_type == 0:
                value, offset = self._read_varint(data, offset)
                if current_field == field_num:
                    return value
            else:
                offset = self._skip_field(data, offset, wire_type)
        return None

    def _find_string_field(self, data: bytes, field_num: int) -> Optional[str]:
        value = self._find_length_delimited_field(data, field_num)
        if not value:
            return None
        try:
            return value.decode("utf-8")
        except Exception:
            return None
