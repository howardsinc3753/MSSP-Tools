"""
SOCaaS File Management
"""

import base64
from typing import Optional


class FileManager:
    """
    Manage SOCaaS file downloads.

    Download attachments and reports from SOCaaS.
    """

    def __init__(self, client):
        """
        Initialize FileManager.

        Args:
            client: SOCaaSClient instance
        """
        self.client = client

    def download(self, module: str, file_portal_uuid: str) -> dict:
        """
        Download an attachment or report file.

        Args:
            module: "attachment" or "report"
            file_portal_uuid: File portal UUID

        Returns:
            Dict with:
            - filename: Original filename
            - content_type: MIME type
            - file_content: Base64 encoded content
        """
        params = {"module": module, "file-portal-uuid": file_portal_uuid}
        response = self.client._request("GET", "/socaasAPI/v1/file", params=params)
        response.raise_for_status()
        return self.client._extract_data(response.json())

    def download_attachment(self, file_portal_uuid: str) -> dict:
        """Download an attachment file."""
        return self.download("attachment", file_portal_uuid)

    def download_report(self, file_portal_uuid: str) -> dict:
        """Download a report file."""
        return self.download("report", file_portal_uuid)

    def save(self, file_data: dict, output_path: Optional[str] = None) -> str:
        """
        Save downloaded file to disk.

        Args:
            file_data: Response from download/download_attachment/download_report
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
