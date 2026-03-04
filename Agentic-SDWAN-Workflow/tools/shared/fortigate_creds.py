"""
FortiGate Credential Loader (Gap-3 Standardization)
====================================================

Centralized credential loading for FortiGate tools.
All FortiGate tools should import this module instead of
implementing their own credential loading logic.

Credential Search Order:
1. FORTIGATE_CREDS_PATH environment variable (if set)
2. ~/.config/mcp/fortigate_credentials.yaml (PRIMARY)
3. ~/AppData/Local/mcp/fortigate_credentials.yaml (Windows)
4. C:/ProgramData/Ulysses/config/fortigate_credentials.yaml (Windows legacy)
5. C:/ProgramData/mcp/fortigate_credentials.yaml (Windows system)
6. /etc/mcp/fortigate_credentials.yaml (Linux system)

Usage in tools:
    from shared.fortigate_creds import load_fortigate_credentials

    creds = load_fortigate_credentials(target_ip)
    if not creds:
        return {"success": False, "error": f"No credentials for {target_ip}"}

    api_token = creds.get("api_token")
    ssh_key_path = creds.get("ssh_key_path")

Author: Project Ulysses
Version: 1.0.0
Created: 2026-01-22
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any

# Import shared constants if available, otherwise define locally
try:
    from .constants import (
        FORTIGATE_CREDS_PATH_ENV,
        FORTIGATE_CREDS_FILENAME,
        get_credential_paths
    )
except ImportError:
    # Fallback for standalone use
    FORTIGATE_CREDS_PATH_ENV = "FORTIGATE_CREDS_PATH"
    FORTIGATE_CREDS_FILENAME = "fortigate_credentials.yaml"

    def get_credential_paths(filename: str = FORTIGATE_CREDS_FILENAME) -> list:
        paths = []
        env_path = os.environ.get(FORTIGATE_CREDS_PATH_ENV)
        if env_path:
            paths.append(Path(env_path))
        paths.append(Path.home() / ".config" / "mcp" / filename)
        if os.name == 'nt':
            paths.append(Path.home() / "AppData" / "Local" / "mcp" / filename)
            paths.append(Path("C:/ProgramData/Ulysses/config") / filename)
            paths.append(Path("C:/ProgramData/mcp") / filename)
        else:
            paths.append(Path("/etc/mcp") / filename)
        return paths


def load_fortigate_credentials(target_ip: str) -> Optional[Dict[str, Any]]:
    """Load FortiGate credentials for a specific device.

    Args:
        target_ip: The FortiGate management IP address to look up

    Returns:
        dict with credentials (api_token, ssh_key_path, etc.) or None if not found

    Credential file structure expected:
        default_lookup:
          192.168.1.1: hub1
          192.168.1.2: spoke1
        devices:
          hub1:
            host: 192.168.1.1
            api_token: "xxxxx"
            ssh_key_path: "~/.config/mcp/keys/fortigate_rsa"
            verify_ssl: false
    """
    try:
        import yaml
    except ImportError:
        # PyYAML not available
        return None

    config_paths = get_credential_paths(FORTIGATE_CREDS_FILENAME)

    for config_path in config_paths:
        if not config_path.exists():
            continue

        try:
            with open(config_path, encoding='utf-8') as f:
                config = yaml.safe_load(f)

            if not config:
                continue

            # Method 1: Check default_lookup (IP -> device_name mapping)
            if "default_lookup" in config and target_ip in config["default_lookup"]:
                device_name = config["default_lookup"][target_ip]
                if device_name in config.get("devices", {}):
                    device = config["devices"][device_name]
                    device["_source_path"] = str(config_path)
                    device["_device_name"] = device_name
                    return device

            # Method 2: Search devices by host field
            for device_name, device in config.get("devices", {}).items():
                if device.get("host") == target_ip:
                    device["_source_path"] = str(config_path)
                    device["_device_name"] = device_name
                    return device

        except Exception:
            # Skip malformed files, try next path
            continue

    return None


def get_credential_file_path() -> Optional[Path]:
    """Get the first existing credential file path.

    Useful for tools that need to know where credentials are stored.

    Returns:
        Path to existing credential file, or None if no file exists
    """
    for path in get_credential_paths(FORTIGATE_CREDS_FILENAME):
        if path.exists():
            return path
    return None


def list_devices() -> Dict[str, Dict[str, Any]]:
    """List all devices from the credential file.

    Returns:
        dict mapping device_name -> device_config
    """
    try:
        import yaml
    except ImportError:
        return {}

    for config_path in get_credential_paths(FORTIGATE_CREDS_FILENAME):
        if not config_path.exists():
            continue
        try:
            with open(config_path, encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config.get("devices", {})
        except Exception:
            continue
    return {}


# Convenience function for inline use in tools
def load_credentials(target_ip: str) -> Optional[Dict[str, Any]]:
    """Alias for load_fortigate_credentials for backward compatibility."""
    return load_fortigate_credentials(target_ip)
