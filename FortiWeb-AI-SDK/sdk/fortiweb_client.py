#!/usr/bin/env python3
from __future__ import annotations
"""
FortiWeb REST API Client — Shared SDK Module

Provides the base HTTP client for all FortiWeb SDK tools.
Implements the FortiWeb 8.0 REST API authentication and request patterns.

Auth Model (from FortiWeb API docs):
  - Base64-encode JSON: {"username":"...","password":"...","vdom":"..."}
  - Send as Authorization header on EVERY request (stateless, no session)
  - No login/logout endpoints needed

URL Format:
  /api/v2.0/<path>/<table>/<subtable>?<args>

Paths:
  cmdb        — General CLI config operations
  cmdb_extra  — File upload/download operations
  ftp         — FTP policy operations
  log         — Log filtering and searching
  machine_learning — ML operations
  monitor     — Monitoring operations
  policy      — Policy operations
  server      — Server object operations
  system      — System operations
  user        — User management operations
  wad         — WAD function operations
  waf         — WAF function operations
  wvs         — WVS function operations

HTTP Methods:
  GET    — Read/list objects
  POST   — Create new objects
  PUT    — Update existing objects (requires ?mkey=<id>)
  DELETE — Remove objects (requires ?mkey=<id>)

Required Headers:
  Accept: application/json
  Content-Type: application/json
  Authorization: <base64-token>

Notes:
  - HTTP 1.0/1.1 only (no HTTP/2)
  - No keepalive or pipeline support
  - One API call per HTTP request

Author: Ulysses Project
Version: 1.0.0
"""

import urllib.request
import urllib.error
import urllib.parse
import ssl
import json
import base64
import os
from pathlib import Path
from typing import Any, Optional


def build_auth_token(username: str, password: str, vdom: str = "root") -> str:
    """Build FortiWeb Base64 authorization token.

    FortiWeb REST API requires Base64-encoding a JSON credential object
    and passing it in the Authorization header on every request.

    Args:
        username: FortiWeb admin username
        password: FortiWeb admin password
        vdom: Virtual domain (ADOM) name, default "root"

    Returns:
        Base64-encoded auth string ready for Authorization header
    """
    auth_obj = json.dumps({
        "username": username,
        "password": password,
        "vdom": vdom,
    })
    return base64.b64encode(auth_obj.encode()).decode()


def load_credentials(target_ip: str) -> Optional[dict]:
    """Load device credentials from MCP credential file.

    Search order (uses FIRST match):
    1. ~/.config/mcp/fortiweb_credentials.yaml (PRIMARY)
    2. ~/AppData/Local/mcp/fortiweb_credentials.yaml (Windows)
    3. C:/ProgramData/mcp/fortiweb_credentials.yaml (Windows system)
    4. C:/ProgramData/Ulysses/config/fortiweb_credentials.yaml (Ulysses)
    5. /etc/mcp/fortiweb_credentials.yaml (Linux system)

    Returns:
        dict with keys: host, username, password, verify_ssl (optional)
        None if no credentials found
    """
    config_paths = [
        Path.home() / ".config" / "mcp" / "fortiweb_credentials.yaml",
    ]

    if os.name == 'nt':
        config_paths.extend([
            Path.home() / "AppData" / "Local" / "mcp" / "fortiweb_credentials.yaml",
            Path("C:/ProgramData/mcp/fortiweb_credentials.yaml"),
            Path("C:/ProgramData/Ulysses/config/fortiweb_credentials.yaml"),
        ])
    else:
        config_paths.append(Path("/etc/mcp/fortiweb_credentials.yaml"))

    for config_path in config_paths:
        if config_path.exists():
            try:
                import yaml
                with open(config_path) as f:
                    config = yaml.safe_load(f)

                # Check default_lookup first (IP -> device_id mapping)
                if "default_lookup" in config and target_ip in config["default_lookup"]:
                    device_name = config["default_lookup"][target_ip]
                    if device_name in config.get("devices", {}):
                        return config["devices"][device_name]

                # Search devices by host
                for device in config.get("devices", {}).values():
                    if device.get("host") == target_ip:
                        return device

            except Exception:
                continue

    return None


# Common FortiWeb API error codes (from API docs)
FORTIWEB_ERROR_CODES = {
    -1: "Invalid length of value",
    -2: "Value out of range",
    -3: "Entry not found",
    -4: "Max entries reached",
    -5: "Duplicate entry exists",
    -6: "Memory allocation failed",
    -7: "Conflicts with system settings",
    -8: "Invalid IP address",
    -9: "Invalid IP netmask",
    -20: "Blank entry",
    -23: "Entry is in use",
    -30: "Invalid username or password",
    -37: "Permission denied",
    -50: "Invalid input format",
    -56: "Empty value not allowed",
    -100: "Duplicate username exists",
    -204: "Invalid username or password",
    -515: "Name is reserved keyword",
}


class FortiWebAPIError(Exception):
    """Error from FortiWeb REST API response."""

    def __init__(self, http_code: int, errcode: int = 0,
                 message: str = "", body: str = ""):
        self.http_code = http_code
        self.errcode = errcode
        self.message = message or FORTIWEB_ERROR_CODES.get(errcode, f"Error code {errcode}")
        self.body = body
        super().__init__(f"HTTP {http_code}: [{errcode}] {self.message}")


