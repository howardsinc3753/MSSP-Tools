#!/usr/bin/env python3
"""
FortiGate BGP Troubleshooting Tool

Comprehensive BGP diagnostics for SD-WAN deployments.
Provides summary, neighbor details, received/advertised routes.

Canonical ID: org.ulysses.noc.fortigate-bgp-troubleshoot/1.0.3
"""

import json
import sys
import os
import urllib3
from typing import Optional, Dict, List, Any
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    import urllib.request
    import urllib.error
    import ssl

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


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


def api_request(host: str, api_token: str, method: str, endpoint: str,
                data: dict = None, verify_ssl: bool = False) -> dict:
    """Make FortiOS API request."""
    url = f"https://{host}/api/v2{endpoint}"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }

    if HAS_REQUESTS:
        try:
            if method == "GET":
                resp = requests.get(url, headers=headers, verify=verify_ssl, timeout=30)
            elif method == "POST":
                resp = requests.post(url, headers=headers, json=data, verify=verify_ssl, timeout=30)
            else:
                return {"success": False, "error": f"Unknown method: {method}"}

            result = {"status_code": resp.status_code, "success": resp.status_code in [200, 201]}
            try:
                result["data"] = resp.json()
            except:
                result["data"] = {"raw": resp.text}
            return result
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}
    else:
        ctx = ssl.create_default_context()
        if not verify_ssl:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

        try:
            req = urllib.request.Request(url, headers=headers, method=method)
            if data:
                req.data = json.dumps(data).encode('utf-8')

            with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                result = {"status_code": resp.status, "success": resp.status in [200, 201]}
                try:
                    result["data"] = json.loads(resp.read().decode('utf-8'))
                except:
                    result["data"] = {}
                return result
        except urllib.error.HTTPError as e:
            result = {"success": False, "status_code": e.code, "error": str(e)}
            try:
                result["data"] = json.loads(e.read().decode('utf-8'))
            except:
                pass
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}


def get_bgp_summary(host: str, api_token: str, verify_ssl: bool = False) -> dict:
    """Get BGP summary - equivalent to 'get router info bgp summary'.

    FortiOS 7.6.5: /monitor/router/bgp/summary returns 404.
    Use /monitor/router/bgp/neighbors (confirmed working) as primary.
    """
    # Primary: neighbors endpoint (works on FortiOS 7.6.5)
    result = api_request(host, api_token, "GET", "/monitor/router/bgp/neighbors", verify_ssl=verify_ssl)

    if result.get("success"):
        data = result.get("data", {}).get("results", [])
        neighbors = []
        for n in data:
            neighbors.append({
                "ip": n.get("neighbor_ip", ""),
                "remote_as": n.get("remote_as", ""),
                "local_as": n.get("local_as", ""),
                "state": n.get("state", ""),
                "up_time": n.get("up_time", ""),
                "prefixes_received": n.get("state_pfxrcd", 0),
                "messages_received": n.get("msg_rcvd", 0),
                "messages_sent": n.get("msg_sent", 0),
                "table_version": n.get("tbl_ver", 0),
                "in_queue": n.get("in_q", 0),
                "out_queue": n.get("out_q", 0),
                "admin_status": n.get("admin_status", True),
                "type": n.get("type", "")
            })

        # Get router-id and local_as from CMDB for summary context
        router_id = ""
        local_as = ""
        cmdb_result = api_request(host, api_token, "GET", "/cmdb/router/bgp", verify_ssl=verify_ssl)
        if cmdb_result.get("success"):
            cmdb_data = cmdb_result.get("data", {}).get("results", [])
            if isinstance(cmdb_data, list) and len(cmdb_data) > 0:
                cmdb_data = cmdb_data[0]
                router_id = cmdb_data.get("router-id", "")
                local_as = str(cmdb_data.get("as", ""))

        return {
            "success": True,
            "router_id": router_id,
            "local_as": local_as,
            "neighbors": neighbors,
            "neighbor_count": len(neighbors),
            "source": "monitor"
        }

    # Fallback: try legacy summary endpoints
    for endpoint in ["/monitor/router/bgp/summary", "/monitor/router/bgp"]:
        result = api_request(host, api_token, "GET", endpoint, verify_ssl=verify_ssl)
        if result.get("success"):
            data = result.get("data", {}).get("results", {})
            if isinstance(data, list):
                data = data[0] if data else {}
            summary = {
                "success": True,
                "router_id": data.get("local_id", ""),
                "local_as": data.get("local_as", ""),
                "table_version": data.get("table_version", 0),
                "neighbors": [],
                "source": "legacy_monitor"
            }
            for n in data.get("neighbors", []):
                summary["neighbors"].append({
                    "ip": n.get("neighbor_ip", ""),
                    "remote_as": n.get("remote_as", ""),
                    "state": n.get("state", ""),
                    "up_time": n.get("up_time", ""),
                    "prefixes_received": n.get("state_pfxrcd", 0),
                })
            summary["neighbor_count"] = len(summary["neighbors"])
            return summary

    # Last resort: CMDB config only (no runtime state)
    result = api_request(host, api_token, "GET", "/cmdb/router/bgp", verify_ssl=verify_ssl)
    if result.get("success"):
        data = result.get("data", {}).get("results", [])
        if isinstance(data, list) and len(data) > 0:
            data = data[0]
        neighbors = []
        for n in data.get("neighbor", []):
            neighbors.append({
                "ip": n.get("ip", ""),
                "remote_as": str(n.get("remote-as", "")),
                "state": "configured",
                "up_time": "",
                "prefixes_received": 0
            })
        return {
            "success": True,
            "router_id": data.get("router-id", ""),
            "local_as": str(data.get("as", "")),
            "neighbors": neighbors,
            "neighbor_count": len(neighbors),
            "source": "cmdb"
        }

    return {"success": False, "error": "Failed to get BGP summary from any endpoint"}


