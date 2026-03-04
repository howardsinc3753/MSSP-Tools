#!/usr/bin/env python3
"""
Secure Credential Provider (Patent Innovation 4)
=================================================

Implements secure credential loading with encrypted vault fallback to cleartext YAML.

Credential Resolution Order:
1. SECURE: Windows DPAPI encrypted vault (%LOCALAPPDATA%/UlyssesMCP/vault/)
2. LEGACY: Cleartext YAML (~/.config/mcp/fortigate_credentials.yaml)

All credential accesses are logged for audit trail.

This module implements "Innovation 4: Credential Boundary Isolation" from the
FortiMCP patent disclosure - credentials remain on subscriber endpoints and
are encrypted at rest with audit logging.

Author: Daniel Howard
Version: 1.0.0
Created: 2026-02-09
Patent Reference: FortiMCP Invention Disclosure Form, Section 5, Innovation 4
"""

import os
import json
import ctypes
import base64
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Configure audit logger
audit_logger = logging.getLogger("credential_audit")
audit_logger.setLevel(logging.INFO)

# Ensure audit log handler exists
if not audit_logger.handlers:
    audit_dir = Path.home() / ".config" / "mcp" / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_file = audit_dir / "credential_access.log"
    handler = logging.FileHandler(audit_file)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s'
    ))
    audit_logger.addHandler(handler)


# =============================================================================
# WINDOWS DPAPI ENCRYPTION (Secure Tier)
# =============================================================================

# DPAPI constants
CRYPTPROTECT_UI_FORBIDDEN = 0x01

class DATA_BLOB(ctypes.Structure):
    """Windows DPAPI data blob structure."""
    _fields_ = [
        ('cbData', ctypes.c_ulong),
        ('pbData', ctypes.POINTER(ctypes.c_char))
    ]


def _get_vault_path() -> Path:
    """Get the DPAPI vault directory path."""
    app_data = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
    return Path(app_data) / 'UlyssesMCP' / 'vault'


def _dpapi_decrypt(encrypted_data: bytes) -> Optional[bytes]:
    """Decrypt data using Windows DPAPI."""
    if os.name != 'nt':
        return None  # DPAPI only on Windows

    try:
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32

        # Input blob
        input_blob = DATA_BLOB()
        input_blob.cbData = len(encrypted_data)
        input_blob.pbData = ctypes.cast(
            ctypes.create_string_buffer(encrypted_data, len(encrypted_data)),
            ctypes.POINTER(ctypes.c_char)
        )

        # Output blob
        output_blob = DATA_BLOB()

        # Entropy (must match encryption)
        entropy = DATA_BLOB()
        entropy_data = b"UlyssesMCPVault"
        entropy.cbData = len(entropy_data)
        entropy.pbData = ctypes.cast(
            ctypes.create_string_buffer(entropy_data, len(entropy_data)),
            ctypes.POINTER(ctypes.c_char)
        )

        # Decrypt
        result = crypt32.CryptUnprotectData(
            ctypes.byref(input_blob),
            None,
            ctypes.byref(entropy),
            None,
            None,
            CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(output_blob)
        )

        if not result:
            return None

        # Copy and free
        decrypted = ctypes.string_at(output_blob.pbData, output_blob.cbData)
        ctypes.memset(output_blob.pbData, 0, output_blob.cbData)
        kernel32.LocalFree(output_blob.pbData)

        return decrypted

    except Exception:
        return None


def _dpapi_encrypt(data: bytes) -> Optional[bytes]:
    """Encrypt data using Windows DPAPI."""
    if os.name != 'nt':
        return None

    try:
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32

        # Input blob
        input_blob = DATA_BLOB()
        input_blob.cbData = len(data)
        input_blob.pbData = ctypes.cast(
            ctypes.create_string_buffer(data, len(data)),
            ctypes.POINTER(ctypes.c_char)
        )

        # Output blob
        output_blob = DATA_BLOB()

        # Entropy
        entropy = DATA_BLOB()
        entropy_data = b"UlyssesMCPVault"
        entropy.cbData = len(entropy_data)
        entropy.pbData = ctypes.cast(
            ctypes.create_string_buffer(entropy_data, len(entropy_data)),
            ctypes.POINTER(ctypes.c_char)
        )

        # Encrypt
        result = crypt32.CryptProtectData(
            ctypes.byref(input_blob),
            "MCP Credential",
            ctypes.byref(entropy),
            None,
            None,
            CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(output_blob)
        )

        if not result:
            return None

        encrypted = ctypes.string_at(output_blob.pbData, output_blob.cbData)
        kernel32.LocalFree(output_blob.pbData)

        return encrypted

    except Exception:
        return None


