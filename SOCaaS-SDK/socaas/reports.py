"""
SOCaaS Report Management
"""

from typing import List


class ReportManager:
    """
    Manage SOCaaS reports.

    Reports are generated security reports that can be downloaded.
    """

    def __init__(self, client):
        """
        Initialize ReportManager.

        Args:
            client: SOCaaSClient instance
        """
        self.client = client

    def list(self) -> List[dict]:
        """
        Get list of all available reports.

        Returns:
            List of report objects with file info:
            - uuid: Report UUID
            - name: Report name
            - file_portal_uuid: File UUID for download
            - created_datetime: Creation timestamp
            - client_name: Client name (MSSP)
        """
        response = self.client._request("GET", "/socaasAPI/v1/report")
        response.raise_for_status()
        return self.client._extract_data(response.json()) or []

    def get_by_client(self, client_uuid: str) -> List[dict]:
        """
        Get all reports for a specific MSSP client.

        Args:
            client_uuid: Client UUID from list_clients()

        Returns:
            List of report objects for the client
        """
        response = self.client._request("GET", f"/socaasAPI/v1/report/client/{client_uuid}")
        response.raise_for_status()
        return self.client._extract_data(response.json()) or []