def get_bgp_neighbors(host: str, api_token: str, verify_ssl: bool = False) -> dict:
    """Get detailed BGP neighbor information."""
    result = api_request(host, api_token, "GET", "/monitor/router/bgp/neighbors", verify_ssl=verify_ssl)

    if not result.get("success"):
        return {"success": False, "error": result.get("error", "Failed to get BGP neighbors")}

    data = result.get("data", {}).get("results", [])

    neighbors = []
    for n in data:
        neighbor = {
            "ip": n.get("neighbor_ip", ""),
            "remote_as": n.get("remote_as", ""),
            "local_as": n.get("local_as", ""),
            "state": n.get("state", ""),
            "up_time": n.get("up_time", ""),
            "router_id": n.get("remote_router_id", ""),
            "bfd": n.get("bfd_status", "disabled"),
            "graceful_restart": n.get("gr_status", ""),
            "prefixes_received": n.get("state_pfxrcd", 0),
            "capabilities": {
                "ipv4_unicast": n.get("ipv4_unicast", False),
                "ipv6_unicast": n.get("ipv6_unicast", False),
                "route_refresh": n.get("route_refresh", False)
            }
        }
        neighbors.append(neighbor)

    return {
        "success": True,
        "neighbors": neighbors,
        "count": len(neighbors)
    }


def get_bgp_paths(host: str, api_token: str, neighbor_ip: str = None,
                  verify_ssl: bool = False) -> dict:
    """Get BGP paths/routes - the BGP RIB."""
    result = api_request(host, api_token, "GET", "/monitor/router/bgp/paths", verify_ssl=verify_ssl)

    if not result.get("success"):
        return {"success": False, "error": result.get("error", "Failed to get BGP paths")}

    data = result.get("data", {}).get("results", [])

    paths = []
    for p in data:
        # Handle various FortiOS API field name formats
        network = p.get("network") or p.get("prefix") or p.get("ip") or ""
        prefix_len = p.get("prefix_len") or p.get("prefixlen") or p.get("prefix-len") or p.get("netmask_len") or 0
        next_hop = p.get("nexthop") or p.get("next_hop") or p.get("next-hop") or p.get("gateway") or ""
        peer = p.get("peer") or p.get("neighbor") or p.get("from") or ""

        # Skip entries with no network (API may return metadata)
        if not network and not next_hop:
            continue

        path = {
            "network": network,
            "prefix_len": prefix_len,
            "next_hop": next_hop,
            "metric": p.get("metric") or p.get("med") or 0,
            "local_pref": p.get("local_pref") or p.get("localpref") or p.get("local-preference") or 0,
            "weight": p.get("weight") or 0,
            "as_path": p.get("as_path") or p.get("aspath") or p.get("path") or "",
            "origin": p.get("origin") or "",
            "valid": p.get("valid", False),
            "best": p.get("best", False),
            "internal": p.get("internal") or p.get("ibgp", False),
            "peer": peer,
            "raw": p  # Include raw data for debugging
        }

        # Filter by neighbor if specified
        if neighbor_ip and path["peer"] != neighbor_ip and path["next_hop"] != neighbor_ip:
            continue

        paths.append(path)

    return {
        "success": True,
        "paths": paths,
        "count": len(paths)
    }


