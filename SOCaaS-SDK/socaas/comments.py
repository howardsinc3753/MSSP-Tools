"""
SOCaaS Comment Management
"""

from typing import List


class CommentManager:
    """
    Manage comments on SOCaaS alerts and service requests.
    """

    def __init__(self, client):
        """
        Initialize CommentManager.

        Args:
            client: SOCaaSClient instance
        """
        self.client = client

    def list(self, module: str, uuid: str) -> List[dict]:
        """
        Get comments for an alert or service request.

        Args:
            module: "alerts" or "service_request"
            uuid: UUID of the alert or service request

        Returns:
            List of comment objects with:
            - id: Comment ID
            - content: Comment text
            - tag: Comment tag/label
            - created_datetime: Creation timestamp
            - author: Comment author
        """
        params = {"module": module, "uuid": uuid}
        response = self.client._request("GET", "/socaasAPI/v1/comment", params=params)
        response.raise_for_status()
        return self.client._extract_data(response.json()) or []

    def list_for_alert(self, alert_uuid: str) -> List[dict]:
        """Get comments for an alert."""
        return self.list("alerts", alert_uuid)

    def list_for_service_request(self, sr_uuid: str) -> List[dict]:
        """Get comments for a service request."""
        return self.list("service_request", sr_uuid)

    def create(
        self,
        module: str,
        related_uuid: str,
        content: str,
        tag: str = ""
    ) -> dict:
        """
        Create a comment on an alert or service request.

        Args:
            module: "alerts" or "service_request"
            related_uuid: UUID of the alert or service request
            content: Comment text
            tag: Must be empty string. The SOCaaS API returns
                 InvalidRequest (code 14) for non-empty tag values.

        Notes:
            - tag must be an empty string (default).
            - Service request comments may return HTTP 500 due to an API
              limitation; alert comments are supported.

        Returns:
            Created comment object with:
            - content: Comment text
            - create_user: Author (e.g., "APIuser(uuid)")
            - created_date: ISO timestamp
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
        response = self.client._request("POST", "/socaasAPI/v1/comment", json=payload)
        response.raise_for_status()
        return self.client._extract_data(response.json())

    def create_for_alert(self, alert_uuid: str, content: str, tag: str = "") -> dict:
        """Create a comment on an alert."""
        return self.create("alerts", alert_uuid, content, tag)

    def create_for_service_request(self, sr_uuid: str, content: str, tag: str = "") -> dict:
        """
        Create a comment on a service request.

        Note:
            The SOCaaS SR comment API currently returns HTTP 500 in some
            environments. This is an API-side limitation, not an SDK error.
        """
        return self.create("service_request", sr_uuid, content, tag)
