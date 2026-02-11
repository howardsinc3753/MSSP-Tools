"""
SOCaaS Service Request Management
"""

from typing import Any, Dict, List, Optional


# Service request type mappings
# Note: "technicalassitance" spelling matches the SOCaaS API (intentional typo in API)
SERVICE_REQUEST_TYPES = {
    "devicedecommissioning": "Device Decommissioning",
    "escalationmatrixupdate": "Escalation Matrix Update",
    "newmonitoringrequest": "New Monitoring Request",
    "newreportrequest": "New Report Request",
    "portalaccess": "Portal Access",
    "servicedecommissioning": "Service Decommissioning",
    "serviceenquiry": "Service Enquiry",
    "technicalassitance": "Technical Assistance",  # API spelling (missing 's')
    "whitelistrequest": "Whitelist Request",
    "others": "Others",
}


class ServiceRequestManager:
    """
    Manage SOCaaS service requests (support tickets).

    Service requests are support tickets submitted to the SOCaaS team for:
    - Device decommissioning
    - Escalation matrix updates
    - New monitoring requests
    - Report requests
    - Portal access
    - Technical assistance
    - Whitelist requests
    """

    def __init__(self, client):
        """
        Initialize ServiceRequestManager.

        Args:
            client: SOCaaSClient instance
        """
        self.client = client

    def list(self) -> List[dict]:
        """
        Get list of all service requests.

        Returns:
            List of service request objects with:
            - uuid: Service request UUID
            - id: Service request ID (numeric)
            - title: Request title
            - type: Request type code
            - status: Request status
            - created_datetime: Creation timestamp
            - client_name: Client name (MSSP)
        """
        response = self.client._request("GET", "/socaasAPI/v1/service-request")
        response.raise_for_status()
        return self.client._extract_data(response.json()) or []

    def get(self, sr_uuid: str) -> dict:
        """
        Get service request details by UUID.

        Args:
            sr_uuid: Service request UUID

        Returns:
            Service request details including:
            - title, type, notes
            - status, timestamps
            - timeline: Status history
            - attachments: Attached files
        """
        response = self.client._request("GET", f"/socaasAPI/v1/service-request/{sr_uuid}")
        response.raise_for_status()
        return self.client._extract_data(response.json())

    def create(
        self,
        title: str,
        request_type: str,
        notes: str,
        notification: Optional[str] = None,
        client_name: Optional[str] = None,
        attachment_files: Optional[List[dict]] = None,
        translated_title: str = "",
        translated_notes: str = ""
    ) -> dict:
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

        Valid request_type values:
            - devicedecommissioning
            - escalationmatrixupdate
            - newmonitoringrequest
            - newreportrequest
            - portalaccess
            - servicedecommissioning
            - serviceenquiry
            - technicalassitance (note: API spelling, missing 's')
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
        response = self.client._request("POST", "/socaasAPI/v1/service-request", json=payload)
        response.raise_for_status()
        return self.client._extract_data(response.json())

    def get_by_client(self, client_uuid: str) -> List[dict]:
        """
        Get all service requests for a specific MSSP client.

        Args:
            client_uuid: Client UUID from list_clients()

        Returns:
            List of service request objects for the client
        """
        response = self.client._request("GET", f"/socaasAPI/v1/service-request/client/{client_uuid}")
        response.raise_for_status()
        return self.client._extract_data(response.json()) or []