def get_bgp_routes_received(host: str, api_token: str, neighbor_ip: str,
                            verify_ssl: bool = False) -> dict:
    """Get routes received from a specific neighbor."""
    # FortiOS API for neighbor-specific routes
    endpoint = f"/monitor/router/bgp/neighbors/{neighbor_ip}/routes"
    result = api_request(host, api_token, "GET", endpoint, verify_ssl=verify_ssl)

    if not result.get("success"):
        # Try alternate endpoint
        result = api_request(host, api_token, "GET", "/monitor/router/bgp/paths", verify_ssl=verify_ssl)
        if not result.get("success"):
            return {"success": False, "error": result.get("error", "Failed to get received routes")}

        # Filter paths by neighbor
        data = result.get("data", {}).get("results", [])
        routes = []
        for p in data:
            if p.get("peer") == neighbor_ip or p.get("nexthop") == neighbor_ip:
                routes.append({
                    "network": f"{p.get('network', '')}/{p.get('prefix_len', 0)}",
                    "next_hop": p.get("nexthop", ""),
                    "metric": p.get("metric", 0),
                    "local_pref": p.get("local_pref", 100),
                    "weight": p.get("weight", 0),
                    "as_path": p.get("as_path", ""),
                    "origin": p.get("origin", "i"),
                    "valid": p.get("valid", True),
                    "best": p.get("best", False)
                })

        return {
            "success": True,
            "neighbor": neighbor_ip,
            "routes": routes,
            "count": len(routes)
        }

    data = result.get("data", {}).get("results", [])
    routes = []
    for r in data:
        routes.append({
            "network": f"{r.get('network', '')}/{r.get('prefix_len', 0)}",
            "next_hop": r.get("nexthop", ""),
            "metric": r.get("metric", 0),
            "local_pref": r.get("local_pref", 100),
            "weight": r.get("weight", 0),
            "as_path": r.get("as_path", ""),
            "origin": r.get("origin", "i")
        })

    return {
        "success": True,
        "neighbor": neighbor_ip,
        "routes": routes,
        "count": len(routes)
    }


def get_bgp_routes_advertised(host: str, api_token: str, neighbor_ip: str,
                              verify_ssl: bool = False) -> dict:
    """Get routes advertised to a specific neighbor."""
    # FortiOS doesn't have direct API for advertised routes per neighbor
    # We get local BGP networks and RIB redistribution

    # Get BGP network statements
    result = api_request(host, api_token, "GET", "/cmdb/router/bgp", verify_ssl=verify_ssl)

    if not result.get("success"):
        return {"success": False, "error": result.get("error", "Failed to get BGP config")}

    data = result.get("data", {}).get("results", [])
    if isinstance(data, list) and len(data) > 0:
        data = data[0]

    advertised = []

    # Network statements
    networks = data.get("network", [])
    for n in networks:
        prefix = n.get("prefix", "")
        if prefix:
            advertised.append({
                "network": prefix,
                "type": "network_statement",
                "route_map": n.get("route-map", "")
            })

    # Redistributed routes (connected, static, etc.)
    redistribute = data.get("redistribute", [])
    for r in redistribute:
        if r.get("status") == "enable":
            advertised.append({
                "network": f"[{r.get('name', 'unknown')}]",
                "type": "redistribute",
                "route_map": r.get("route-map", "")
            })

    # Also get the actual paths being advertised (best paths)
    paths_result = api_request(host, api_token, "GET", "/monitor/router/bgp/paths", verify_ssl=verify_ssl)
    if paths_result.get("success"):
        paths_data = paths_result.get("data", {}).get("results", [])
        for p in paths_data:
            if p.get("best") and not p.get("peer"):  # Local routes (no peer = locally originated)
                network = f"{p.get('network', '')}/{p.get('prefix_len', 0)}"
                # Check if already in list
                existing = [a for a in advertised if a.get("network") == network]
                if not existing:
                    advertised.append({
                        "network": network,
                        "type": "local_rib",
                        "next_hop": p.get("nexthop", ""),
                        "origin": p.get("origin", "")
                    })

    return {
        "success": True,
        "neighbor": neighbor_ip,
        "advertised": advertised,
        "count": len(advertised)
    }


