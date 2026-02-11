"""
SOCaaS Alert Management
"""

from typing import Any, Dict, List, Optional


class AlertManager:
    """
    Manage SOCaaS security alerts.

    Alerts are security incidents escalated by the SOC team with:
    - Status: Inprogress, Completed
    - SLA status: Met, Missed
    - Severity: Critical, High, Medium, Low
    - IOCs, events, endpoints, forensic data
    """

    def __init__(self, client):
        """
        Initialize AlertManager.

        Args:
            client: SOCaaSClient instance
        """
        self.client = client

    def list(
        self,
        alert_id: Optional[int] = None,
        created_date_from: Optional[str] = None,
        created_date_to: Optional[str] = None
    ) -> List[dict]:
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
            List of alert objects with keys:
            - uuid: Alert UUID (use for get, update, comments)
            - id: Alert ID (numeric)
            - name: Alert title
            - status: Alert status
            - severity: Alert severity
            - created_datetime: Creation timestamp
            - client_name: Client name (MSSP)
        """
        params = {}
        if alert_id:
            params["alert_id"] = alert_id
        if created_date_from:
            params["created_date_from"] = created_date_from
        if created_date_to:
            params["created_date_to"] = created_date_to

        response = self.client._request("GET", "/socaasAPI/v1/alert", params=params)
        response.raise_for_status()
        return self.client._extract_data(response.json()) or []

    def get(self, alert_uuid: str) -> dict:
        """
        Get alert details by UUID.

        Returns detailed alert information including:
        - Related alerts, assets, attachments, endpoints
        - Events, event users, forensic analysis
        - Indicators of Compromise (IOCs)

        Args:
            alert_uuid: Alert UUID

        Returns:
            Alert details object with:
            - uuid, id, name, description
            - status, severity, category
            - indicators: List of IOCs
            - events: Security events
            - endpoints: Affected hosts
            - attachments: File attachments
            - forensic_analysis: Forensic data
        """
        response = self.client._request("GET", f"/socaasAPI/v1/alert/{alert_uuid}")
        response.raise_for_status()
        return self.client._extract_data(response.json())

    def update_status(
        self,
        alert_uuid: str,
        status: str,
        closure_notes: Optional[str] = None
    ) -> Any:
        """
        Update alert status.

        Args:
            alert_uuid: Alert UUID
            status: New status ("inprogress" or "completed")
            closure_notes: Optional closure notes

        Returns:
            API response data (dict) on success. Raises HTTPError on failure.

        Note:
            Cannot change status from 'Completed' to other statuses.
        """
        data = {"status": status}
        if closure_notes:
            data["closure_notes"] = closure_notes

        payload = {"param": {"data": data}}
        response = self.client._request(
            "POST",
            f"/socaasAPI/v1/alert/{alert_uuid}",
            json=payload
        )
        response.raise_for_status()
        return self.client._extract_data(response.json())

    def get_by_client(self, client_uuid: str) -> List[dict]:
        """
        Get all alerts for a specific MSSP client.

        Args:
            client_uuid: Client UUID from list_clients()

        Returns:
            List of alert objects for the client
        """
        response = self.client._request("GET", f"/socaasAPI/v1/alert/client/{client_uuid}")
        response.raise_for_status()
        return self.client._extract_data(response.json()) or []
