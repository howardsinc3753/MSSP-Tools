"""
SOCaaS Python SDK
Fortinet Security Operations Center as a Service API Client

This package provides a Python interface to the Fortinet SOCaaS API for managing
security alerts, service requests, comments, reports, and MSSP client operations.

Example:
    from socaas import SOCaaSClient

    client = SOCaaSClient(username="your-api-user", password="your-api-password")
    alerts = client.list_alerts()
    print(f"Found {len(alerts)} alerts")

Copyright (c) 2025 Fortinet MSSP Partner Tools
Licensed under MIT License
"""

__version__ = "1.0.0"
__author__ = "Fortinet MSSP Partner Tools"

from .client import (
    SOCaaSClient,
    SOCaaSError,
    AuthenticationError,
    APIError
)
from .alerts import AlertManager
from .service_requests import ServiceRequestManager
from .clients import ClientManager
from .comments import CommentManager
from .reports import ReportManager
from .files import FileManager

__all__ = [
    # Client
    "SOCaaSClient",
    # Managers
    "AlertManager",
    "ServiceRequestManager",
    "ClientManager",
    "CommentManager",
    "ReportManager",
    "FileManager",
    # Exceptions
    "SOCaaSError",
    "AuthenticationError",
    "APIError",
    # Meta
    "__version__"
]
