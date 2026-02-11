"""
SOCaaS MSSP Client Management
"""

from typing import List


class ClientManager:
    """
    Manage MSSP clients in SOCaaS.

    MSSP accounts can manage multiple client (tenant) organizations.
    Use client_uuid to filter alerts, service requests, and reports by client.
    """

    def __init__(self, client):
        """
        Initialize ClientManager.

        Args:
            client: SOCaaSClient instance
        """
        self.client = client

    def list(self) -> List[dict]:
        """
        Get list of all clients managed by the MSSP.

        Returns:
            List of client objects with:
            - client_uuid: Client UUID (use for filtering)
            - client_name: Client display name
            - modify_date: Last modification timestamp
        """
        response = self.client._request("GET", "/socaasAPI/v1/client")
        response.raise_for_status()
        return self.client._extract_data(response.json()) or []
