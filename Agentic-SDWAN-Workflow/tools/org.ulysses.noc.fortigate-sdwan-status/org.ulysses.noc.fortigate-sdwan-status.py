#!/usr/bin/env python3
"""
FortiGate SD-WAN Status Tool

Check SD-WAN operational status including:
- Health check probe status (latency, jitter, packet loss, SLA)
- SD-WAN member status
- BGP neighbor status
- IPsec tunnel status

Uses FortiOS REST API monitor endpoints for real-time status.
FortiOS 7.6+ compatible.
"""

import urllib.request
import urllib.error
import ssl
import json
import gzip
import os
from pathlib import Path
from typing import Any, Optional


def load_credentials(target_ip: str) -> Optional[dict]:
    """Load API credentials from local config file."""
    config_paths = [
        Path.home() / ".config" / "mcp" / "fortigate_credentials.yaml",
    ]

    if os.name == 'nt':
        config_paths.append(Path.home() / "AppData" / "Local" / "mcp" / "fortigate_credentials.yaml")
        config_paths.append(Path("C:/ProgramData/mcp/fortigate_credentials.yaml"))
    else:
        config_paths.append(Path("/etc/mcp/fortigate_credentials.yaml"))

    for config_path in config_paths:
        if config_path.exists():
            try:
                import yaml
                with open(config_path) as f:
                    config = yaml.safe_load(f)

                if "default_lookup" in config and target_ip in config["default_lookup"]:
                    device_name = config["default_lookup"][target_ip]
                    if device_name in config.get("devices", {}):
                        return config["devices"][device_name]

                for device in config.get("devices", {}).values():
                    if device.get("host") == target_ip:
                        return device

            except Exception:
                continue

    return None


def decode_response(response) -> str:
    """Decode response handling gzip compression."""
    data = response.read()
    if data[:2] == b'\x1f\x8b':
        data = gzip.decompress(data)
    return data.decode('utf-8')


def api_get(host: str, endpoint: str, api_token: str,
            verify_ssl: bool = False, timeout: int = 30) -> dict:
    """Make GET request to FortiGate REST API."""
    url = f"https://{host}{endpoint}"

    ctx = ssl.create_default_context()
    if not verify_ssl:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {api_token}")

    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
        return json.loads(decode_response(response))


def get_health_check_status(host: str, api_token: str, verify_ssl: bool = False) -> dict:
    """Get SD-WAN health check probe status.

    Returns real-time health check metrics including:
    - Status (up/down)
    - Latency, jitter, packet loss
    - SLA targets met
    - Packet sent/received counts
    """
    try:
        result = api_get(host, "/api/v2/monitor/virtual-wan/health-check", api_token, verify_ssl)
        return result.get("results", {})
    except Exception as e:
        return {"error": str(e)}


def get_sdwan_members(host: str, api_token: str, verify_ssl: bool = False) -> list:
    """Get SD-WAN member status.

    FortiOS 7.6: /system/sdwan/members returns 404.
    Use virtual-wan/members as fallback.
    """
    endpoints = [
        "/api/v2/monitor/system/sdwan/members",
        "/api/v2/monitor/virtual-wan/members"
    ]
    for endpoint in endpoints:
        try:
            result = api_get(host, endpoint, api_token, verify_ssl)
            return result.get("results", [])
        except Exception:
            continue
    return [{"error": "SD-WAN members endpoint not available"}]


def get_bgp_neighbors(host: str, api_token: str, verify_ssl: bool = False) -> list:
    """Get BGP neighbor status."""
    try:
        result = api_get(host, "/api/v2/monitor/router/bgp/neighbors", api_token, verify_ssl)
        return result.get("results", [])
    except Exception as e:
        return [{"error": str(e)}]


def get_ipsec_tunnels(host: str, api_token: str, verify_ssl: bool = False) -> list:
    """Get IPsec tunnel status."""
    try:
        result = api_get(host, "/api/v2/monitor/vpn/ipsec", api_token, verify_ssl)
        return result.get("results", [])
    except Exception as e:
        return [{"error": str(e)}]