class FortiWebClient:
    """FortiWeb REST API client.

    Stateless client — each request carries full auth in the header.
    No session management needed.

    Usage:
        client = FortiWebClient("192.168.209.31", "admin", "password")
        admins = client.get("cmdb/system/admin")
        client.post("cmdb/system/admin", {"name": "new-admin", ...})
        client.put("cmdb/system/admin", {"name": "new-admin", ...}, mkey="new-admin")
        client.delete("cmdb/system/admin", mkey="new-admin")

    Note: post() and put() auto-wrap data in {"data": ...} if not already wrapped.
    """

    API_PREFIX = "/api/v2.0"

    def __init__(self, host: str, username: str, password: str,
                 vdom: str = "root", verify_ssl: bool = False,
                 timeout: int = 30):
        self.host = host
        self.vdom = vdom
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self._auth_token = build_auth_token(username, password, vdom)
        self._ssl_context = self._build_ssl_context()

    def _build_ssl_context(self) -> ssl.SSLContext:
        if not self.verify_ssl:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            return ctx
        return ssl.create_default_context()

    def _build_url(self, path: str, mkey: Optional[str] = None,
                   extra_params: Optional[dict] = None) -> str:
        """Build full API URL.

        Args:
            path: API path after /api/v2.0/ (e.g., "cmdb/system/admin")
            mkey: Primary key for PUT/DELETE operations
            extra_params: Additional query parameters
        """
        # Normalize path — strip leading slash if present
        path = path.lstrip("/")
        url = f"https://{self.host}{self.API_PREFIX}/{path}"

        params = {}
        if mkey is not None:
            params["mkey"] = mkey
        if extra_params:
            params.update(extra_params)

        if params:
            query = urllib.parse.urlencode(params)
            url = f"{url}?{query}"

        return url

    def request(self, method: str, path: str, data: Optional[dict] = None,
                mkey: Optional[str] = None,
                extra_params: Optional[dict] = None) -> dict:
        """Make an authenticated API request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API path (e.g., "cmdb/system/admin")
            data: Request body dict (for POST/PUT) — auto-wrapped in {"data": ...}
            mkey: Primary key for targeted operations
            extra_params: Additional query parameters

        Returns:
            Parsed JSON response dict

        Raises:
            FortiWebAPIError: On HTTP errors with parsed error codes
        """
        url = self._build_url(path, mkey, extra_params)

        # Auto-wrap data in {"data": ...} for POST/PUT if not already wrapped
        if data is not None and "data" not in data:
            data = {"data": data}

        payload = json.dumps(data).encode() if data else None

        req = urllib.request.Request(url, data=payload, method=method)
        req.add_header("Accept", "application/json")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", self._auth_token)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout,
                                        context=self._ssl_context) as response:
                raw = response.read().decode()
                if raw:
                    result = json.loads(raw)
                    # Check for error in successful response
                    if isinstance(result.get("results"), dict):
                        errcode = result["results"].get("errcode")
                        if errcode and errcode != 0:
                            raise FortiWebAPIError(200, errcode)
                    return result
                return {}
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode()
            except Exception:
                pass
            # Try to parse errcode from response body
            errcode = 0
            msg = ""
            try:
                parsed = json.loads(body)
                errcode = parsed.get("results", {}).get("errcode", 0)
                msg = parsed.get("msg", parsed.get("results", {}).get("msg", ""))
            except (json.JSONDecodeError, AttributeError):
                msg = body
            raise FortiWebAPIError(e.code, errcode, msg, body) from e

    def get(self, path: str, mkey: Optional[str] = None,
            extra_params: Optional[dict] = None) -> dict:
        """GET request — read/list objects."""
        return self.request("GET", path, mkey=mkey, extra_params=extra_params)

    def post(self, path: str, data: dict,
             extra_params: Optional[dict] = None) -> dict:
        """POST request — create new objects.

        Data is auto-wrapped: post("cmdb/system/admin", {"name": "foo"})
        sends body: {"data": {"name": "foo"}}
        """
        return self.request("POST", path, data=data, extra_params=extra_params)

    def put(self, path: str, data: dict, mkey: str,
            extra_params: Optional[dict] = None) -> dict:
        """PUT request — update existing objects.

        Data is auto-wrapped. mkey is required (the row/entry identifier).
        """
        return self.request("PUT", path, data=data, mkey=mkey,
                            extra_params=extra_params)

    def delete(self, path: str, mkey: str,
               extra_params: Optional[dict] = None) -> dict:
        """DELETE request — remove objects."""
        return self.request("DELETE", path, mkey=mkey,
                            extra_params=extra_params)

    @classmethod
    def from_credentials(cls, target_ip: str,
                         context_creds: Optional[dict] = None,
                         vdom: str = "root",
                         verify_ssl: bool = False,
                         timeout: int = 30) -> "FortiWebClient":
        """Create client from MCP credential chain.

        Checks context credentials first, then local config files.

        Args:
            target_ip: FortiWeb management IP
            context_creds: Credentials from ExecutionContext (optional)
            vdom: Virtual domain name
            verify_ssl: SSL verification flag
            timeout: Request timeout

        Returns:
            Configured FortiWebClient

        Raises:
            ValueError: If no credentials found
        """
        username = None
        password = None

        if context_creds:
            username = context_creds.get("username")
            password = context_creds.get("password")
            if context_creds.get("verify_ssl") is not None:
                verify_ssl = context_creds["verify_ssl"]

        if not username:
            local_creds = load_credentials(target_ip)
            if local_creds:
                username = local_creds.get("username")
                password = local_creds.get("password")
                if local_creds.get("verify_ssl") is not None:
                    verify_ssl = local_creds["verify_ssl"]

        if not username or not password:
            raise ValueError(
                f"No credentials found for {target_ip}. "
                f"Configure in ~/.config/mcp/fortiweb_credentials.yaml"
            )

        return cls(target_ip, username, password, vdom, verify_ssl, timeout)


if __name__ == "__main__":
    # Quick connectivity test
    client = FortiWebClient.from_credentials("192.168.209.31")
    result = client.get("cmdb/system/admin")
    print(json.dumps(result, indent=2))