# =============================================================================
# VAULT OPERATIONS
# =============================================================================

def _load_from_vault(device_id: str) -> Optional[Dict[str, Any]]:
    """
    Load credentials from encrypted DPAPI vault.

    Args:
        device_id: Device identifier (e.g., "lab-71f" or IP "10.0.0.62")

    Returns:
        Credential dict or None if not found
    """
    vault_path = _get_vault_path()

    # Try device_id directly
    cred_file = vault_path / f"device_{device_id}.cred"

    if not cred_file.exists():
        # Try IP-based lookup
        index_file = vault_path / ".device_index.json"
        if index_file.exists():
            try:
                with open(index_file, 'r') as f:
                    index = json.load(f)
                mapped_id = index.get("ip_lookup", {}).get(device_id)
                if mapped_id:
                    cred_file = vault_path / f"device_{mapped_id}.cred"
            except Exception:
                pass

    if not cred_file.exists():
        return None

    try:
        with open(cred_file, 'r') as f:
            cred_data = json.load(f)

        # Decrypt the encrypted value
        encrypted = base64.b64decode(cred_data.get("encrypted_value", ""))
        decrypted = _dpapi_decrypt(encrypted)

        if not decrypted:
            return None

        # Parse the decrypted credential
        credential = json.loads(decrypted.decode('utf-8'))
        credential["_source"] = "vault"
        credential["_encrypted"] = True

        return credential

    except Exception:
        return None


def store_in_vault(device_id: str, host: str, api_token: str,
                   verify_ssl: bool = False, metadata: Dict = None) -> bool:
    """
    Store credentials in encrypted DPAPI vault.

    Args:
        device_id: Device identifier
        host: Device IP/hostname
        api_token: API token
        verify_ssl: SSL verification flag
        metadata: Optional metadata dict

    Returns:
        True if stored successfully
    """
    vault_path = _get_vault_path()
    vault_path.mkdir(parents=True, exist_ok=True)

    try:
        # Build credential object
        credential = {
            "host": host,
            "api_token": api_token,
            "verify_ssl": verify_ssl,
            "_metadata": metadata or {},
            "_stored_at": datetime.now().isoformat()
        }

        # Encrypt
        cred_json = json.dumps(credential).encode('utf-8')
        encrypted = _dpapi_encrypt(cred_json)

        if not encrypted:
            return False

        # Store
        cred_file = vault_path / f"device_{device_id}.cred"
        cred_data = {
            "device_id": device_id,
            "host": host,
            "encrypted_value": base64.b64encode(encrypted).decode('ascii'),
            "created_at": datetime.now().isoformat()
        }

        with open(cred_file, 'w') as f:
            json.dump(cred_data, f, indent=2)

        # Update index
        index_file = vault_path / ".device_index.json"
        if index_file.exists():
            with open(index_file, 'r') as f:
                index = json.load(f)
        else:
            index = {"devices": {}, "ip_lookup": {}}

        index["devices"][device_id] = {"host": host, "stored_at": cred_data["created_at"]}
        index["ip_lookup"][host] = device_id

        with open(index_file, 'w') as f:
            json.dump(index, f, indent=2)

        # Audit log
        audit_logger.info(f"STORE | device={device_id} | host={host} | vault=DPAPI")

        return True

    except Exception as e:
        audit_logger.error(f"STORE_FAILED | device={device_id} | error={str(e)}")
        return False


# =============================================================================
# YAML FALLBACK (Legacy)
# =============================================================================

