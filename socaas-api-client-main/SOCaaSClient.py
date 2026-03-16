"""
SOCaaS API Client SDK
Fortinet SOCaaS (Security Operations Center as a Service) Python SDK

Authentication: OAuth 2.0 Password Grant
Base URL: https://socaas.mss.fortinet.com
Auth URL: https://customerapiauth.fortinet.com/api/v1/oauth/token/
"""

import requests
import time
import base64
from typing import Optional, List, Dict, Any
from datetime import datetime


class SOCaaSClient:
    """
    Python SDK for Fortinet SOCaaS API.

    Provides methods for:
    - Alerts: list, get details, update status, get by client
    - Comments: list, create (for alerts and service requests)
    - Files: download attachments and reports
    - Service Requests: list, get details, create, get by client
    - Reports: list, get by client
    - Clients: list (MSSP)
    - MSSP Onboarding: get info, create onboarding request
    """

    def __init__(self, username: str, password: str, client_id: str = "socaas",
                 authentication_url: str = "https://customerapiauth.fortinet.com/api/v1/oauth/token/",
                 base_url: str = "https://socaas.mss.fortinet.com"):
        """
        Initialize the SOCaaS API client.

        Args:
            username: API User ID (UUID format from FortiCloud)
            password: API User password
            client_id: OAuth client ID (default: "socaas")
            authentication_url: OAuth token endpoint
            base_url: SOCaaS API base URL
        """
        self.username = username
        self.password = password
        self.client_id = client_id
        self.authentication_url = authentication_url
        self.base_url = base_url
        self.token = None
        self.refresh_token = None
        self.token_expiry = 0
        self.debug = False

    def _log(self, message: str):
        """Print debug messages if debug mode is enabled."""
        if self.debug:
            print(f"[SOCaaS] {message}")

    def _authenticate(self):
        """Authenticate and retrieve a new bearer token."""
        payload = {
            "username": self.username,
            "password": self.password,
            "client_id": self.client_id,
            "grant_type": "password"
        }
        response = requests.post(self.authentication_url, json=payload)
        if response.status_code != 200:
            self._log(f"Auth error: {response.status_code} - {response.text}")
        response.raise_for_status()

        data = response.json()
        self.token = data["access_token"]
        self.refresh_token = data.get("refresh_token")
        expires_in = data.get("expires_in", 36000)
        self.token_expiry = time.time() + expires_in - 60  # 60s buffer
        self._log(f"Authenticated. Token expires in {expires_in}s")

    def _refresh_token_if_needed(self):
        """Refresh the token if it has expired or is about to expire."""
        if not self.token or time.time() >= self.token_expiry:
            self._authenticate()

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """
        Make an authenticated API request.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments passed to requests

        Returns:
            JSON response as dict
        """
        self._refresh_token_if_needed()

        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {self.token}"
        kwargs["headers"] = headers

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        self._log(f"{method} {url}")

        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()

    def _extract_data(self, response: dict) -> Any:
        """Extract data from standard SOCaaS response format."""
        if "result" in response:
            result = response["result"]
            if result.get("status") != 0:
                errors = result.get("errorArr", [])
                raise Exception(f"API Error (status={result['status']}): {errors}")
            return result.get("data")
        return response

    # =========================================================================
    # ALERTS
    # =========================================================================

    def list_alerts(self, alert_id: Optional[int] = None,
                    created_date_from: Optional[str] = None,
                    created_date_to: Optional[str] = None) -> List[dict]:
        """
        Get list of alerts.

        Returns alerts where:
        - Status is NOT: new, investigating, false positive, closed immature
        - escalated_to_incident = yes
        - SLA = missed or met

        Args:
            alert_id: Filter by specific Alert ID
            created_date_from: Filter from date (RFC3339, e.g., "2025-01-01T00:00:00Z")
            created_date_to: Filter to date (RFC3339)

        Returns:
            List of alert objects
        """
        params = {}
        if alert_id:
            params["alert_id"] = alert_id
        if created_date_from:
            params["created_date_from"] = created_date_from
        if created_date_to:
            params["created_date_to"] = created_date_to

        response = self._request("GET", "/socaasAPI/v1/alert", params=params)
        return self._extract_data(response)

    def get_alert(self, alert_uuid: str) -> dict:
        """
        Get alert details by UUID.

        Returns detailed alert information including:
        - Related alerts, assets, attachments, endpoints
        - Events, event users, forensic analysis, indicators (IOCs)

        Args:
            alert_uuid: Alert UUID

        Returns:
            Alert details object
        """
        response = self._request("GET", f"/socaasAPI/v1/alert/{alert_uuid}")
        return self._extract_data(response)

    def update_alert_status(self, alert_uuid: str, status: str,
                           closure_notes: Optional[str] = None) -> bool:
        """
        Update alert status.

        Args:
            alert_uuid: Alert UUID
            status: New status ("inprogress" or "completed")
            closure_notes: Optional closure notes

        Returns:
            True if successful

        Note:
            Cannot change status from 'Completed' to other statuses.
        """
        data = {"status": status}
        if closure_notes:
            data["closure_notes"] = closure_notes

        payload = {"param": {"data": data}}
        response = self._request("POST", f"/socaasAPI/v1/alert/{alert_uuid}", json=payload)
        return self._extract_data(response)

    def get_alerts_by_client(self, client_uuid: str) -> List[dict]:
        """
        Get all alerts for a specific client.

        Args:
            client_uuid: Client UUID

        Returns:
            List of alert objects for the client
        """
        response = self._request("GET", f"/socaasAPI/v1/alert/client/{client_uuid}")
        return self._extract_data(response)

    # =========================================================================
    # COMMENTS
    # =========================================================================

    def list_comments(self, module: str, uuid: str) -> List[dict]:
        """
        Get comments for an alert or service request.

        Args:
            module: "alerts" or "service_request"
            uuid: UUID of the alert or service request

        Returns:
            List of comment objects
        """
        params = {"module": module, "uuid": uuid}
        response = self._request("GET", "/socaasAPI/v1/comment", params=params)
        return self._extract_data(response)

    def list_alert_comments(self, alert_uuid: str) -> List[dict]:
        """Get comments for an alert."""
        return self.list_comments("alerts", alert_uuid)

    def list_service_request_comments(self, sr_uuid: str) -> List[dict]:
        """Get comments for a service request."""
        return self.list_comments("service_request", sr_uuid)

    def create_comment(self, module: str, related_uuid: str, content: str,
                       tag: str = "") -> dict:
        """
        Create a comment on an alert or service request.

        Args:
            module: "alerts" or "service_request"
            related_uuid: UUID of the alert or service request
            content: Comment text
            tag: Optional tag/label

        Returns:
            Created comment object
        """
        payload = {
            "param": {
                "data": {
                    "content": content,
                    "related": module,
                    "related_uuid": related_uuid,
                    "tag": tag
                }
            }
        }
        response = self._request("POST", "/socaasAPI/v1/comment", json=payload)
        return self._extract_data(response)

    def create_alert_comment(self, alert_uuid: str, content: str, tag: str = "") -> dict:
        """Create a comment on an alert."""
        return self.create_comment("alerts", alert_uuid, content, tag)

    def create_service_request_comment(self, sr_uuid: str, content: str, tag: str = "") -> dict:
        """Create a comment on a service request."""
        return self.create_comment("service_request", sr_uuid, content, tag)

    # =========================================================================
    # FILES
    # =========================================================================

    def download_file(self, module: str, file_portal_uuid: str) -> dict:
        """
        Download an attachment or report file.

        Args:
            module: "attachment" or "report"
            file_portal_uuid: File portal UUID

        Returns:
            Dict with filename, content_type, and file_content (base64)
        """
        params = {"module": module, "file-portal-uuid": file_portal_uuid}
        response = self._request("GET", "/socaasAPI/v1/file", params=params)
        return self._extract_data(response)

    def download_attachment(self, file_portal_uuid: str) -> dict:
        """Download an attachment file."""
        return self.download_file("attachment", file_portal_uuid)

    def download_report(self, file_portal_uuid: str) -> dict:
        """Download a report file."""
        return self.download_file("report", file_portal_uuid)

    def save_file(self, file_data: dict, output_path: Optional[str] = None) -> str:
        """
        Save downloaded file to disk.

        Args:
            file_data: Response from download_file/download_attachment/download_report
            output_path: Optional output path (defaults to original filename)

        Returns:
            Path to saved file
        """
        filename = file_data.get("filename", "download")
        content = file_data.get("file_content", "")

        if output_path is None:
            output_path = filename

        # Handle both base64 string and byte array formats
        if isinstance(content, str):
            file_bytes = base64.b64decode(content)
        elif isinstance(content, list):
            file_bytes = bytes(content)
        else:
            file_bytes = content

        with open(output_path, "wb") as f:
            f.write(file_bytes)

        return output_path

    # =========================================================================
    # SERVICE REQUESTS
    # =========================================================================

    def list_service_requests(self) -> List[dict]:
        """
        Get list of all service requests.

        Returns:
            List of service request objects
        """
        response = self._request("GET", "/socaasAPI/v1/service-request")
        return self._extract_data(response)

    def get_service_request(self, sr_uuid: str) -> dict:
        """
        Get service request details by UUID.

        Args:
            sr_uuid: Service request UUID

        Returns:
            Service request details (includes timeline, attachments)
        """
        response = self._request("GET", f"/socaasAPI/v1/service-request/{sr_uuid}")
        return self._extract_data(response)

    def create_service_request(self, title: str, request_type: str, notes: str,
                               notification: Optional[str] = None,
                               client_name: Optional[str] = None,
                               attachment_files: Optional[List[dict]] = None,
                               translated_title: str = "",
                               translated_notes: str = "") -> dict:
        """
        Create a new service request.

        Args:
            title: Request title
            request_type: Type of request (see SERVICE_REQUEST_TYPES)
            notes: Request description
            notification: Email for notifications
            client_name: Client name (required for MSSPs with multiple clients)
            attachment_files: List of file dicts with filename, content_type, file_content
            translated_title: Translated title
            translated_notes: Translated notes

        Returns:
            Created service request object

        Service Request Types:
            - devicedecommissioning
            - escalationmatrixupdate
            - newmonitoringrequest
            - newreportrequest
            - portalaccess
            - servicedecommissioning
            - serviceenquiry
            - technicalassitance
            - whitelistrequest
            - others
        """
        data = {
            "title": title,
            "type": request_type,
            "notes": notes,
            "translated_title": translated_title,
            "translated_notes": translated_notes,
        }

        if notification:
            data["notification"] = notification
        if client_name:
            data["client_name"] = client_name
        if attachment_files:
            data["attachment_files"] = attachment_files

        payload = {"param": {"data": data}}
        response = self._request("POST", "/socaasAPI/v1/service-request", json=payload)
        return self._extract_data(response)

    def get_service_requests_by_client(self, client_uuid: str) -> List[dict]:
        """
        Get all service requests for a specific client.

        Args:
            client_uuid: Client UUID

        Returns:
            List of service request objects
        """
        response = self._request("GET", f"/socaasAPI/v1/service-request/client/{client_uuid}")
        return self._extract_data(response)

    # =========================================================================
    # REPORTS
    # =========================================================================

    def list_reports(self) -> List[dict]:
        """
        Get list of all available reports.

        Returns:
            List of report objects with file info
        """
        response = self._request("GET", "/socaasAPI/v1/report")
        return self._extract_data(response)

    def get_reports_by_client(self, client_uuid: str) -> List[dict]:
        """
        Get all reports for a specific client.

        Args:
            client_uuid: Client UUID

        Returns:
            List of report objects
        """
        response = self._request("GET", f"/socaasAPI/v1/report/client/{client_uuid}")
        return self._extract_data(response)

    # =========================================================================
    # CLIENTS (MSSP)
    # =========================================================================

    def list_clients(self) -> List[dict]:
        """
        Get list of all clients managed by the MSSP.

        Returns:
            List of client objects with client_uuid, client_name, modify_date
        """
        response = self._request("GET", "/socaasAPI/v1/client")
        return self._extract_data(response)

    # =========================================================================
    # MSSP ONBOARDING
    # =========================================================================

    def get_onboarding_info(self) -> dict:
        """
        Get pre-onboarding information required for MSSP client onboarding.

        Returns:
            Dict with:
            - clients: Existing client names
            - assets: Available assets to onboard
            - fortiAnalyzer_cloud_location: Available FAZ Cloud locations
            - country_soc_fazs: Country-specific SOC FAZ collectors
            - existing_contacts: Existing contacts for escalation paths
        """
        response = self._request("GET", "/socaasAPI/v1/mssp-onboarding-info")
        return self._extract_data(response)

    def create_onboarding_request(self, client_name: str, devices: List[dict],
                                  monitoring_subnet: List[dict],
                                  contacts: List[dict],
                                  escalation_paths: List[dict],
                                  notification: Optional[str] = None,
                                  notes: Optional[str] = None,
                                  log_collection: Optional[dict] = None) -> dict:
        """
        Create a new MSSP client onboarding request.

        Args:
            client_name: New client name (must be unique)
            devices: List of device objects to onboard
            monitoring_subnet: List of subnet objects (include/exclude)
            contacts: List of contact objects
            escalation_paths: List of escalation path objects
            notification: Notification email
            notes: Additional notes
            log_collection: Log collection config (required for non-onboarded assets)

        Returns:
            Dict with status and service_request_uuid

        Device Object:
            - serial_number (required)
            - hostname, location, description
            - ha_mode (bool), master
            - is_vdom (bool), vdom (required if is_vdom)

        Monitoring Subnet Object:
            - type: "include" or "exclude"
            - name: Subnet label
            - criticality: "Critical", "High", "Medium", "Low"
            - subnet: CIDR or range format

        Contact Object:
            - name, team_emails, primary_phone, backup_phone, is_default

        Escalation Path Object:
            - name, primary_contact, secondary_contact
            - included_subnets, excluded_subnets, included_devices
        """
        data = {
            "client_name": client_name,
            "devices": devices,
            "monitoring_subnet": monitoring_subnet,
            "contacts": contacts,
            "escalation_paths": escalation_paths,
        }

        if notification:
            data["notification"] = notification
        if notes:
            data["notes"] = notes
        if log_collection:
            data["log_collection"] = log_collection

        payload = {"param": {"data": data}}
        response = self._request("POST", "/socaasAPI/v1/mssp-customer-onboarding", json=payload)
        return self._extract_data(response)


