"""
FortiZTP API Client
Base client for FortiZTP API authentication and requests.
"""

import os
import time
import requests
import yaml
from typing import Any, Dict, Optional


class FortiZTPClient:
    """
    FortiZTP API Client for Zero Touch Provisioning operations.

    IMPORTANT: FortiZTP requires LOCAL IAM API Users, not ORG type.
    Create your API user in FortiCloud IAM with type "Local".

    Example:
        # Method 1: Direct credentials
        client = FortiZTPClient(
            username="your-api-user-id",
            password="your-api-password"
        )

        # Method 2: From credential file
        client = FortiZTPClient.from_credential_file("credentials.yaml")

        # Method 3: From environment variables
        client = FortiZTPClient.from_env()

        # Use the client
        devices = client.list_devices()
        scripts = client.list_scripts()
    """

    AUTH_URL = "https://customerapiauth.fortinet.com/api/v1/oauth/token/"
    API_BASE = "https://fortiztp.forticloud.com/public/api/v2"
    CLIENT_ID = "fortiztp"

    def __init__(
        self,
        username: str,
        password: str,
        account_email: Optional[str] = None
    ):
        """
        Initialize FortiZTP client.

        Args:
            username: FortiCloud API User ID (Local IAM type only)
            password: FortiCloud API Password
            account_email: Optional FortiCloud account email for v1 API features
        """
        self.username = username
        self.password = password
        self.account_email = account_email
        self._access_token: Optional[str] = None
        self._token_expiry_time: float = 0  # Unix timestamp when token expires
        self._token_refresh_buffer: int = 60  # Refresh 60 seconds before expiry

    @classmethod
    def from_credential_file(cls, filepath: str) -> "FortiZTPClient":
        """
        Create client from a YAML credential file.

        Expected file format:
            api_username: "your-api-user-id"
            api_password: "your-api-password"
            account_email: "your@email.com"  # optional

        Or with nested structure:
            local_iam:
              fortiztp:
                api_username: "your-api-user-id"
                api_password: "your-api-password"
                account_email: "your@email.com"

        Args:
            filepath: Path to YAML credential file

        Returns:
            FortiZTPClient instance
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Credential file not found: {filepath}")

        with open(filepath, 'r') as f:
            creds = yaml.safe_load(f) or {}

        # Check for nested structure first
        local_creds = creds.get("local_iam", {}).get("fortiztp", {})

        username = local_creds.get("api_username") or creds.get("api_username")
        password = local_creds.get("api_password") or creds.get("api_password")
        account_email = local_creds.get("account_email") or creds.get("account_email")

        if not username or not password:
            raise ValueError("Credential file must contain api_username and api_password")

        return cls(username=username, password=password, account_email=account_email)

    @classmethod
    def from_env(cls) -> "FortiZTPClient":
        """
        Create client from environment variables.

        Required environment variables:
            FORTIZTP_USERNAME: FortiCloud API User ID
            FORTIZTP_PASSWORD: FortiCloud API Password

        Optional:
            FORTIZTP_ACCOUNT_EMAIL: FortiCloud account email

        Returns:
            FortiZTPClient instance
        """
        username = os.environ.get("FORTIZTP_USERNAME")
        password = os.environ.get("FORTIZTP_PASSWORD")
        account_email = os.environ.get("FORTIZTP_ACCOUNT_EMAIL")

        if not username or not password:
            raise ValueError(
                "Environment variables FORTIZTP_USERNAME and FORTIZTP_PASSWORD must be set"
            )

        return cls(username=username, password=password, account_email=account_email)

    def _authenticate(self) -> str:
        """
        Authenticate and get OAuth access token.

        Returns:
            Access token string

        Raises:
            AuthenticationError: If authentication fails
        """
        payload = {
            "username": self.username,
            "password": self.password,
            "client_id": self.CLIENT_ID,
            "grant_type": "password"
        }

        response = requests.post(self.AUTH_URL, json=payload, timeout=30)

        if response.status_code != 200:
            raise AuthenticationError(
                f"Authentication failed: {response.status_code} - {response.text}"
            )

        data = response.json()
        if "access_token" not in data:
            raise AuthenticationError(f"No access_token in response: {data}")

        self._access_token = data["access_token"]
        expires_in = data.get("expires_in", 3600)
        self._token_expiry_time = time.time() + expires_in

        return self._access_token

    def _is_token_expired(self) -> bool:
        """Check if token is expired or about to expire."""
        if not self._access_token:
            return True
        # Refresh if within buffer period of expiry
        return time.time() >= (self._token_expiry_time - self._token_refresh_buffer)

    def get_token(self) -> str:
        """Get current access token, authenticating or refreshing if needed."""
        if self._is_token_expired():
            self._authenticate()
        return self._access_token

    def refresh_token(self) -> str:
        """Force token refresh."""
        self._access_token = None
        return self._authenticate()

    def _headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        return {
            "Authorization": f"Bearer {self.get_token()}",
            "Content-Type": "application/json"
        }

    def _request(
        self,
        method: str,
        endpoint: str,
        _retry_on_401: bool = True,
        **kwargs
    ) -> requests.Response:
        """
        Make authenticated API request with automatic token refresh on 401.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            _retry_on_401: Whether to retry once on 401 (default: True)
            **kwargs: Additional arguments for requests

        Returns:
            Response object
        """
        url = f"{self.API_BASE}{endpoint}"
        kwargs.setdefault("headers", self._headers())
        kwargs.setdefault("timeout", 60)

        response = requests.request(method, url, **kwargs)

        # Retry once on 401 with fresh token
        if response.status_code == 401 and _retry_on_401:
            self.refresh_token()
            kwargs["headers"] = self._headers()  # Update with new token
            response = requests.request(method, url, **kwargs)

        return response

    # Convenience methods that use DeviceManager and ScriptManager
    def list_devices(
        self,
        device_type: Optional[str] = None,
        provision_status: Optional[str] = None,
        provision_target: Optional[str] = None
    ) -> list:
        """List all devices. See DeviceManager.list() for details."""
        from .devices import DeviceManager
        manager = DeviceManager(self)
        return manager.list(
            device_type=device_type,
            provision_status=provision_status,
            provision_target=provision_target
        )

    def get_device(self, serial_number: str) -> dict:
        """Get device status. See DeviceManager.get() for details."""
        from .devices import DeviceManager
        manager = DeviceManager(self)
        return manager.get(serial_number)

    def provision_device(self, serial_number: str, device_type: str, **kwargs) -> dict:
        """Provision a device. See DeviceManager.provision() for details."""
        from .devices import DeviceManager
        manager = DeviceManager(self)
        return manager.provision(serial_number, device_type, **kwargs)

    def list_scripts(self, include_content: bool = False) -> list:
        """List all scripts. See ScriptManager.list() for details."""
        from .scripts import ScriptManager
        manager = ScriptManager(self)
        return manager.list(include_content=include_content)

    def create_script(self, name: str, content: str) -> dict:
        """Create a script. See ScriptManager.create() for details."""
        from .scripts import ScriptManager
        manager = ScriptManager(self)
        return manager.create(name, content)

    def list_fortimanagers(self) -> list:
        """List FortiManagers registered for ZTP."""
        response = self._request("GET", "/setting/fortimanagers")

        if response.status_code != 200:
            raise APIError(f"API request failed: {response.status_code} - {response.text}")

        data = response.json()
        fortimanagers = data.get("fortiManagers") or []

        return [
            {
                "oid": fmg.get("oid"),
                "serial_number": fmg.get("sn"),
                "ip_address": fmg.get("ip"),
                "script_oid": fmg.get("scriptOid"),
                "update_time": fmg.get("updateTime")
            }
            for fmg in fortimanagers
        ]


class FortiZTPError(Exception):
    """Base exception for FortiZTP errors."""
    pass


class AuthenticationError(FortiZTPError):
    """Authentication failed."""
    pass


class APIError(FortiZTPError):
    """API request failed."""
    pass
