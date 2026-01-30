"""
FortiZTP Device Management
Operations for listing, querying, and provisioning devices.
"""

from typing import Any, Dict, List, Optional


class DeviceManager:
    """
    Manage FortiZTP device operations.

    Device Types:
        - FortiGate
        - FortiAP
        - FortiSwitch
        - FortiExtender

    Provision Status:
        - provisioned: Device is configured for ZTP
        - unprovisioned: Device is not configured
        - hidden: Device is hidden from inventory
        - incomplete: Device provisioning is incomplete

    Provision Targets:
        - FortiManager: Managed by FortiManager
        - FortiGateCloud: Managed by FortiGate Cloud
        - FortiEdgeCloud: Managed by FortiEdge Cloud
        - ExternalController: Managed by external controller

    Example:
        from fortiztp import FortiZTPClient

        client = FortiZTPClient(username="...", password="...")
        devices = DeviceManager(client)

        # List all devices
        all_devices = devices.list()

        # List only unprovisioned FortiGates
        unprov = devices.list(device_type="FortiGate", provision_status="unprovisioned")

        # Get specific device
        device = devices.get("FGT60F1234567890")

        # Provision device to FortiManager
        result = devices.provision(
            serial_number="FGT60F1234567890",
            device_type="FortiGate",
            provision_target="FortiManager",
            fortimanager_oid=123,
            external_controller_ip="192.168.1.100",
            script_oid=456  # Optional bootstrap script
        )
    """

    VALID_DEVICE_TYPES = ["FortiGate", "FortiAP", "FortiSwitch", "FortiExtender"]
    VALID_PROVISION_STATUS = ["provisioned", "unprovisioned", "hidden", "incomplete"]
    VALID_PROVISION_TARGETS = ["FortiManager", "FortiGateCloud", "FortiEdgeCloud", "ExternalController"]

    def __init__(self, client):
        """
        Initialize DeviceManager.

        Args:
            client: FortiZTPClient instance
        """
        self.client = client

    def list(
        self,
        device_type: Optional[str] = None,
        provision_status: Optional[str] = None,
        provision_target: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all devices with optional filters.

        Args:
            device_type: Filter by device type (FortiGate, FortiAP, etc.)
            provision_status: Filter by status (provisioned, unprovisioned, etc.)
            provision_target: Filter by target (FortiManager, FortiGateCloud, etc.)

        Returns:
            List of device dictionaries

        Example:
            # All FortiGates
            devices.list(device_type="FortiGate")

            # Unprovisioned devices
            devices.list(provision_status="unprovisioned")
        """
        from .client import APIError

        response = self.client._request("GET", "/devices")

        if response.status_code != 200:
            raise APIError(f"API request failed: {response.status_code} - {response.text}")

        data = response.json()
        devices = data.get("devices") or []

        # Apply client-side filters
        if device_type:
            devices = [d for d in devices if d.get("deviceType") == device_type]

        if provision_status:
            devices = [d for d in devices if d.get("provisionStatus") == provision_status]

        if provision_target:
            devices = [d for d in devices if d.get("provisionTarget") == provision_target]

        # Transform to cleaner output
        return [self._transform_device(d) for d in devices]

    def get(self, serial_number: str) -> Dict[str, Any]:
        """
        Get detailed status for a specific device.

        Args:
            serial_number: Device serial number (e.g., "FGT60F1234567890")

        Returns:
            Device details dictionary

        Raises:
            APIError: If device not found or request fails

        Example:
            device = devices.get("FGT60F1234567890")
            print(f"Status: {device['provision_status']}")
        """
        from .client import APIError

        response = self.client._request("GET", f"/devices/{serial_number}")

        if response.status_code == 404:
            raise APIError(f"Device {serial_number} not found in FortiZTP")

        if response.status_code != 200:
            raise APIError(f"API request failed: {response.status_code} - {response.text}")

        return self._transform_device(response.json())

    def provision(
        self,
        serial_number: str,
        device_type: str,
        provision_status: str = "provisioned",
        provision_target: Optional[str] = None,
        region: Optional[str] = None,
        fortimanager_oid: Optional[int] = None,
        script_oid: Optional[int] = None,
        use_default_script: Optional[bool] = None,
        external_controller_sn: Optional[str] = None,
        external_controller_ip: Optional[str] = None,
        firmware_profile: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provision or unprovision a device.

        Args:
            serial_number: Device serial number
            device_type: Device type (FortiGate, FortiAP, FortiSwitch, FortiExtender)
            provision_status: 'provisioned' or 'unprovisioned' (default: provisioned)
            provision_target: FortiManager, FortiGateCloud, FortiEdgeCloud, ExternalController
            region: FortiCloud region (required for cloud targets)
            fortimanager_oid: FortiManager OID (for FortiManager target)
            script_oid: Script OID for bootstrap CLI script
            use_default_script: Use default script for this device
            external_controller_sn: External controller serial number
            external_controller_ip: External controller IP address
            firmware_profile: Firmware upgrade profile name

        Returns:
            Provisioning result dictionary

        Example:
            # Provision to FortiManager
            result = devices.provision(
                serial_number="FGT60F1234567890",
                device_type="FortiGate",
                provision_target="FortiManager",
                fortimanager_oid=123,
                external_controller_ip="192.168.1.100",
                script_oid=456
            )

            # Unprovision a device
            result = devices.provision(
                serial_number="FGT60F1234567890",
                device_type="FortiGate",
                provision_status="unprovisioned"
            )
        """
        from .client import APIError

        # Validate inputs
        if device_type not in self.VALID_DEVICE_TYPES:
            raise ValueError(
                f"Invalid device_type: {device_type}. Must be one of: {', '.join(self.VALID_DEVICE_TYPES)}"
            )

        if provision_status not in ["provisioned", "unprovisioned"]:
            raise ValueError(
                f"Invalid provision_status: {provision_status}. Must be 'provisioned' or 'unprovisioned'"
            )

        # Validate provision_target if provided
        if provision_target and provision_target not in self.VALID_PROVISION_TARGETS:
            raise ValueError(
                f"Invalid provision_target: {provision_target}. Must be one of: {', '.join(self.VALID_PROVISION_TARGETS)}"
            )

        # Build payload - deviceType is REQUIRED
        payload = {
            "deviceType": device_type,
            "provisionStatus": provision_status
        }

        # Add optional fields
        if provision_target:
            payload["provisionTarget"] = provision_target
        if region:
            payload["region"] = region
        if fortimanager_oid is not None:
            payload["fortiManagerOid"] = fortimanager_oid
        if script_oid is not None:
            payload["scriptOid"] = script_oid
        if use_default_script is not None:
            payload["useDefaultScript"] = use_default_script
        if external_controller_sn:
            payload["externalControllerSn"] = external_controller_sn
        if external_controller_ip:
            payload["externalControllerIp"] = external_controller_ip
        if firmware_profile:
            payload["firmwareProfile"] = firmware_profile

        response = self.client._request("PUT", f"/devices/{serial_number}", json=payload)

        if response.status_code != 200:
            raise APIError(f"Provision request failed: {response.status_code} - {response.text}")

        # API may return empty body on success
        try:
            api_response = response.json() if response.text.strip() else {}
        except Exception:
            api_response = {}

        return {
            "success": True,
            "message": f"Device {serial_number} ({device_type}) {provision_status} successfully",
            "device": {
                "serial_number": serial_number,
                "device_type": device_type,
                "provision_status": provision_status,
                "provision_target": provision_target,
                "fortimanager_oid": fortimanager_oid,
                "script_oid": script_oid
            },
            "api_response": api_response
        }

    def _transform_device(self, device: Dict[str, Any]) -> Dict[str, Any]:
        """Transform API response to cleaner format."""
        transformed = {
            "serial_number": device.get("deviceSN"),
            "device_type": device.get("deviceType"),
            "platform": device.get("platform"),
            "provision_status": device.get("provisionStatus"),
            "provision_sub_status": device.get("provisionSubStatus"),
            "provision_target": device.get("provisionTarget"),
            "region": device.get("region"),
            "firmware_profile": device.get("firmwareProfile"),
            "fortimanager_oid": device.get("fortiManagerOid"),
            "script_oid": device.get("scriptOid"),
            "use_default_script": device.get("useDefaultScript"),
            "external_controller_sn": device.get("externalControllerSn"),
            "external_controller_ip": device.get("externalControllerIp")
        }
        # Remove None values
        return {k: v for k, v in transformed.items() if v is not None}
