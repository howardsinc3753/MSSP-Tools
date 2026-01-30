"""
FortiZTP Python SDK
Fortinet Zero Touch Provisioning API Client

This package provides a Python interface to the FortiZTP API for managing
device provisioning, bootstrap scripts, and FortiManager assignments.

IMPORTANT: FortiZTP does NOT support ORG IAM API Users.
Only Local type IAM API Users work with this API.

Example:
    from fortiztp import FortiZTPClient

    client = FortiZTPClient(username="your-api-user", password="your-api-password")
    devices = client.list_devices()
    print(f"Found {len(devices)} devices")

Copyright (c) 2025 Fortinet MSSP Partner Tools
Licensed under MIT License
"""

__version__ = "1.0.0"
__author__ = "Fortinet MSSP Partner Tools"

from .client import FortiZTPClient
from .devices import DeviceManager
from .scripts import ScriptManager

__all__ = [
    "FortiZTPClient",
    "DeviceManager",
    "ScriptManager",
    "__version__"
]