# =============================================================================
# SERVICE REQUEST TYPES
# =============================================================================

SERVICE_REQUEST_TYPES = {
    "devicedecommissioning": "Device Decommissioning",
    "escalationmatrixupdate": "Escalation Matrix Update",
    "newmonitoringrequest": "New Monitoring Request",
    "newreportrequest": "New Report Request",
    "portalaccess": "Portal Access",
    "servicedecommissioning": "Service Decommissioning",
    "serviceenquiry": "Service Enquiry",
    "technicalassitance": "Technical Assistance",
    "whitelistrequest": "Whitelist Request",
    "others": "Others",
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_client_from_env() -> SOCaaSClient:
    """
    Create SOCaaSClient from environment variables.

    Required env vars:
        USERNAME, PASSWORD

    Optional env vars:
        CLIENT_ID (default: "socaas")
        AUTH_URL (default: https://customerapiauth.fortinet.com/api/v1/oauth/token/)
        BASE_URL (default: https://socaas.mss.fortinet.com)
    """
    import os
    from dotenv import load_dotenv

    load_dotenv()

    return SOCaaSClient(
        username=os.getenv("USERNAME"),
        password=os.getenv("PASSWORD"),
        client_id=os.getenv("CLIENT_ID", "socaas"),
        authentication_url=os.getenv("AUTH_URL", "https://customerapiauth.fortinet.com/api/v1/oauth/token/"),
        base_url=os.getenv("BASE_URL", "https://socaas.mss.fortinet.com"),
    )


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Option 1: Create from environment variables
    # client = create_client_from_env()

    # Option 2: Create directly
    client = SOCaaSClient(
        username="62A1AFE0-0119-46FB-8AC8-9D2D04315BEE",
        password="91298682ce2e55c2721666f835e547e0!1Aa",
    )
    client.debug = True

    try:
        # List alerts
        print("\n=== List Alerts ===")
        alerts = client.list_alerts()
        print(f"Found {len(alerts) if alerts else 0} alerts")

        if alerts:
            alert = alerts[0]
            print(f"First alert: {alert.get('name')} (UUID: {alert.get('uuid')})")

            # Get alert details
            print("\n=== Alert Details ===")
            details = client.get_alert(alert["uuid"])
            print(f"Status: {details.get('status')}, Severity: {details.get('severity')}")

            # List comments for alert
            print("\n=== Alert Comments ===")
            comments = client.list_alert_comments(alert["uuid"])
            print(f"Found {len(comments) if comments else 0} comments")

        # List service requests
        print("\n=== List Service Requests ===")
        srs = client.list_service_requests()
        print(f"Found {len(srs) if srs else 0} service requests")

        # List clients (MSSP)
        print("\n=== List Clients ===")
        clients = client.list_clients()
        print(f"Found {len(clients) if clients else 0} clients")

        # List reports
        print("\n=== List Reports ===")
        reports = client.list_reports()
        print(f"Found {len(reports) if reports else 0} reports")

    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
    except Exception as e:
        print(f"Error: {e}")
