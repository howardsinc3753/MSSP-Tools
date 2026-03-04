"""
Shared Module (NFR-012-B)
=========================

Cross-component shared constants and utilities.
Single source of truth to prevent integration issues.

Documentation:
- NFR: docs/NFRs/NFR-012-B-AI-CODER-GOVERNANCE.md
"""

from .constants import *
from .fortigate_creds import (
    load_fortigate_credentials,
    load_credentials,
    get_credential_file_path,
    list_devices,
)
