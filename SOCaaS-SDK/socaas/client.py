"""
SOCaaS API Client
Base client for SOCaaS API authentication and requests.
"""

import os
import time
import requests
import yaml
from typing import Any, Dict, List, Optional


class SOCaaSClient:
    """
    SOCaaS API Client for Security Operations Center as a Service.

    Provides access to Fortinet SOCaaS features:
    - Security Alerts (list, details, update status)
    - Service Requests (list, details, create)
    - Comments (on alerts and service requests)
    - Reports (download)
    - MSSP Client Management (multi-tenant)
    - MSSP Onboarding

    Example:
        # Method 1: Direct credentials
        client = SOCaaSClient(
            username="your-api-user-id",
            password="your-api-password"
        )

        # Method 2: From credential file
        client = SOCaaSClient.from_credential_file("credentials.yaml")

        # Method 3: From environment variables
        client = SOCaaSClient.from_env()

        # Use the client
        alerts = client.list_alerts()
        clients = client.list_clients()

    Rate Limits:
        - GET endpoints: 100 requests per minute
        - POST endpoints: 5 requests per minute
    """

    AUTH_URL = "https://customerapiauth.fortinet.com/api/v1/oauth/token/"
    BASE_URL = "https://socaas.mss.fortinet.com"
    CLIENT_ID = "socaas"

    def __init__(
        self,
        username: str,
        password: str,
        client_id: str = "socaas",
        auth_url: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        """
        Initialize SOCaaS client.

        Args:
            username: FortiCloud API User ID (UUID format)
            password: FortiCloud API Password
            client_id: OAuth client ID (default: "socaas")
            auth_url: Override authentication URL
            base_url: Override API base URL
        """
        self.username = username
        self.password = password
        self.client_id = client_id
        self.auth_url = auth_url or self.AUTH_URL
        self.base_url = base_url or self.BASE_URL
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expiry_time: float = 0
        self._token_refresh_buffer: int = 60  # Refresh 60 seconds before expiry
        self.debug = False

    def _log(self, message: str):
        """Print debug messages if debug mode is enabled."""
        if self.debug:
            print(f"[SOCaaS] {message}")

    @classmethod
    def from_credential_file(cls, filepath: str) -> "SOCaaSClient":
        """
        Create client from a YAML credential file.

        Expected file format:
            username: "your-api-user-id"
            password: "your-api-password"

        Or with nested structure:
            socaas:
              username: "your-api-user-id"
              password: "your-api-password"

        Args:
            filepath: Path to YAML credential file

        Returns:
            SOCaaSClient instance
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Credential file not found: {filepath}")

        with open(filepath, 'r') as f:
            creds = yaml.safe_load(f) or {}

        # Check for nested structure first
        nested_creds = creds.get("socaas", {})

        username = nested_creds.get("username") or creds.get("username") or creds.get("USERNAME")
        password = nested_creds.get("password") or creds.get("password") or creds.get("PASSWORD")
        client_id = nested_creds.get("client_id") or creds.get("client_id") or creds.get("CLIENT_ID") or "socaas"
        auth_url = nested_creds.get("auth_url") or creds.get("auth_url") or creds.get("AUTH_URL")
        base_url = nested_creds.get("base_url") or creds.get("base_url") or creds.get("BASE_URL")

        if not username or not password:
            raise ValueError("Credential file must contain username and password")

        return cls(
            username=username,
            password=password,
            client_id=client_id,
            auth_url=auth_url,
            base_url=base_url
        )

    @classmethod
    def from_env(cls) -> "SOCaaSClient":
        """
        Create client from environment variables.

        Required environment variables:
            SOCAAS_USERNAME: FortiCloud API User ID
            SOCAAS_PASSWORD: FortiCloud API Password

        Optional:
            SOCAAS_CLIENT_ID: OAuth client ID
            SOCAAS_AUTH_URL: Authentication URL
            SOCAAS_BASE_URL: API base URL

        Returns:
            SOCaaSClient instance
        """
        username = os.environ.get("SOCAAS_USERNAME")
        password = os.environ.get("SOCAAS_PASSWORD")
        client_id = os.environ.get("SOCAAS_CLIENT_ID", "socaas")
        auth_url = os.environ.get("SOCAAS_AUTH_URL")
        base_url = os.environ.get("SOCAAS_BASE_URL")

        if not username or not password:
            raise ValueError(
                "Environment variables SOCAAS_USERNAME and SOCAAS_PASSWORD must be set"
            )

        return cls(
            username=username,
            password=password,
            client_id=client_id,
            auth_url=auth_url,
            base_url=base_url
        )

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
            "client_id": self.client_id,
            "grant_type": "password"
        }

        self._log(f"Authenticating to {self.auth_url}")
        response = requests.post(self.auth_url, json=payload, timeout=30)

        if response.status_code != 200:
            raise AuthenticationError(
                f"Authentication failed: {response.status_code} - {response.text}"
            )

        data = response.json()
        if "access_token" not in data:
            raise AuthenticationError(f"No access_token in response: {data}")

        self._access_token = data["access_token"]
        self._refresh_token = data.get("refresh_token")
        expires_in = data.get("expires_in", 36000)
        self._token_expiry_time = time.time() + expires_in

        self._log(f"Authenticated. Token expires in {expires_in}s")
        return self._access_token

    def _is_token_expired(self) -> bool:
        """Check if token is expired or about to expire."""
        if not self._access_token:
            return True
        return time.time() >= (self._token_expiry_time - self._token_refresh_buffer)

    def get_token(self) -> str:
        """Get current access token, authenticating or refreshing if needed."""
        if self._is_token_expired():
            self._authenticate()
        return self._access_token

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
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        # Merge custom headers with auth headers (auth headers take precedence)
        custom_headers = kwargs.pop("headers", None) or {}
        merged_headers = {**custom_headers, **self._headers()}
        kwargs["headers"] = merged_headers

        kwargs.setdefault("timeout", 60)

        self._log(f"{method} {url}")
        response = requests.request(method, url, **kwargs)

        # Retry once on 401 with fresh token
        if response.status_code == 401 and _retry_on_401:
            self._authenticate()
            kwargs["headers"] = {**custom_headers, **self._headers()}
            response = requests.request(method, url, **kwargs)

        return response

    def _extract_data(self, response: dict) -> Any:
        """Extract data from standard SOCaaS response format."""
        if "result" in response:
            result = response["result"]
            if result.get("status") != 0:
                errors = result.get("errorArr", [])
                message = result.get("message", "Unknown error")
                raise APIError(f"API Error (status={result['status']}): {message} - {errors}")
            return result.get("data")
        return response

    # =========================================================================
    # CONVENIENCE METHODS - Delegate to specific managers
    # =========================================================================

    def list_alerts(
        self,
        alert_id: Optional[int] = None,
        created_date_from: Optional[str] = None,
        created_date_to: Optional[str] = None
    ) -> List[dict]:
        """List alerts. See AlertManager.list() for details."""
        from .alerts import AlertManager
        return AlertManager(self).list(
            alert_id=alert_id,
            created_date_from=created_date_from,
            created_date_to=created_date_to
        )

    def get_alert(self, alert_uuid: str) -> dict:
        """Get alert details. See AlertManager.get() for details."""
        from .alerts import AlertManager
        return AlertManager(self).get(alert_uuid)

    def update_alert_status(
        self,
        alert_uuid: str,
        status: str,
        closure_notes: Optional[str] = None
    ) -> Any:
        """Update alert status. See AlertManager.update_status() for details."""
        from .alerts import AlertManager
        return AlertManager(self).update_status(alert_uuid, status, closure_notes)

    def get_alerts_by_client(self, client_uuid: str) -> List[dict]:
        """Get alerts for a client. See AlertManager.get_by_client() for details."""
        from .alerts import AlertManager
        return AlertManager(self).get_by_client(client_uuid)

    def list_service_requests(self) -> List[dict]:
        """List service requests. See ServiceRequestManager.list() for details."""
        from .service_requests import ServiceRequestManager
        return ServiceRequestManager(self).list()

    def get_service_request(self, sr_uuid: str) -> dict:
        """Get service request details. See ServiceRequestManager.get() for details."""
        from .service_requests import ServiceRequestManager
        return ServiceRequestManager(self).get(sr_uuid)

    def create_service_request(self, title: str, request_type: str, notes: str, **kwargs) -> dict:
        """Create service request. See ServiceRequestManager.create() for details."""
        from .service_requests import ServiceRequestManager
        return ServiceRequestManager(self).create(title, request_type, notes, **kwargs)

    def list_clients(self) -> List[dict]:
        """List MSSP clients. See ClientManager.list() for details."""
        from .clients import ClientManager
        return ClientManager(self).list()

    def list_reports(self) -> List[dict]:
        """List reports. See ReportManager.list() for details."""
        from .reports import ReportManager
        return ReportManager(self).list()

    def list_alert_comments(self, alert_uuid: str) -> List[dict]:
        """List comments for an alert. See CommentManager.list_for_alert() for details."""
        from .comments import CommentManager
        return CommentManager(self).list_for_alert(alert_uuid)

    def create_alert_comment(self, alert_uuid: str, content: str, tag: str = "") -> dict:
        """Create comment on alert. See CommentManager.create_for_alert() for details."""
        from .comments import CommentManager
        return CommentManager(self).create_for_alert(alert_uuid, content, tag)


class SOCaaSError(Exception):
    """Base exception for SOCaaS errors."""
    pass


class AuthenticationError(SOCaaSError):
    """Authentication failed."""
    pass


class APIError(SOCaaSError):
    """API request failed."""
    pass