def get_full_bgp_report(host: str, api_token: str, verify_ssl: bool = False) -> dict:
    """Generate comprehensive BGP troubleshooting report."""
    report = {
        "success": True,
        "target_ip": host,
        "sections": {}
    }

    # BGP Summary
    summary = get_bgp_summary(host, api_token, verify_ssl)
    report["sections"]["summary"] = summary

    if not summary.get("success"):
        report["success"] = False
        report["error"] = "Failed to get BGP summary"
        return report

    report["router_id"] = summary.get("router_id", "")
    report["local_as"] = summary.get("local_as", "")

    # For each neighbor, get received and advertised routes
    neighbors_detail = []
    for n in summary.get("neighbors", []):
        neighbor_ip = n.get("ip", "")
        if not neighbor_ip:
            continue

        detail = {
            "ip": neighbor_ip,
            "remote_as": n.get("remote_as"),
            "state": n.get("state"),
            "up_time": n.get("up_time"),
            "prefixes_received": n.get("prefixes_received", 0)
        }

        # Get received routes
        received = get_bgp_routes_received(host, api_token, neighbor_ip, verify_ssl)
        if received.get("success"):
            detail["received_routes"] = received.get("routes", [])

        # Get advertised routes
        advertised = get_bgp_routes_advertised(host, api_token, neighbor_ip, verify_ssl)
        if advertised.get("success"):
            detail["advertised_routes"] = advertised.get("advertised", [])

        neighbors_detail.append(detail)

    report["sections"]["neighbors"] = neighbors_detail
    report["neighbor_count"] = len(neighbors_detail)

    return report


def main(context) -> dict:
    """Main entry point for the tool."""
    # Handle both ExecutionContext (MCP) and dict (CLI)
    if hasattr(context, 'parameters'):
        params = context.parameters
    else:
        params = context

    target_ip = params.get("target_ip")
    action = params.get("action", "summary").lower()
    neighbor_ip = params.get("neighbor_ip")
    verify_ssl = params.get("verify_ssl", False)

    if not target_ip:
        return {"success": False, "error": "target_ip is required"}

    valid_actions = ["summary", "neighbors", "paths", "received", "advertised", "report"]
    if action not in valid_actions:
        return {"success": False, "error": f"Invalid action: {action}. Must be one of: {', '.join(valid_actions)}"}

    # Get credentials - check MCP context first, then local config
    api_token = None
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
        return {"success": False, "error": f"No API credentials found for {target_ip}. Configure in fortigate_credentials.yaml"}

    result = {"action": action, "target_ip": target_ip}

    if action == "summary":
        action_result = get_bgp_summary(target_ip, api_token, verify_ssl)
        result.update(action_result)

    elif action == "neighbors":
        action_result = get_bgp_neighbors(target_ip, api_token, verify_ssl)
        result.update(action_result)

    elif action == "paths":
        action_result = get_bgp_paths(target_ip, api_token, neighbor_ip, verify_ssl)
        result.update(action_result)

    elif action == "received":
        if not neighbor_ip:
            return {"success": False, "error": "neighbor_ip is required for 'received' action"}
        action_result = get_bgp_routes_received(target_ip, api_token, neighbor_ip, verify_ssl)
        result.update(action_result)

    elif action == "advertised":
        if not neighbor_ip:
            return {"success": False, "error": "neighbor_ip is required for 'advertised' action"}
        action_result = get_bgp_routes_advertised(target_ip, api_token, neighbor_ip, verify_ssl)
        result.update(action_result)

    elif action == "report":
        action_result = get_full_bgp_report(target_ip, api_token, verify_ssl)
        result.update(action_result)

    return result


if __name__ == "__main__":
    if len(sys.argv) > 1:
        params = {}
        for arg in sys.argv[1:]:
            if '=' in arg:
                key, val = arg.split('=', 1)
                key = key.lstrip('-')
                if val.lower() in ['true', 'false']:
                    val = val.lower() == 'true'
                elif val.isdigit():
                    val = int(val)
                params[key] = val
        result = main(params)
    else:
        try:
            input_data = sys.stdin.read()
            params = json.loads(input_data) if input_data.strip() else {}
            result = main(params)
        except json.JSONDecodeError as e:
            result = {"success": False, "error": f"Invalid JSON input: {e}"}

    print(json.dumps(result, indent=2))
