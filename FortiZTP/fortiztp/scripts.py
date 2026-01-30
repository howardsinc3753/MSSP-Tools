"""
FortiZTP Script Management
Operations for listing, creating, and managing bootstrap CLI scripts.
"""

import requests
from typing import Any, Dict, List, Optional


class ScriptManager:
    """
    Manage FortiZTP pre-run CLI scripts.

    Scripts contain FortiGate CLI commands that execute during initial device
    setup (Zero Touch Provisioning). Use scripts for:

    - Initial network configuration (interfaces, VLANs, routing)
    - VPN tunnel setup (IPsec, SSL-VPN)
    - FortiManager registration
    - Security policies
    - Logging and SNMP configuration
    - Any CLI command that should run at first boot

    Example:
        from fortiztp import FortiZTPClient

        client = FortiZTPClient(username="...", password="...")
        scripts = ScriptManager(client)

        # List all scripts
        all_scripts = scripts.list()

        # List with content
        all_scripts = scripts.list(include_content=True)

        # Create a new script
        result = scripts.create(
            name="Site-Bootstrap",
            content='''
config system global
    set hostname "Branch-FGT"
end
config system interface
    edit "wan1"
        set mode dhcp
        set allowaccess ping https ssh
    next
end
'''
        )
        print(f"Created script OID: {result['script']['oid']}")

        # Use script OID when provisioning devices
        devices.provision(
            serial_number="FGT60F1234567890",
            device_type="FortiGate",
            provision_target="FortiManager",
            fortimanager_oid=123,
            external_controller_ip="192.168.1.100",
            script_oid=result['script']['oid']  # Use the script
        )
    """

    def __init__(self, client):
        """
        Initialize ScriptManager.

        Args:
            client: FortiZTPClient instance
        """
        self.client = client

    def list(self, include_content: bool = False) -> List[Dict[str, Any]]:
        """
        List all pre-run CLI scripts.

        Args:
            include_content: If True, fetch content for each script (slower)

        Returns:
            List of script dictionaries

        Example:
            # Quick list
            scripts = manager.list()

            # With content
            scripts = manager.list(include_content=True)
            for script in scripts:
                print(f"{script['name']}: {len(script.get('content', ''))} chars")
        """
        from .client import APIError

        response = self.client._request("GET", "/setting/scripts")

        if response.status_code != 200:
            raise APIError(f"API request failed: {response.status_code} - {response.text}")

        data = response.json()
        scripts = data.get("data") or []

        results = []
        for script in scripts:
            transformed = {
                "oid": script.get("oid"),
                "name": script.get("name"),
                "update_time": script.get("updateTime")
            }

            # Optionally fetch content
            if include_content and transformed["oid"]:
                content_response = self.client._request(
                    "GET",
                    f"/setting/scripts/{transformed['oid']}/content"
                )
                if content_response.status_code == 200:
                    try:
                        content_data = content_response.json()
                        transformed["content"] = (
                            content_data.get("content") or
                            content_data.get("script") or ""
                        )
                    except Exception:
                        transformed["content"] = content_response.text

            results.append(transformed)

        return results

    def get(self, script_oid: int, include_content: bool = True) -> Dict[str, Any]:
        """
        Get a specific script by OID.

        Args:
            script_oid: Script OID
            include_content: If True, fetch script content

        Returns:
            Script dictionary with name, oid, and optionally content

        Example:
            script = scripts.get(456)
            print(script['content'])
        """
        from .client import APIError

        # Get script metadata
        all_scripts = self.list(include_content=False)
        script = next((s for s in all_scripts if s.get("oid") == script_oid), None)

        if not script:
            raise APIError(f"Script with OID {script_oid} not found")

        if include_content:
            content_response = self.client._request(
                "GET",
                f"/setting/scripts/{script_oid}/content"
            )
            if content_response.status_code == 200:
                try:
                    content_data = content_response.json()
                    script["content"] = (
                        content_data.get("content") or
                        content_data.get("script") or ""
                    )
                except Exception:
                    script["content"] = content_response.text

        return script

    def create(self, name: str, content: str) -> Dict[str, Any]:
        """
        Create a new pre-run CLI script.

        Args:
            name: Script name (e.g., "Site-A-Bootstrap")
            content: FortiGate CLI commands

        Returns:
            Dictionary with:
            - success: True if script AND content created, False otherwise
            - partial_success: True if script created but content failed
            - content_upload_failed: True if content upload failed
            - script: Dict with oid, name, content_length

        IMPORTANT: Always check content_upload_failed! If True, the script
        exists but has no content - do NOT use it for provisioning until
        content is added via the FortiCloud portal.

        Example:
            result = scripts.create(
                name="Branch-Config",
                content='''
config system global
    set hostname "Branch-01"
end
'''
            )

            if result.get('content_upload_failed'):
                print(f"WARNING: Script created but content failed!")
                print(f"Add content at: {result['portal_url']}")
            elif result['success']:
                print(f"Created script: {result['script']['oid']}")
        """
        from .client import APIError

        if not name:
            raise ValueError("Script name is required")
        if not content:
            raise ValueError("Script content is required")

        # Step 1: Create script metadata
        create_response = self.client._request(
            "POST",
            "/setting/scripts",
            json={"name": name}
        )

        if create_response.status_code not in [200, 201]:
            raise APIError(
                f"Failed to create script: {create_response.status_code} - {create_response.text}"
            )

        create_data = create_response.json()
        script_oid = create_data.get("oid")

        if not script_oid:
            raise APIError(f"No OID returned from script creation: {create_data}")

        # Step 2: Upload content using JSON with content key
        content_url = f"{self.client.API_BASE}/setting/scripts/{script_oid}/content"
        content_response = requests.put(
            content_url,
            headers=self.client._headers(),
            json={"content": content},
            timeout=30
        )

        if content_response.status_code in [200, 201, 204]:
            return {
                "success": True,
                "message": f"Script '{name}' created successfully with content",
                "script": {
                    "oid": script_oid,
                    "name": name,
                    "content_length": len(content)
                }
            }

        # Content upload failed - try fallback methods
        fallback_methods = [
            # Plain text
            lambda: requests.put(
                content_url,
                headers={
                    "Authorization": f"Bearer {self.client.get_token()}",
                    "Content-Type": "text/plain; charset=utf-8"
                },
                data=content,
                timeout=30
            ),
            # Multipart file
            lambda: requests.put(
                content_url,
                headers={"Authorization": f"Bearer {self.client.get_token()}"},
                files={"file": ("script.txt", content, "text/plain")},
                timeout=30
            )
        ]

        for method in fallback_methods:
            try:
                resp = method()
                if resp.status_code in [200, 201, 204]:
                    return {
                        "success": True,
                        "message": f"Script '{name}' created successfully with content",
                        "script": {
                            "oid": script_oid,
                            "name": name,
                            "content_length": len(content)
                        }
                    }
            except Exception:
                continue

        # All methods failed - return partial success with clear warning
        return {
            "success": False,  # Full operation did NOT succeed
            "partial_success": True,  # Script metadata was created
            "message": f"Script '{name}' created (OID: {script_oid}) but content upload FAILED. "
                       f"DO NOT use this script for provisioning until content is added via portal.",
            "script": {
                "oid": script_oid,
                "name": name,
                "content_length": 0
            },
            "content_upload_failed": True,
            "portal_url": "https://fortiztp.forticloud.com"
        }

    def delete(self, script_oid: int) -> Dict[str, Any]:
        """
        Delete a script by OID.

        Args:
            script_oid: Script OID to delete

        Returns:
            Dictionary with success status

        Example:
            result = scripts.delete(456)
        """
        from .client import APIError

        response = self.client._request("DELETE", f"/setting/scripts/{script_oid}")

        if response.status_code not in [200, 204]:
            raise APIError(
                f"Failed to delete script: {response.status_code} - {response.text}"
            )

        return {
            "success": True,
            "message": f"Script {script_oid} deleted successfully"
        }
