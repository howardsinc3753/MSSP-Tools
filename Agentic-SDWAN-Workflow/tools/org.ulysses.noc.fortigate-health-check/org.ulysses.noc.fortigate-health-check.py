#!/usr/bin/env python3
from __future__ import annotations
"""
FortiGate Health Check Tool

Retrieves health metrics from a FortiGate device via REST API.
Returns CPU, memory, session count, uptime, and firmware version.
"""

import urllib.request
import urllib.error
import ssl
import json
import os
from pathlib import Path
from typing import Any, Optional


def load_credentials(target_ip: str) -> Optional[dict]:
    """Load API credentials from local config file.

    MCP credential search order (uses FIRST match):
    1. ~/.config/mcp/ (PRIMARY - MCP server checks this first)
    2. ~/AppData/Local/mcp/ (Windows secondary)
    3. C:/ProgramData/mcp/ or /etc/mcp/ (System-wide)

    Note: We ONLY check MCP paths to ensure consistency with credential-manager.
    Tool-relative and CWD-relative paths are NOT checked to avoid stale credentials.
    """
    config_paths = [
        # PRIMARY: User config (MCP server checks this FIRST)
        Path.home() / ".config" / "mcp" / "fortigate_credentials.yaml",
    ]

    # Platform-specific paths
    if os.name == 'nt':
        # Windows secondary
        config_paths.append(Path.home() / "AppData" / "Local" / "mcp" / "fortigate_credentials.yaml")
        # Windows system-wide
        config_paths.append(Path("C:/ProgramData/mcp/fortigate_credentials.yaml"))
    else:
        # Linux/Mac system-wide
        config_paths.append(Path("/etc/mcp/fortigate_credentials.yaml"))

    for config_path in config_paths:
        if config_path.exists():
            try:
                import yaml
                with open(config_path) as f:
                    config = yaml.safe_load(f)

                # Check default_lookup first (IP -> device_id mapping)
                if "default_lookup" in config and target_ip in config["default_lookup"]:
                    device_name = config["default_lookup"][target_ip]
                    if device_name in config.get("devices", {}):
                        return config["devices"][device_name]

                # Search devices by host
                for device in config.get("devices", {}).values():
                    if device.get("host") == target_ip:
                        return device

            except Exception:
                continue

    return None


def make_api_request(host: str, endpoint: str, api_token: str,
                     verify_ssl: bool = False, timeout: int = 30) -> dict:
    """Make a request to FortiGate REST API using Bearer token auth.

    Note: FortiOS 7.6+ requires Bearer token authentication.
    Query parameter auth (access_token=) is deprecated.
    """
    url = f"https://{host}{endpoint}"

    # Create SSL context
    if not verify_ssl:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    else:
        ctx = ssl.create_default_context()

    req = urllib.request.Request(url, method="GET")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_token}")

    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
        return json.loads(response.read().decode())


def main(context) -> dict[str, Any]:
    """
    FortiGate Health Check - returns device health metrics.

    Args:
        context: ExecutionContext containing:
            - parameters: Tool parameters (target_ip, timeout, verify_ssl)
            - credentials: Credential vault data (optional, falls back to local config)
            - metadata: Tool manifest and execution metadata

    Returns:
        dict: Health metrics including:
            - cpu_percent: CPU utilization
            - memory_percent: Memory utilization
            - session_count: Active sessions
            - uptime_seconds: Device uptime
            - firmware_version: FortiOS version
            - hostname: Device hostname
            - serial_number: Device serial
    """
    # Support both old dict format and new context format
    if hasattr(context, "parameters"):
        args = context.parameters
        creds = getattr(context, "credentials", None)
    else:
        args = context
        creds = None

    target_ip = args.get("target_ip")
    timeout = args.get("timeout", 30)
    verify_ssl = args.get("verify_ssl", False)

    if not target_ip:
        return {
            "error": "target_ip is required",
            "success": False,
        }

    # Get credentials - check context first, then local config
    api_token = None
    if creds and creds.get("api_token"):
        api_token = creds["api_token"]
        if creds.get("verify_ssl") is not None:
            verify_ssl = creds["verify_ssl"]
    else:
        # Load from local credential file
        local_creds = load_credentials(target_ip)
        if local_creds:
            api_token = local_creds.get("api_token")
            if local_creds.get("verify_ssl") is not None:
                verify_ssl = local_creds["verify_ssl"]

    if not api_token:
        return {
            "error": f"No API credentials found for {target_ip}. Configure in config/fortigate_credentials.yaml",
            "success": False,
        }

    try:
        # Fetch system status
        status_resp = make_api_request(
            target_ip, "/api/v2/monitor/system/status",
            api_token, verify_ssl, timeout
        )

        # Fetch resource usage
        resource_resp = make_api_request(
            target_ip, "/api/v2/monitor/system/resource/usage",
            api_token, verify_ssl, timeout
        )

        # Parse results
        results = status_resp.get("results", {})
        resources = resource_resp.get("results", {})

        # Helper to extract current and historical max from resource data
        def get_metric(data, is_list=True):
            """Extract current value and 1-hour max from resource data."""
            if is_list:
                entry = data[0] if data else {}
            else:
                entry = data if isinstance(data, dict) else {}

            current = entry.get("current", 0)
            historical = entry.get("historical", {})
            hour_data = historical.get("1-hour", {})
            hour_max = hour_data.get("max", current)

            return current, hour_max

        # Extract CPU with historical
        cpu_data = resources.get("cpu", [{}])
        cpu_percent, cpu_1hr_max = get_metric(cpu_data, is_list=True)

        # Extract memory with historical
        mem_data = resources.get("mem", [{}])
        memory_percent, memory_1hr_max = get_metric(mem_data, is_list=True)

        # Extract session count with historical
        session_data = resources.get("session", [{}])
        session_count, session_1hr_max = get_metric(session_data, is_list=True)

        # Extract disk usage
        disk_data = resources.get("disk", [{}])
        disk_percent, _ = get_metric(disk_data, is_list=True)

        return {
            "success": True,
            "target_ip": target_ip,
            "hostname": results.get("hostname", "unknown"),
            "serial_number": status_resp.get("serial", "unknown"),
            "firmware_version": status_resp.get("version", "unknown"),
            "build": status_resp.get("build", 0),
            "model": results.get("model", "unknown"),
            "model_name": results.get("model_name", "FortiGate"),
            "cpu_percent": cpu_percent,
            "cpu_1hr_max": cpu_1hr_max,
            "memory_percent": memory_percent,
            "memory_1hr_max": memory_1hr_max,
            "disk_percent": disk_percent,
            "session_count": session_count,
            "session_1hr_max": session_1hr_max,
            "log_disk_status": results.get("log_disk_status", "unknown"),
            "vdom": status_resp.get("vdom", "root"),
        }

    except urllib.error.HTTPError as e:
        return {
            "success": False,
            "error": f"HTTP Error {e.code}: {e.reason}",
            "target_ip": target_ip,
        }
    except urllib.error.URLError as e:
        return {
            "success": False,
            "error": f"Connection failed: {e.reason}",
            "target_ip": target_ip,
        }
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Invalid JSON response: {e}",
            "target_ip": target_ip,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "target_ip": target_ip,
        }


if __name__ == "__main__":
    # Test execution against lab FortiGate
    result = main({"target_ip": "10.0.0.62"})
    print(json.dumps(result, indent=2))