def _load_from_yaml(target_ip: str) -> Optional[Dict[str, Any]]:
    """
    Load credentials from cleartext YAML (legacy fallback).

    Args:
        target_ip: Device IP address

    Returns:
        Credential dict or None if not found
    """
    try:
        import yaml
    except ImportError:
        return None

    # Search paths in order
    search_paths = [
        Path.home() / ".config" / "mcp",
        Path.home() / "AppData" / "Local" / "mcp",
        Path("C:/ProgramData/Ulysses/config"),
        Path("C:/ProgramData/mcp"),
    ]

    for search_path in search_paths:
        if not search_path.exists():
            continue

        for config_file in search_path.glob("*_credentials.yaml"):
            try:
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)

                if not config:
                    continue

                # Check default_lookup
                if "default_lookup" in config and target_ip in config["default_lookup"]:
                    device_name = config["default_lookup"][target_ip]
                    if device_name in config.get("devices", {}):
                        cred = config["devices"][device_name].copy()
                        cred["_source"] = "yaml"
                        cred["_encrypted"] = False
                        cred["_device_name"] = device_name
                        return cred

                # Search by host
                for device_name, device_info in config.get("devices", {}).items():
                    if device_info.get("host") == target_ip:
                        cred = device_info.copy()
                        cred["_source"] = "yaml"
                        cred["_encrypted"] = False
                        cred["_device_name"] = device_name
                        return cred

            except Exception:
                continue

    return None


# =============================================================================
# MAIN API: SECURE CREDENTIAL PROVIDER
# =============================================================================

def load_secure_credentials(target_ip: str, tool_id: str = "unknown") -> Optional[Dict[str, Any]]:
    """
    Load credentials with secure vault priority and YAML fallback.

    Resolution Order:
    1. DPAPI encrypted vault (SECURE)
    2. Cleartext YAML (LEGACY - logged as warning)

    All accesses are logged for audit trail.

    Args:
        target_ip: Device IP address or device_id
        tool_id: Tool requesting credentials (for audit)

    Returns:
        Credential dict with keys: host, api_token, verify_ssl, _source, _encrypted
        Returns None if no credentials found
    """
    timestamp = datetime.now().isoformat()

    # TIER 1: Try encrypted vault first
    credential = _load_from_vault(target_ip)

    if credential:
        audit_logger.info(
            f"ACCESS | device={target_ip} | tool={tool_id} | source=VAULT | secure=YES"
        )
        return credential

    # TIER 2: Fallback to YAML (legacy)
    credential = _load_from_yaml(target_ip)

    if credential:
        audit_logger.warning(
            f"ACCESS | device={target_ip} | tool={tool_id} | source=YAML | secure=NO | "
            f"RECOMMENDATION: Migrate to encrypted vault"
        )
        return credential

    # Not found
    audit_logger.warning(
        f"ACCESS_FAILED | device={target_ip} | tool={tool_id} | error=NOT_FOUND"
    )
    return None


def get_credential_status(target_ip: str) -> Dict[str, Any]:
    """
    Check credential storage status for a device.

    Returns:
        Dict with storage location and security status
    """
    vault_cred = _load_from_vault(target_ip)
    yaml_cred = _load_from_yaml(target_ip)

    return {
        "device": target_ip,
        "in_vault": vault_cred is not None,
        "in_yaml": yaml_cred is not None,
        "secure": vault_cred is not None,
        "recommendation": "Credentials secured in vault" if vault_cred
                         else "Migrate to vault: store_in_vault(device_id, host, token)"
    }


# =============================================================================
# CLI TESTING
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python secure_credential_provider.py <target_ip> [tool_id]")
        print("\nExamples:")
        print("  python secure_credential_provider.py 10.0.0.62")
        print("  python secure_credential_provider.py 10.0.0.62 fortigate-health-check")
        sys.exit(1)

    target = sys.argv[1]
    tool = sys.argv[2] if len(sys.argv) > 2 else "cli-test"

    print(f"\n=== Secure Credential Provider Test ===")
    print(f"Target: {target}")
    print(f"Tool: {tool}")

    # Check status
    status = get_credential_status(target)
    print(f"\nStatus:")
    print(f"  In Vault (encrypted): {status['in_vault']}")
    print(f"  In YAML (cleartext):  {status['in_yaml']}")
    print(f"  Secure:               {status['secure']}")
    print(f"  Recommendation:       {status['recommendation']}")

    # Load credential
    print(f"\nLoading credentials...")
    cred = load_secure_credentials(target, tool)

    if cred:
        print(f"  Source:     {cred.get('_source', 'unknown')}")
        print(f"  Encrypted:  {cred.get('_encrypted', False)}")
        print(f"  Host:       {cred.get('host', 'N/A')}")
        print(f"  Has Token:  {'Yes' if cred.get('api_token') else 'No'}")
        print(f"  SSL Verify: {cred.get('verify_ssl', False)}")
    else:
        print("  No credentials found!")

    print(f"\nAudit log: ~/.config/mcp/audit/credential_access.log")
