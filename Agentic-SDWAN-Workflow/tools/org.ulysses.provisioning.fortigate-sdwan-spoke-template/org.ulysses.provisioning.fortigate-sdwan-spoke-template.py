#!/usr/bin/env python3
from __future__ import annotations
"""
FortiGate SD-WAN Spoke Template Tool (WITH ADVPN)

v1.2.0 - Naming standardized to BASELINE_TEMPLATE.yaml naming_constants

Provisions a complete SD-WAN spoke configuration:
1. System settings (ike-tcp-port: 11443 CRITICAL)
2. Loopback interface (Spoke-Lo)
3. IPsec Phase1 tunnels WITH ADVPN (HUB1-VPN1, HUB1-VPN2)
4. IPsec Phase2 interfaces
5. SD-WAN zone (SDWAN_OVERLAY)
6. SD-WAN members (both tunnels)
7. SD-WAN health check (HUB_Health)
8. BGP bootstrap static routes
9. Firewall policy and address objects

CRITICAL Settings (from BASELINE_TEMPLATE.yaml critical_settings):
- transport: "udp" (NEVER "auto")
- net-device: "enable" (required for SD-WAN)
- auto-discovery-sender/receiver: "enable" (ADVPN)
- tunnel-search: "selectors" (ADVPN)
- ike-tcp-port: 11443 (NEVER default 443)
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


def decode_response(response) -> str:
    """Decode response handling gzip compression."""
    data = response.read()
    if data[:2] == b'\x1f\x8b':
        data = gzip.decompress(data)
    return data.decode('utf-8')


def make_api_request(host: str, endpoint: str, api_token: str,
                     method: str = "GET", data: dict = None,
                     verify_ssl: bool = False, timeout: int = 30) -> dict:
    """Make a request to FortiGate REST API using Bearer token auth."""
    url = f"https://{host}{endpoint}"

    ctx = ssl.create_default_context()
    if not verify_ssl:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    body = json.dumps(data).encode('utf-8') if data else None

    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_token}")

    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
        return json.loads(decode_response(response))


def create_loopback_interface(host: str, api_token: str, name: str, ip: str,
                               verify_ssl: bool = False) -> dict:
    """Create loopback interface."""
    data = {
        "name": name,
        "vdom": "root",
        "ip": ip,
        "allowaccess": "ping",
        "type": "loopback"
    }
    return make_api_request(host, "/api/v2/cmdb/system/interface", api_token,
                            "POST", data, verify_ssl)


def create_ipsec_phase1(host: str, api_token: str, name: str, interface: str,
                        remote_gw: str, psk: str, loopback_ip: str,
                        network_id: int = 1, verify_ssl: bool = False) -> dict:
    """Create IPsec Phase1-interface for spoke.

    Key settings from Fortinet 4D-Demo:
    - exchange-ip-addr4: Loopback IP for SD-WAN overlay routing
    - auto-discovery-sender/receiver: Enable ADVPN shortcut discovery
    - dhgrp: DH groups 20 21 for modern security
    - transport: UDP for consistent overlay behavior
    """
    # Extract just the IP without mask for exchange-ip-addr4
    exchange_ip = loopback_ip.split('/')[0].split()[0]

    data = {
        "name": name,
        "interface": interface,
        "ike-version": 2,
        "peertype": "any",
        "net-device": "enable",  # CRITICAL: Required for SD-WAN routing
        "exchange-ip-addr4": exchange_ip,  # Loopback IP for SD-WAN overlay routing
        "proposal": "aes256-sha256",
        "add-route": "disable",  # Routes handled by BGP, not IPsec
        "localid": f"spoke-{name}",
        "dpd": "on-idle",
        "dpd-retrycount": 3,
        "dpd-retryinterval": 5,
        "dhgrp": "20 21",  # Modern DH groups
        # ADVPN settings (CRITICAL for spoke-to-spoke shortcuts)
        "auto-discovery-sender": "enable",    # Spoke sends ADVPN shortcuts
        "auto-discovery-receiver": "enable",  # Spoke receives ADVPN shortcuts from hub
        "tunnel-search": "selectors",         # ADVPN tunnel negotiation
        "network-overlay": "enable",
        "network-id": network_id,
        "transport": "udp",  # CRITICAL: Must be UDP, never "auto"
        "remote-gw": remote_gw,
        "psksecret": psk
    }
    return make_api_request(host, "/api/v2/cmdb/vpn.ipsec/phase1-interface", api_token,
                            "POST", data, verify_ssl)


def create_ipsec_phase2(host: str, api_token: str, name: str, phase1name: str,
                        verify_ssl: bool = False) -> dict:
    """Create IPsec Phase2-interface."""
    data = {
        "name": name,
        "phase1name": phase1name,
        "proposal": "aes256-sha256",
        "auto-negotiate": "enable"
    }
    return make_api_request(host, "/api/v2/cmdb/vpn.ipsec/phase2-interface", api_token,
                            "POST", data, verify_ssl)


def create_static_route(host: str, api_token: str, seq_num: int, dst: str,
                        device: str, comment: str = "", verify_ssl: bool = False) -> dict:
    """Create static route for BGP bootstrap.

    This is critical for BGP to establish - spokes need a route to hub loopbacks
    before BGP can learn them dynamically. Routes go via the IPsec tunnel interface.

    Args:
        host: FortiGate IP
        api_token: API token
        seq_num: Route sequence number (unique ID)
        dst: Destination subnet (e.g., "172.16.255.252 255.255.255.255")
        device: Outgoing interface (e.g., "HUB1_VPN1")
        comment: Route comment for documentation
        verify_ssl: SSL verification
    """
    data = {
        "seq-num": seq_num,
        "dst": dst,
        "device": device,
        "comment": comment
    }
    return make_api_request(host, "/api/v2/cmdb/router/static", api_token,
                            "POST", data, verify_ssl)


def set_system_global(host: str, api_token: str, hostname: str = None,
                      management_ip: str = None, timezone: str = "US/Pacific",
                      admintimeout: int = 480, rest_api_key_url_query: str = "enable",
                      verify_ssl: bool = False) -> dict:
    """Set system global settings.

    Critical settings from working SD-WAN spokes:
    - hostname: Device name for identification
    - management-ip: Management IP for SD-WAN fabric
    - timezone: Local timezone
    - admintimeout: Admin session timeout (480 = 8 hours)
    - rest-api-key-url-query: Enable API key in URL (required for some operations)
    """
    data = {
        "admintimeout": admintimeout,
        "rest-api-key-url-query": rest_api_key_url_query,
        "timezone": timezone,
        "gui-auto-upgrade-setup-warning": "disable"
    }
    if hostname:
        data["hostname"] = hostname
    if management_ip:
        data["management-ip"] = management_ip

    return make_api_request(host, "/api/v2/cmdb/system/global", api_token,
                            "PUT", data, verify_ssl)


def set_system_settings(host: str, api_token: str, loopback_ip: str,
                        ike_tcp_port: int = 11443, verify_ssl: bool = False) -> dict:
    """Set system settings including location-id and ike-tcp-port.

    Critical settings:
    - location-id: Loopback IP for SD-WAN device identification
    - ike-tcp-port: IKE TCP port (11443 to avoid conflict with HTTPS 443)
    """
    # Extract just the IP without mask
    location_ip = loopback_ip.split('/')[0].split()[0]

    data = {
        "location-id": location_ip,
        "ike-tcp-port": ike_tcp_port
    }
    return make_api_request(host, "/api/v2/cmdb/system/settings", api_token,
                            "PUT", data, verify_ssl)


def set_location_id(host: str, api_token: str, loopback_ip: str,
                    verify_ssl: bool = False) -> dict:
    """Set system location-id to loopback IP for SD-WAN identification.

    DEPRECATED: Use set_system_settings() instead which also sets ike-tcp-port.
    Kept for backward compatibility.
    """
    # Extract just the IP without mask
    location_ip = loopback_ip.split('/')[0].split()[0]

    data = {"location-id": location_ip}
    return make_api_request(host, "/api/v2/cmdb/system/settings", api_token,
                            "PUT", data, verify_ssl)


def enable_sdwan(host: str, api_token: str, verify_ssl: bool = False) -> dict:
    """Enable SD-WAN if not already enabled."""
    data = {"status": "enable"}
    return make_api_request(host, "/api/v2/cmdb/system/sdwan", api_token,
                            "PUT", data, verify_ssl)


def create_sdwan_zone(host: str, api_token: str, name: str,
                      verify_ssl: bool = False) -> dict:
    """Create SD-WAN zone."""
    data = {"name": name}
    return make_api_request(host, "/api/v2/cmdb/system/sdwan/zone", api_token,
                            "POST", data, verify_ssl)


def create_sdwan_member(host: str, api_token: str, seq_num: int, interface: str,
                        zone: str, source_ip: str, priority: int = 10,
                        priority_in_sla: int = 10, priority_out_sla: int = 20,
                        verify_ssl: bool = False) -> dict:
    """Add interface as SD-WAN member with priority settings.

    Priority settings from Fortinet 4D-Demo:
    - priority: Base priority (lower = preferred)
    - priority-in-sla: Priority when SLA is met
    - priority-out-sla: Priority when SLA is not met
    """
    # Extract just IP without mask
    source = source_ip.split('/')[0].split()[0]

    data = {
        "seq-num": seq_num,
        "interface": interface,
        "zone": zone,
        "source": source,
        "priority": priority,
        "priority-in-sla": priority_in_sla,
        "priority-out-sla": priority_out_sla
    }
    return make_api_request(host, "/api/v2/cmdb/system/sdwan/members", api_token,
                            "POST", data, verify_ssl)


def detect_wan_interface(host: str, api_token: str, verify_ssl: bool = False) -> str:
    """Auto-detect the WAN interface.

    Checks for common WAN interface naming conventions:
    - wan1, wan, wan2 (hardware appliances)
    - port1, port2 (VMs and some models)
    """
    try:
        result = make_api_request(host, "/api/v2/cmdb/system/interface", api_token,
                                  "GET", verify_ssl=verify_ssl)
        interfaces = result.get("results", [])

        # Priority 1: wan1, wan, wan2
        for name in ["wan1", "wan", "wan2"]:
            for iface in interfaces:
                if iface.get("name") == name and iface.get("type") == "physical":
                    ip = iface.get("ip", "0.0.0.0 0.0.0.0")
                    if ip and not ip.startswith("0.0.0.0"):
                        return name

        # Priority 2: Any interface starting with wan
        for iface in interfaces:
            if iface.get("name", "").startswith("wan") and iface.get("type") == "physical":
                ip = iface.get("ip", "0.0.0.0 0.0.0.0")
                if ip and not ip.startswith("0.0.0.0"):
                    return iface.get("name")

        # Priority 3: port1 (common on VMs)
        for iface in interfaces:
            if iface.get("name") == "port1" and iface.get("type") == "physical":
                ip = iface.get("ip", "0.0.0.0 0.0.0.0")
                if ip and not ip.startswith("0.0.0.0"):
                    return "port1"

        # Priority 4: First physical interface with an IP
        for iface in interfaces:
            if iface.get("type") == "physical":
                ip = iface.get("ip", "0.0.0.0 0.0.0.0")
                if ip and not ip.startswith("0.0.0.0"):
                    return iface.get("name")

        return "wan1"  # Fallback
    except Exception:
        return "wan1"


def create_sdwan_health_check(host: str, api_token: str, name: str, server: str,
                               members: list, verify_ssl: bool = False) -> dict:
    """Create SD-WAN health check."""
    # FortiOS doesn't allow hyphens in health check names - replace with underscore
    safe_name = name.replace("-", "_")
    data = {
        "name": safe_name,
        "server": server,
        "protocol": "ping",
        "members": [{"seq-num": m} for m in members],
        "sla": [{
            "id": 1,
            "latency-threshold": 200,
            "jitter-threshold": 50,
            "packetloss-threshold": 5
        }]
    }
    return make_api_request(host, "/api/v2/cmdb/system/sdwan/health-check", api_token,
                            "POST", data, verify_ssl)


def configure_sdwan_zone_advpn(host: str, api_token: str, zone_name: str,
                                health_check_name: str, verify_ssl: bool = False) -> dict:
    """Configure ADVPN settings on SD-WAN zone.

    CRITICAL for spoke-to-spoke ADVPN shortcuts.
    From Spoke-02 working baseline:
    - advpn-select: enable (allows zone to use ADVPN shortcuts)
    - advpn-health-check: health check to use for ADVPN path selection
    """
    data = {
        "advpn-select": "enable",
        "advpn-health-check": health_check_name
    }
    return make_api_request(host, f"/api/v2/cmdb/system/sdwan/zone/{zone_name}",
                            api_token, "PUT", data, verify_ssl)


def create_sdwan_neighbor(host: str, api_token: str, neighbor_ip: str,
                          members: list, health_check_name: str,
                          verify_ssl: bool = False) -> dict:
    """Create SD-WAN neighbor for BGP integration.

    From Spoke-02 working baseline:
    - Neighbor IP is hub's BGP router-id (172.16.255.252)
    - member: SD-WAN member seq-nums (tunnels)
    - route-metric: priority (use SD-WAN priority for route selection)
    - health-check: health check to use for neighbor monitoring
    """
    data = {
        "ip": neighbor_ip,
        "member": [{"seq-num": m} for m in members],
        "route-metric": "priority",
        "health-check": health_check_name
    }
    return make_api_request(host, "/api/v2/cmdb/system/sdwan/neighbor",
                            api_token, "POST", data, verify_ssl)


def create_firewall_address(host: str, api_token: str, name: str, subnet: str,
                            verify_ssl: bool = False) -> dict:
    """Create firewall address object."""
    data = {
        "name": name,
        "subnet": subnet
    }
    return make_api_request(host, "/api/v2/cmdb/firewall/address", api_token,
                            "POST", data, verify_ssl)


def create_firewall_policy(host: str, api_token: str, name: str,
                           srcintf: list, dstintf: list,
                           srcaddr: list, dstaddr: list,
                           verify_ssl: bool = False) -> dict:
    """Create firewall policy."""
    data = {
        "name": name,
        "srcintf": [{"name": i} for i in srcintf],
        "dstintf": [{"name": i} for i in dstintf],
        "action": "accept",
        "srcaddr": [{"name": a} for a in srcaddr],
        "dstaddr": [{"name": a} for a in dstaddr],
        "schedule": "always",
        "service": [{"name": "ALL"}],
        "logtraffic": "all"
    }
    return make_api_request(host, "/api/v2/cmdb/firewall/policy", api_token,
                            "POST", data, verify_ssl)


def main(context) -> dict[str, Any]:
    """
    FortiGate SD-WAN Spoke Template - Provisions complete spoke configuration.

    Creates:
    1. Loopback interface for BGP/health peering
    2. IPsec Phase1 tunnel to hub
    3. IPsec Phase2 interface
    4. SD-WAN zone
    5. SD-WAN member (tunnel → zone)
    6. SD-WAN health check
    7. Firewall address objects
    8. Firewall policy (loopback ↔ SDWAN zone)

    Args:
        context: ExecutionContext with parameters:
            - target_ip: Spoke FortiGate IP
            - hub_wan_ip: Hub's public WAN IP (remote gateway)
            - loopback_ip: Spoke loopback IP (e.g., "172.16.0.1 255.255.255.255")
            - loopback_name: Loopback interface name (default: "Spoke-Lo")
            - tunnel_name: IPsec tunnel name (default: "HUB-VPN1")
            - wan_interface: WAN interface for tunnel (default: "wan1")
            - psk: Pre-shared key for IPsec
            - sdwan_zone: SD-WAN zone name (default: "SDWAN-OVERLAY")
            - hub_loopback_ip: Hub's loopback IP for health check
            - network_id: Network overlay ID 1-255 (default: 1)

    Returns:
        dict: Result with created components and any errors
    """
    if hasattr(context, "parameters"):
        args = context.parameters
    else:
        args = context

    # Required parameters
    target_ip = args.get("target_ip")
    hub_wan_ip = args.get("hub_wan_ip")
    loopback_ip = args.get("loopback_ip")
    psk = args.get("psk")

    # Optional parameters with defaults (from BASELINE_TEMPLATE naming_constants)
    loopback_name = args.get("loopback_name", "Spoke-Lo")      # Hyphen per naming_constants
    tunnel_name = args.get("tunnel_name", "HUB1-VPN1")         # Hyphen per naming_constants
    wan_interface = args.get("wan_interface")  # Auto-detect if not specified
    sdwan_zone = args.get("sdwan_zone", "SDWAN_OVERLAY")       # Underscore per naming_constants
    hub_loopback_ip = args.get("hub_loopback_ip", "172.16.255.253")
    network_id = args.get("network_id", 1)
    verify_ssl = args.get("verify_ssl", False)
    timeout = args.get("timeout", 30)

    # System global settings (NEW - from working SD-WAN spoke analysis)
    site_id = args.get("site_id")  # e.g., 4 -> derives hostname "sdwan-spoke-04"
    hostname = args.get("hostname")  # Explicit hostname, or derived from site_id
    management_ip = args.get("management_ip", target_ip)  # Default to target_ip
    timezone = args.get("timezone", "US/Pacific")
    admintimeout = args.get("admintimeout", 480)

    # Derive hostname from site_id if not explicitly provided
    if not hostname and site_id:
        hostname = f"sdwan-spoke-{str(site_id).zfill(2)}"

    # System settings
    ike_tcp_port = args.get("ike_tcp_port", 11443)

    # Dual VPN tunnel support (required for proper SD-WAN redundancy)
    create_second_vpn = args.get("create_second_vpn", True)
    tunnel_name_2 = args.get("tunnel_name_2", "HUB1-VPN2")   # Hyphen per naming_constants

    # BGP bootstrap routes - hub loopback IPs for BGP peering (CRITICAL)
    # Without these routes, BGP cannot establish to hub because spoke has no path
    # Default includes both hub BGP loopbacks from our SD-WAN design
    hub_bgp_loopbacks = args.get("hub_bgp_loopbacks", ["172.16.255.252", "172.16.255.253"])

    # Validation
    if not target_ip:
        return {"success": False, "error": "target_ip is required"}
    if not hub_wan_ip:
        return {"success": False, "error": "hub_wan_ip is required"}
    if not loopback_ip:
        return {"success": False, "error": "loopback_ip is required (e.g., '172.16.0.1 255.255.255.255')"}
    if not psk:
        return {"success": False, "error": "psk (pre-shared key) is required"}

    # Get credentials
    creds = load_credentials(target_ip)
    if not creds:
        return {"success": False, "error": f"No credentials found for {target_ip}"}
    api_token = creds.get("api_token")
    if creds.get("verify_ssl") is not None:
        verify_ssl = creds["verify_ssl"]

    # Auto-detect WAN interface if not specified
    if not wan_interface:
        wan_interface = detect_wan_interface(target_ip, api_token, verify_ssl)

    result = {
        "success": False,
        "target_ip": target_ip,
        "components_created": [],
        "errors": []
    }

    try:
        # 0a. Set system global settings (ALWAYS - admintimeout, rest-api-key-url-query are critical)
        try:
            set_system_global(target_ip, api_token, hostname=hostname,
                              management_ip=management_ip, timezone=timezone,
                              admintimeout=admintimeout, verify_ssl=verify_ssl)
            result["components_created"].append(f"admintimeout:{admintimeout}")
            result["components_created"].append("rest-api-key-url-query:enable")
            result["components_created"].append(f"timezone:{timezone}")
            if hostname:
                result["components_created"].append(f"hostname:{hostname}")
            if management_ip:
                result["components_created"].append(f"management-ip:{management_ip}")
        except Exception as e:
            result["errors"].append(f"system-global: {str(e)}")

        # 0b. Set system settings (location-id and ike-tcp-port)
        try:
            set_system_settings(target_ip, api_token, loopback_ip, ike_tcp_port, verify_ssl)
            result["components_created"].append(f"location-id:{loopback_ip.split()[0]}")
            result["components_created"].append(f"ike-tcp-port:{ike_tcp_port}")
        except Exception as e:
            result["errors"].append(f"system-settings: {str(e)}")

        # 1. Create loopback interface
        try:
            create_loopback_interface(target_ip, api_token, loopback_name, loopback_ip, verify_ssl)
            result["components_created"].append(f"loopback:{loopback_name}")
        except urllib.error.HTTPError as e:
            if e.code == 500:  # May already exist
                result["errors"].append(f"loopback:{loopback_name} may already exist")
            else:
                raise

        # 2. Create IPsec Phase1
        try:
            create_ipsec_phase1(target_ip, api_token, tunnel_name, wan_interface,
                               hub_wan_ip, psk, loopback_ip, network_id, verify_ssl)
            result["components_created"].append(f"phase1:{tunnel_name}")
        except urllib.error.HTTPError as e:
            if e.code == 500:
                result["errors"].append(f"phase1:{tunnel_name} may already exist")
            else:
                raise

        # 3. Create IPsec Phase2 for VPN1
        try:
            create_ipsec_phase2(target_ip, api_token, tunnel_name, tunnel_name, verify_ssl)
            result["components_created"].append(f"phase2:{tunnel_name}")
        except urllib.error.HTTPError as e:
            if e.code == 500:
                result["errors"].append(f"phase2:{tunnel_name} may already exist")
            else:
                raise

        # 3a. Create second VPN tunnel (HUB1_VPN2) for SD-WAN redundancy
        if create_second_vpn:
            # Phase1 for VPN2 (network-id: 2)
            try:
                create_ipsec_phase1(target_ip, api_token, tunnel_name_2, wan_interface,
                                   hub_wan_ip, psk, loopback_ip, 2, verify_ssl)  # network-id 2
                result["components_created"].append(f"phase1:{tunnel_name_2}")
            except urllib.error.HTTPError as e:
                if e.code == 500:
                    result["errors"].append(f"phase1:{tunnel_name_2} may already exist")
                else:
                    result["errors"].append(f"phase1:{tunnel_name_2}: HTTP {e.code}")

            # Phase2 for VPN2
            try:
                create_ipsec_phase2(target_ip, api_token, tunnel_name_2, tunnel_name_2, verify_ssl)
                result["components_created"].append(f"phase2:{tunnel_name_2}")
            except urllib.error.HTTPError as e:
                if e.code == 500:
                    result["errors"].append(f"phase2:{tunnel_name_2} may already exist")
                else:
                    result["errors"].append(f"phase2:{tunnel_name_2}: HTTP {e.code}")

        # 3b. Create BGP bootstrap static routes to hub loopbacks (CRITICAL for BGP)
        # Without these, BGP cannot establish because spoke has no route to hub BGP peers
        # Routes use high seq-nums (900+) to avoid conflicts with other static routes
        for idx, hub_loopback in enumerate(hub_bgp_loopbacks):
            seq_num = 900 + idx  # Start at 900 to avoid conflicts
            dst = f"{hub_loopback} 255.255.255.255"  # /32 route
            comment = f"BGP bootstrap to hub loopback {hub_loopback}"
            try:
                create_static_route(target_ip, api_token, seq_num, dst, tunnel_name, comment, verify_ssl)
                result["components_created"].append(f"static-route:{hub_loopback}/32->{tunnel_name}")
            except urllib.error.HTTPError as e:
                if e.code == 500:
                    result["errors"].append(f"static-route:{hub_loopback} may already exist")
                else:
                    # Non-fatal - BGP may still work if routes exist from prior config
                    result["errors"].append(f"static-route:{hub_loopback}: HTTP {e.code}")

        # 4. Enable SD-WAN
        try:
            enable_sdwan(target_ip, api_token, verify_ssl)
            result["components_created"].append("sdwan:enabled")
        except Exception:
            pass  # May already be enabled

        # 5. Create SD-WAN zone
        try:
            create_sdwan_zone(target_ip, api_token, sdwan_zone, verify_ssl)
            result["components_created"].append(f"zone:{sdwan_zone}")
        except urllib.error.HTTPError as e:
            if e.code == 500:
                result["errors"].append(f"zone:{sdwan_zone} may already exist")
            else:
                raise

        # 6. Create SD-WAN member for VPN1 (seq-num 100)
        try:
            create_sdwan_member(target_ip, api_token, 100, tunnel_name, sdwan_zone, loopback_ip, verify_ssl)
            result["components_created"].append(f"member:{tunnel_name}->{sdwan_zone}")
        except urllib.error.HTTPError as e:
            if e.code == 500:
                result["errors"].append(f"member:{tunnel_name} may already exist")
            else:
                raise

        # 6a. Create SD-WAN member for VPN2 (seq-num 101)
        health_check_members = [100]  # Start with VPN1
        if create_second_vpn:
            try:
                create_sdwan_member(target_ip, api_token, 101, tunnel_name_2, sdwan_zone, loopback_ip, verify_ssl)
                result["components_created"].append(f"member:{tunnel_name_2}->{sdwan_zone}")
                health_check_members.append(101)  # Add VPN2 to health check
            except urllib.error.HTTPError as e:
                if e.code == 500:
                    result["errors"].append(f"member:{tunnel_name_2} may already exist")
                    health_check_members.append(101)  # Still add to health check
                else:
                    result["errors"].append(f"member:{tunnel_name_2}: HTTP {e.code}")

        # 7. Create SD-WAN health check (includes both VPN members)
        try:
            create_sdwan_health_check(target_ip, api_token, "HUB_Health", hub_loopback_ip, health_check_members, verify_ssl)
            result["components_created"].append(f"health-check:HUB_Health (members: {health_check_members})")
        except urllib.error.HTTPError as e:
            if e.code == 500:
                result["errors"].append("health-check:HUB_Health may already exist")
            else:
                raise

        # 8. Configure SD-WAN zone ADVPN settings (CRITICAL for ADVPN shortcut tunnels)
        try:
            configure_sdwan_zone_advpn(target_ip, api_token, sdwan_zone, "HUB_Health", verify_ssl)
            result["components_created"].append(f"sdwan-zone-advpn:{sdwan_zone} (advpn-select=enable, advpn-health-check=HUB_Health)")
        except urllib.error.HTTPError as e:
            if e.code == 500:
                result["errors"].append(f"sdwan-zone-advpn:{sdwan_zone} may already be configured")
            else:
                # ADVPN zone config is critical but may fail on older firmware
                result["errors"].append(f"sdwan-zone-advpn:{sdwan_zone} failed: HTTP {e.code}")

        # 9. Create SD-WAN neighbor for BGP integration (CRITICAL for BGP over SD-WAN)
        # Uses hub loopback as neighbor IP, links to health check for route monitoring
        try:
            create_sdwan_neighbor(target_ip, api_token, hub_loopback_ip,
                                  list(range(1, len(health_check_members) + 1)),
                                  "HUB_Health", verify_ssl)
            result["components_created"].append(f"sdwan-neighbor:{hub_loopback_ip} (members: 1-{len(health_check_members)})")
        except urllib.error.HTTPError as e:
            if e.code == 500:
                result["errors"].append(f"sdwan-neighbor:{hub_loopback_ip} may already exist")
            else:
                result["errors"].append(f"sdwan-neighbor:{hub_loopback_ip} failed: HTTP {e.code}")

        # 10. Create firewall address for loopback subnet
        loopback_subnet_name = "SDWAN-Loopbacks"
        try:
            create_firewall_address(target_ip, api_token, loopback_subnet_name, "172.16.0.0 255.255.0.0", verify_ssl)
            result["components_created"].append(f"address:{loopback_subnet_name}")
        except urllib.error.HTTPError as e:
            if e.code == 500:
                result["errors"].append(f"address:{loopback_subnet_name} may already exist")

        # 11. Create firewall policy for health check / peering
        policy_name = "SDWAN_Overlay_Traffic"
        try:
            create_firewall_policy(
                target_ip, api_token,
                policy_name,
                srcintf=[loopback_name, sdwan_zone],
                dstintf=[loopback_name, sdwan_zone],
                srcaddr=["all"],
                dstaddr=["all"],
                verify_ssl=verify_ssl
            )
            result["components_created"].append(f"policy:{policy_name}")
        except urllib.error.HTTPError as e:
            if e.code == 500:
                result["errors"].append(f"policy:{policy_name} may already exist")

        result["success"] = True
        result["message"] = f"SD-WAN spoke template applied. Created {len(result['components_created'])} components."

        # Build tunnel list for summary
        tunnels = [f"{tunnel_name} (network-id: {network_id})"]
        if create_second_vpn:
            tunnels.append(f"{tunnel_name_2} (network-id: 2)")

        result["config_summary"] = {
            "hostname": hostname,
            "management_ip": management_ip,
            "timezone": timezone,
            "location_id": loopback_ip.split()[0],
            "ike_tcp_port": ike_tcp_port,
            "loopback": f"{loopback_name} ({loopback_ip})",
            "tunnels": tunnels,
            "wan_interface": wan_interface,
            "sdwan_zone": sdwan_zone,
            "sdwan_members": health_check_members,
            "health_check_target": hub_loopback_ip,
            "bgp_bootstrap_routes": [f"{ip}/32 via {tunnel_name}" for ip in hub_bgp_loopbacks]
        }

    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode()[:300]
        except:
            pass
        result["error"] = f"HTTP {e.code}: {e.reason}"
        result["details"] = error_body

    except Exception as e:
        result["error"] = str(e)

    return result


if __name__ == "__main__":
    # Test execution - Full SD-WAN spoke configuration
    # Names follow BASELINE_TEMPLATE.yaml naming_constants
    result = main({
        "target_ip": "10.0.0.40",
        "hub_wan_ip": "10.0.1.1",
        "loopback_ip": "172.16.0.4 255.255.255.255",
        "psk": "fortinet",
        # System global settings
        "site_id": 4,  # Derives hostname "sdwan-spoke-04"
        "management_ip": "10.0.0.40",
        "timezone": "US/Pacific",
        # Tunnel settings (hyphen naming per baseline)
        "tunnel_name": "HUB1-VPN1",
        "create_second_vpn": True,  # Creates HUB1-VPN2 automatically
        # SD-WAN settings (underscore for zones per baseline)
        "sdwan_zone": "SDWAN_OVERLAY",
        "hub_loopback_ip": "172.16.255.253",
        "hub_bgp_loopbacks": ["172.16.255.252", "172.16.255.253"]
    })
    print(json.dumps(result, indent=2))