def main(context) -> dict[str, Any]:
    """
    Check SD-WAN operational status on FortiGate.

    Args:
        context: ExecutionContext with parameters:
            Required:
            - target_ip: FortiGate management IP

            Optional:
            - check: Specific check to run:
                - "all" (default) - Run all checks
                - "health" - Health check probe status only
                - "members" - SD-WAN member status only
                - "bgp" - BGP neighbor status only
                - "ipsec" - IPsec tunnel status only

    Returns:
        dict: Status results for requested checks
    """
    if hasattr(context, "parameters"):
        args = context.parameters
    else:
        args = context

    target_ip = args.get("target_ip")
    check = args.get("check", "all").lower()

    if not target_ip:
        return {"success": False, "error": "target_ip is required"}

    # Get credentials - check MCP context first, then local config
    api_token = None
    verify_ssl = args.get("verify_ssl", False)
    mcp_creds = getattr(context, "credentials", None) if hasattr(context, "parameters") else None
    if mcp_creds and mcp_creds.get("api_token"):
        api_token = mcp_creds["api_token"]
        if mcp_creds.get("verify_ssl") is not None:
            verify_ssl = mcp_creds["verify_ssl"]
    else:
        creds = load_credentials(target_ip)
        if creds:
            api_token = creds.get("api_token")
            if creds.get("verify_ssl") is not None:
                verify_ssl = creds["verify_ssl"]

    if not api_token:
        return {
            "success": False,
            "error": f"No API credentials found for {target_ip}",
            "hint": "Use fortigate-onboard to create API token first"
        }

    result = {
        "success": True,
        "target_ip": target_ip,
        "check": check
    }

    # Track issues found
    issues = []

    try:
        # Health Check Status
        if check in ["all", "health"]:
            health_data = get_health_check_status(target_ip, api_token, verify_ssl)
            health_checks = []

            if "error" in health_data:
                issues.append(f"Health check API error: {health_data['error']}")

            for hc_name, members in health_data.items():
                if hc_name == "error":
                    continue
                if isinstance(members, dict):
                    for member_name, data in members.items():
                        status = data.get("status", "unknown")
                        entry = {
                            "health_check": hc_name,
                            "member": member_name,
                            "status": status
                        }

                        if status == "up":
                            entry["latency_ms"] = round(data.get("latency", 0), 2)
                            entry["jitter_ms"] = round(data.get("jitter", 0), 2)
                            entry["packet_loss_pct"] = round(data.get("packet_loss", 0), 2)
                            entry["sla_met"] = data.get("sla_targets_met", [])
                            entry["packets_sent"] = data.get("packet_sent", 0)
                            entry["packets_received"] = data.get("packet_received", 0)
                        else:
                            issues.append(f"Health check '{hc_name}' member '{member_name}' is DOWN")

                        health_checks.append(entry)

            result["health_checks"] = health_checks

        # BGP Neighbor Status
        if check in ["all", "bgp"]:
            bgp_data = get_bgp_neighbors(target_ip, api_token, verify_ssl)
            bgp_neighbors = []

            for neighbor in bgp_data:
                if "error" not in neighbor:
                    state = neighbor.get("state", "unknown")
                    entry = {
                        "neighbor_ip": neighbor.get("neighbor_ip"),
                        "local_ip": neighbor.get("local_ip"),
                        "remote_as": neighbor.get("remote_as"),
                        "state": state
                    }

                    if state != "Established":
                        issues.append(f"BGP neighbor {neighbor.get('neighbor_ip')} is {state}")

                    bgp_neighbors.append(entry)

            result["bgp_neighbors"] = bgp_neighbors

        # IPsec Tunnel Status
        if check in ["all", "ipsec"]:
            ipsec_data = get_ipsec_tunnels(target_ip, api_token, verify_ssl)
            tunnels = []

            for tunnel in ipsec_data:
                if "error" not in tunnel:
                    name = tunnel.get("name", "unknown")
                    proxyid = tunnel.get("proxyid", [])

                    # Check Phase2 status
                    phase2_up = False
                    for p in proxyid:
                        if p.get("status") == "up":
                            phase2_up = True
                            break

                    entry = {
                        "name": name,
                        "remote_gw": tunnel.get("rgwy"),
                        "phase2_status": "up" if phase2_up else "down",
                        "incoming_bytes": tunnel.get("incoming_bytes", 0),
                        "outgoing_bytes": tunnel.get("outgoing_bytes", 0)
                    }

                    if not phase2_up:
                        issues.append(f"IPsec tunnel '{name}' Phase2 is DOWN")

                    tunnels.append(entry)

            result["ipsec_tunnels"] = tunnels

        # SD-WAN Members (if endpoint works)
        if check in ["all", "members"]:
            member_data = get_sdwan_members(target_ip, api_token, verify_ssl)
            if member_data and "error" not in member_data[0] if member_data else True:
                result["sdwan_members"] = member_data

        # Summary
        result["issues_found"] = len(issues)
        result["issues"] = issues

        if issues:
            result["summary"] = f"Found {len(issues)} issue(s)"
        else:
            result["summary"] = "All checks passed"

    except Exception as e:
        result["success"] = False
        result["error"] = str(e)

    return result


if __name__ == "__main__":
    # Test on spoke
    print("=== SD-WAN Status Check - Spoke ===")
    result = main({
        "target_ip": "10.0.0.30",
        "check": "all"
    })
    print(json.dumps(result, indent=2))
