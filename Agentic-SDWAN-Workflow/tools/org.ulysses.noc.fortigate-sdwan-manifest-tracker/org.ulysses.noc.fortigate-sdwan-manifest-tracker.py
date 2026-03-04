#!/usr/bin/env python3
"""
FortiGate SD-WAN Manifest Tracker

Single source of truth for SD-WAN network inventory and configuration.
Absorbs device configurations and tracks all unique per-site settings.

Features:
- Absorb: Onboard new devices or update existing entries
- Track: Device identity, interfaces, IPsec, SD-WAN, BGP, policies
- Export: Full manifest for blueprint planning

Manifest stored at: C:/ProgramData/Ulysses/config/sdwan-manifest.yaml
"""

import urllib.request
import urllib.error
import ssl
import json
import gzip
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Optional, Dict, List

# Manifest file location
MANIFEST_PATH = Path("C:/ProgramData/Ulysses/config/sdwan-manifest.yaml")


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


def make_api_request(host: str, endpoint: str, api_token: str,
                     method: str = "GET", verify_ssl: bool = False,
                     timeout: int = 30) -> dict:
    """Make a request to FortiGate REST API."""
    url = f"https://{host}{endpoint}"

    ctx = ssl.create_default_context()
    if not verify_ssl:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_token}")

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
            return json.loads(decode_response(response))
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "results": []}
    except Exception as e:
        return {"error": str(e), "results": []}


def load_manifest() -> dict:
    """Load existing manifest or create new one."""
    import yaml

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH) as f:
            return yaml.safe_load(f) or {}

    return {
        "manifest_version": "1.0.0",
        "created": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "network": {
            "name": "SD-WAN Network",
            "as_number": 65000,
            "loopback_range": "172.16.0.0/16"
        },
        "devices": {}
    }


def save_manifest(manifest: dict):
    """Save manifest to file."""
    import yaml

    manifest["last_updated"] = datetime.now().isoformat()
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(MANIFEST_PATH, 'w') as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def get_device_identity(host: str, api_token: str, verify_ssl: bool) -> dict:
    """Get device identity information."""
    result = make_api_request(host, "/api/v2/monitor/system/status", api_token, verify_ssl=verify_ssl)

    # serial and version are at top level, hostname/model are in results
    results = result.get("results", {})
    return {
        "hostname": results.get("hostname", "unknown"),
        "serial_number": result.get("serial", "unknown"),
        "firmware": result.get("version", "unknown"),
        "build": result.get("build", 0),
        "model": results.get("model", "unknown"),
        "model_name": results.get("model_name", "unknown")
    }


def get_vdom_info(host: str, api_token: str, verify_ssl: bool) -> str:
    """Get current VDOM."""
    result = make_api_request(host, "/api/v2/cmdb/system/global", api_token, verify_ssl=verify_ssl)
    # Default to root if not multi-vdom
    return "root"


def get_interfaces(host: str, api_token: str, verify_ssl: bool) -> dict:
    """Get all interfaces organized by type."""
    result = make_api_request(host, "/api/v2/cmdb/system/interface", api_token, verify_ssl=verify_ssl)
    interfaces = result.get("results", [])

    organized = {
        "physical": [],
        "tunnel": [],
        "loopback": [],
        "vlan": [],
        "aggregate": []
    }

    for iface in interfaces:
        itype = iface.get("type", "physical")
        name = iface.get("name", "")
        ip = iface.get("ip", "0.0.0.0 0.0.0.0")

        entry = {
            "name": name,
            "ip": ip,
            "alias": iface.get("alias", ""),
            "status": iface.get("status", "up"),
            "role": iface.get("role", "undefined")
        }

        if itype == "loopback":
            organized["loopback"].append(entry)
        elif itype == "tunnel":
            entry["interface"] = iface.get("interface", "")
            organized["tunnel"].append(entry)
        elif itype == "vlan":
            entry["vlanid"] = iface.get("vlanid", 0)
            entry["interface"] = iface.get("interface", "")
            organized["vlan"].append(entry)
        elif itype == "aggregate":
            entry["member"] = [m.get("interface-name") for m in iface.get("member", [])]
            organized["aggregate"].append(entry)
        elif itype == "physical" or iface.get("type") in ["physical", "hard-switch"]:
            organized["physical"].append(entry)

    # Filter out empty categories and system interfaces
    for cat in organized:
        organized[cat] = [i for i in organized[cat]
                         if not i["name"].startswith(("l2t.", "naf.", "ssl.", "fortilink"))]

    return organized


def get_ipsec_config(host: str, api_token: str, verify_ssl: bool) -> dict:
    """Get IPsec Phase1 and Phase2 configurations."""
    phase1_result = make_api_request(host, "/api/v2/cmdb/vpn.ipsec/phase1-interface",
                                     api_token, verify_ssl=verify_ssl)
    phase2_result = make_api_request(host, "/api/v2/cmdb/vpn.ipsec/phase2-interface",
                                     api_token, verify_ssl=verify_ssl)

    phase1_list = []
    for p1 in phase1_result.get("results", []):
        phase1_list.append({
            "name": p1.get("name"),
            "type": p1.get("type", "static"),
            "interface": p1.get("interface"),
            "remote_gw": p1.get("remote-gw", "0.0.0.0"),
            "localid": p1.get("localid", ""),
            "ike_version": p1.get("ike-version", 2),
            "net_device": p1.get("net-device", "disable"),
            "network_id": p1.get("network-id", 0),
            "network_overlay": p1.get("network-overlay", "disable"),
            "exchange_ip_addr4": p1.get("exchange-ip-addr4", ""),
            "auto_discovery_sender": p1.get("auto-discovery-sender", "disable"),
            "auto_discovery_receiver": p1.get("auto-discovery-receiver", "disable"),
            "add_route": p1.get("add-route", "enable"),
            "dpd": p1.get("dpd", "on-demand"),
            "dpd_retrycount": p1.get("dpd-retrycount", 3),
            "dpd_retryinterval": p1.get("dpd-retryinterval", 20),
            "proposal": p1.get("proposal", ""),
            "transport": p1.get("transport", "udp")
        })

    phase2_list = []
    for p2 in phase2_result.get("results", []):
        phase2_list.append({
            "name": p2.get("name"),
            "phase1name": p2.get("phase1name"),
            "proposal": p2.get("proposal", ""),
            "auto_negotiate": p2.get("auto-negotiate", "disable"),
            "keylifeseconds": p2.get("keylifeseconds", 43200)
        })

    return {"phase1": phase1_list, "phase2": phase2_list}


def get_sdwan_config(host: str, api_token: str, verify_ssl: bool) -> dict:
    """Get complete SD-WAN configuration."""
    # Get SD-WAN status
    sdwan_result = make_api_request(host, "/api/v2/cmdb/system/sdwan", api_token, verify_ssl=verify_ssl)
    sdwan = sdwan_result.get("results", {})

    # Get zones
    zones_result = make_api_request(host, "/api/v2/cmdb/system/sdwan/zone", api_token, verify_ssl=verify_ssl)
    zones = []
    for z in zones_result.get("results", []):
        zones.append({
            "name": z.get("name"),
            "advpn_select": z.get("advpn-select", "disable"),
            "advpn_health_check": z.get("advpn-health-check", ""),
            "minimum_sla_meet_members": z.get("minimum-sla-meet-members", 1),
            "service_access": z.get("service-access", "allow")
        })

    # Get members
    members_result = make_api_request(host, "/api/v2/cmdb/system/sdwan/members", api_token, verify_ssl=verify_ssl)
    members = []
    for m in members_result.get("results", []):
        members.append({
            "seq_num": m.get("seq-num"),
            "interface": m.get("interface"),
            "zone": m.get("zone", "virtual-wan-link"),
            "gateway": m.get("gateway", "0.0.0.0"),
            "source": m.get("source", "0.0.0.0"),
            "priority": m.get("priority", 1),
            "weight": m.get("weight", 1),
            "cost": m.get("cost", 0),
            "status": m.get("status", "enable")
        })

    # Get health checks
    hc_result = make_api_request(host, "/api/v2/cmdb/system/sdwan/health-check", api_token, verify_ssl=verify_ssl)
    health_checks = []
    for hc in hc_result.get("results", []):
        sla_list = []
        for sla in hc.get("sla", []):
            sla_list.append({
                "id": sla.get("id", 1),
                "latency_threshold": sla.get("latency-threshold", 200),
                "jitter_threshold": sla.get("jitter-threshold", 50),
                "packetloss_threshold": sla.get("packetloss-threshold", 5),
                "link_cost_factor": sla.get("link-cost-factor", "latency"),
                "priority_in_sla": sla.get("priority-in-sla", 0),
                "priority_out_sla": sla.get("priority-out-sla", 0)
            })

        health_checks.append({
            "name": hc.get("name"),
            "server": hc.get("server", ""),
            "protocol": hc.get("protocol", "ping"),
            "detect_mode": hc.get("detect-mode", "active"),
            "embed_measured_health": hc.get("embed-measured-health", "disable"),
            "remote_probe_timeout": hc.get("remote-probe-timeout", 2500),
            "failtime": hc.get("failtime", 5),
            "recoverytime": hc.get("recoverytime", 5),
            "members": [m.get("seq-num") for m in hc.get("members", [])],
            "sla": sla_list
        })

    # Get neighbors
    neighbor_result = make_api_request(host, "/api/v2/cmdb/system/sdwan/neighbor", api_token, verify_ssl=verify_ssl)
    neighbors = []
    for n in neighbor_result.get("results", []):
        neighbors.append({
            "ip": n.get("ip"),
            "members": [m.get("seq-num") for m in n.get("member", [])],
            "route_metric": n.get("route-metric", "priority"),
            "health_check": n.get("health-check", ""),
            "sla_id": n.get("sla-id", 0),
            "minimum_sla_meet_members": n.get("minimum-sla-meet-members", 1),
            "mode": n.get("mode", "sla")
        })

    # Get services (rules)
    service_result = make_api_request(host, "/api/v2/cmdb/system/sdwan/service", api_token, verify_ssl=verify_ssl)
    services = []
    for s in service_result.get("results", []):
        services.append({
            "id": s.get("id"),
            "name": s.get("name", ""),
            "mode": s.get("mode", "sla"),
            "dst": [d.get("name") for d in s.get("dst", [])],
            "dst_negate": s.get("dst-negate", "disable"),
            "src": [src.get("name") for src in s.get("src", [])],
            "internet_service": s.get("internet-service", "disable"),
            "internet_service_app_ctrl": s.get("internet-service-app-ctrl", []),
            "health_check": s.get("health-check", ""),
            "priority_members": [m.get("seq-num") for m in s.get("priority-members", [])],
            "priority_zone": [z.get("name") for z in s.get("priority-zone", [])],
            "passive_measurement": s.get("passive-measurement", "disable"),
            "sla": [{
                "health_check": sla.get("health-check"),
                "id": sla.get("id", 1)
            } for sla in s.get("sla", [])]
        })

    return {
        "status": sdwan.get("status", "disable"),
        "zones": zones,
        "members": members,
        "health_checks": health_checks,
        "neighbors": neighbors,
        "services": services
    }


def get_bgp_config(host: str, api_token: str, verify_ssl: bool) -> dict:
    """Get BGP configuration."""
    result = make_api_request(host, "/api/v2/cmdb/router/bgp", api_token, verify_ssl=verify_ssl)
    bgp = result.get("results", {})

    if not bgp:
        return {"enabled": False}

    neighbors = []
    for n in bgp.get("neighbor", []):
        neighbors.append({
            "ip": n.get("ip"),
            "remote_as": n.get("remote-as"),
            "update_source": n.get("update-source", ""),
            "interface": n.get("interface", ""),
            "soft_reconfiguration": n.get("soft-reconfiguration", "disable"),
            "capability_graceful_restart": n.get("capability-graceful-restart", "disable"),
            "advertisement_interval": n.get("advertisement-interval", 30),
            "connect_timer": n.get("connect-timer", 60)
        })

    neighbor_groups = []
    for ng in bgp.get("neighbor-group", []):
        neighbor_groups.append({
            "name": ng.get("name"),
            "remote_as": ng.get("remote-as"),
            "update_source": ng.get("update-source", ""),
            "interface": ng.get("interface", ""),
            "next_hop_self": ng.get("next-hop-self", "disable"),
            "soft_reconfiguration": ng.get("soft-reconfiguration", "disable"),
            "capability_graceful_restart": ng.get("capability-graceful-restart", "disable"),
            "advertisement_interval": ng.get("advertisement-interval", 30)
        })

    neighbor_ranges = []
    for nr in bgp.get("neighbor-range", []):
        neighbor_ranges.append({
            "id": nr.get("id"),
            "prefix": nr.get("prefix", ""),
            "neighbor_group": nr.get("neighbor-group", "")
        })

    networks = []
    for net in bgp.get("network", []):
        networks.append({
            "id": net.get("id"),
            "prefix": net.get("prefix", ""),
            "route_map": net.get("route-map", "")
        })

    return {
        "enabled": True,
        "as_number": bgp.get("as", 0),
        "router_id": bgp.get("router-id", "0.0.0.0"),
        "ibgp_multipath": bgp.get("ibgp-multipath", "disable"),
        "ebgp_multipath": bgp.get("ebgp-multipath", "disable"),
        "recursive_next_hop": bgp.get("recursive-next-hop", "disable"),
        "recursive_inherit_priority": bgp.get("recursive-inherit-priority", "disable"),
        "graceful_restart": bgp.get("graceful-restart", "disable"),
        "neighbors": neighbors,
        "neighbor_groups": neighbor_groups,
        "neighbor_ranges": neighbor_ranges,
        "networks": networks
    }


def get_firewall_policies(host: str, api_token: str, verify_ssl: bool) -> list:
    """Get firewall policies."""
    result = make_api_request(host, "/api/v2/cmdb/firewall/policy", api_token, verify_ssl=verify_ssl)

    policies = []
    for p in result.get("results", []):
        policies.append({
            "id": p.get("policyid"),
            "name": p.get("name", ""),
            "srcintf": [i.get("name") for i in p.get("srcintf", [])],
            "dstintf": [i.get("name") for i in p.get("dstintf", [])],
            "srcaddr": [a.get("name") for a in p.get("srcaddr", [])],
            "dstaddr": [a.get("name") for a in p.get("dstaddr", [])],
            "action": p.get("action", "deny"),
            "schedule": p.get("schedule", "always"),
            "service": [s.get("name") for s in p.get("service", [])],
            "nat": p.get("nat", "disable"),
            "status": p.get("status", "enable"),
            "logtraffic": p.get("logtraffic", "utm")
        })

    return policies


def get_static_routes(host: str, api_token: str, verify_ssl: bool) -> list:
    """Get static routes."""
    result = make_api_request(host, "/api/v2/cmdb/router/static", api_token, verify_ssl=verify_ssl)

    routes = []
    for r in result.get("results", []):
        routes.append({
            "seq_num": r.get("seq-num"),
            "dst": r.get("dst", "0.0.0.0 0.0.0.0"),
            "gateway": r.get("gateway", "0.0.0.0"),
            "device": r.get("device", ""),
            "distance": r.get("distance", 10),
            "weight": r.get("weight", 0),
            "priority": r.get("priority", 1),
            "blackhole": r.get("blackhole", "disable"),
            "comment": r.get("comment", ""),
            "status": r.get("status", "enable")
        })

    return routes


def get_address_objects(host: str, api_token: str, verify_ssl: bool) -> dict:
    """Get firewall address objects and groups."""
    addr_result = make_api_request(host, "/api/v2/cmdb/firewall/address", api_token, verify_ssl=verify_ssl)
    grp_result = make_api_request(host, "/api/v2/cmdb/firewall/addrgrp", api_token, verify_ssl=verify_ssl)

    addresses = []
    for a in addr_result.get("results", []):
        addresses.append({
            "name": a.get("name"),
            "type": a.get("type", "ipmask"),
            "subnet": a.get("subnet", ""),
            "fqdn": a.get("fqdn", ""),
            "comment": a.get("comment", "")
        })

    groups = []
    for g in grp_result.get("results", []):
        groups.append({
            "name": g.get("name"),
            "member": [m.get("name") for m in g.get("member", [])],
            "comment": g.get("comment", "")
        })

    return {"addresses": addresses, "groups": groups}


def determine_role(sdwan_config: dict, ipsec_config: dict) -> str:
    """Determine if device is hub or spoke based on config."""
    # Check for dynamic IPsec tunnels (hub indicator)
    for p1 in ipsec_config.get("phase1", []):
        if p1.get("type") == "dynamic":
            return "hub"

    # Check for remote detect mode health check (hub indicator)
    for hc in sdwan_config.get("health_checks", []):
        if hc.get("detect_mode") == "remote":
            return "hub"

    # Check for auto-discovery-sender on hub
    for p1 in ipsec_config.get("phase1", []):
        if p1.get("auto_discovery_sender") == "enable" and p1.get("type") == "dynamic":
            return "hub"

    return "spoke"


def absorb_device(target_ip: str) -> dict:
    """Absorb a FortiGate device into the manifest."""
    creds = load_credentials(target_ip)
    if not creds:
        return {
            "success": False,
            "error": f"No credentials found for {target_ip}",
            "hint": "Use fortigate-credential-manager to register device first"
        }

    api_token = creds.get("api_token")
    verify_ssl = creds.get("verify_ssl", False)

    # Collect all configuration data
    identity = get_device_identity(target_ip, api_token, verify_ssl)
    vdom = get_vdom_info(target_ip, api_token, verify_ssl)
    interfaces = get_interfaces(target_ip, api_token, verify_ssl)
    ipsec = get_ipsec_config(target_ip, api_token, verify_ssl)
    sdwan = get_sdwan_config(target_ip, api_token, verify_ssl)
    bgp = get_bgp_config(target_ip, api_token, verify_ssl)
    policies = get_firewall_policies(target_ip, api_token, verify_ssl)
    static_routes = get_static_routes(target_ip, api_token, verify_ssl)
    addresses = get_address_objects(target_ip, api_token, verify_ssl)

    # Determine device role
    role = determine_role(sdwan, ipsec)

    # Create device key
    device_key = f"{role}_{target_ip.replace('.', '_')}"

    # Build device entry
    device_entry = {
        "role": role,
        "management_ip": target_ip,
        "device_name": identity.get("hostname"),
        "serial_number": identity.get("serial_number"),
        "firmware": identity.get("firmware"),
        "model": identity.get("model"),
        "model_name": identity.get("model_name"),
        "vdom": vdom,
        "last_absorbed": datetime.now().isoformat(),
        "interfaces": interfaces,
        "ipsec": ipsec,
        "sdwan": sdwan,
        "bgp": bgp,
        "policies": policies,
        "static_routes": static_routes,
        "addresses": addresses,
        # Status tracking: planned | deployed | verified
        # - 'planned': Config generated but not yet pushed to device
        # - 'deployed': Config pushed to device (or absorbed from live device)
        # - 'verified': Deployment verified (IPsec UP, BGP Established)
        "status": "deployed",  # Absorbing from live device means it's deployed
        "deployed_at": datetime.now().isoformat(),
        # Licensing - supports both 'standard' (hardware) and 'fortiflex' (VM) types
        # Populate via update-license action
        "license_type": None,  # 'standard' or 'fortiflex'
        "license": None        # License details based on type
    }

    # Load manifest, update, and save
    manifest = load_manifest()

    is_update = device_key in manifest.get("devices", {})

    # Preserve existing metadata on re-absorb
    if is_update:
        existing = manifest["devices"][device_key]
        if existing.get("license_type"):
            device_entry["license_type"] = existing["license_type"]
        if existing.get("license"):
            device_entry["license"] = existing["license"]
        # Preserve status unless it was "planned" (now "deployed")
        if existing.get("status") == "verified":
            device_entry["status"] = "verified"
        # Preserve original deployment timestamp
        if existing.get("deployed_at"):
            device_entry["deployed_at"] = existing["deployed_at"]
        if existing.get("planned_at"):
            device_entry["planned_at"] = existing["planned_at"]

    manifest.setdefault("devices", {})[device_key] = device_entry

    # Update network AS if BGP is configured
    if bgp.get("enabled") and bgp.get("as_number"):
        manifest["network"]["as_number"] = bgp["as_number"]

    save_manifest(manifest)

    return {
        "success": True,
        "action": "update" if is_update else "create",
        "device_key": device_key,
        "role": role,
        "device_name": identity.get("hostname"),
        "management_ip": target_ip,
        "serial_number": identity.get("serial_number"),
        "firmware": identity.get("firmware"),
        "summary": {
            "interfaces": sum(len(v) for v in interfaces.values()),
            "ipsec_tunnels": len(ipsec.get("phase1", [])),
            "sdwan_members": len(sdwan.get("members", [])),
            "sdwan_zones": len(sdwan.get("zones", [])),
            "sdwan_health_checks": len(sdwan.get("health_checks", [])),
            "sdwan_services": len(sdwan.get("services", [])),
            "bgp_neighbors": len(bgp.get("neighbors", [])) if bgp.get("enabled") else 0,
            "policies": len(policies),
            "static_routes": len(static_routes)
        },
        "manifest_path": str(MANIFEST_PATH)
    }


def list_devices() -> dict:
    """List all tracked devices."""
    manifest = load_manifest()
    devices = []

    for key, device in manifest.get("devices", {}).items():
        device_info = {
            "device_key": key,
            "role": device.get("role"),
            "device_name": device.get("device_name"),
            "management_ip": device.get("management_ip"),
            "serial_number": device.get("serial_number"),
            "firmware": device.get("firmware"),
            "last_absorbed": device.get("last_absorbed")
        }

        # Include license info based on type
        license_type = device.get("license_type")
        license_info = device.get("license")

        if license_type and license_info:
            device_info["license_type"] = license_type
            if license_type == "fortiflex":
                device_info["license"] = {
                    "type": "fortiflex",
                    "serial": license_info.get("serial"),
                    "status": license_info.get("status"),
                    "end_date": license_info.get("end_date"),
                    "requires_token": True
                }
            elif license_type == "standard":
                device_info["license"] = {
                    "type": "standard",
                    "device_serial": license_info.get("device_serial"),
                    "license_name": license_info.get("license_name"),
                    "end_date": license_info.get("end_date"),
                    "requires_token": False
                }

        devices.append(device_info)

    return {
        "success": True,
        "network_name": manifest.get("network", {}).get("name"),
        "as_number": manifest.get("network", {}).get("as_number"),
        "device_count": len(devices),
        "devices": devices,
        "manifest_path": str(MANIFEST_PATH)
    }


def get_device(device_key: str) -> dict:
    """Get a specific device's full manifest entry."""
    manifest = load_manifest()

    if device_key not in manifest.get("devices", {}):
        return {"success": False, "error": f"Device '{device_key}' not found in manifest"}

    return {
        "success": True,
        "device_key": device_key,
        "device": manifest["devices"][device_key]
    }


def remove_device(device_key: str) -> dict:
    """Remove a device from the manifest."""
    manifest = load_manifest()

    if device_key not in manifest.get("devices", {}):
        return {"success": False, "error": f"Device '{device_key}' not found in manifest"}

    del manifest["devices"][device_key]
    save_manifest(manifest)

    return {
        "success": True,
        "message": f"Device '{device_key}' removed from manifest",
        "remaining_devices": len(manifest.get("devices", {}))
    }


def update_license(
    device_key: str,
    license_type: str,
    # FortiFlex parameters (for VM deployments)
    fortiflex_serial: str = None,
    fortiflex_token: str = None,
    fortiflex_config_id: str = None,
    fortiflex_config_name: str = None,
    fortiflex_status: str = "ACTIVE",
    fortiflex_end_date: str = None,
    # Standard license parameters (for hardware devices)
    device_serial: str = None,
    license_name: str = None,
    license_start_date: str = None,
    license_end_date: str = None,
    device_model: str = None
) -> dict:
    """
    Update license info for a device - supports both FortiFlex (VM) and Standard (hardware) licenses.

    Args:
        device_key: Device key in manifest (e.g., "spoke_192_168_209_30")
        license_type: License type - 'fortiflex' (VM token) or 'standard' (hardware)

        For FortiFlex (VM deployments):
        - fortiflex_serial: FortiFlex serial number (FGVMXXXXXX)
        - fortiflex_token: FortiFlex license token (required)
        - fortiflex_config_id: Config ID used to generate token
        - fortiflex_config_name: FortiFlex configuration name
        - fortiflex_status: License status (ACTIVE, PENDING, STOPPED)
        - fortiflex_end_date: License end date (YYYY-MM-DD)

        For Standard (hardware devices):
        - device_serial: Hardware device serial number (e.g., FW50G5TKXXXXXXXXX)
        - license_name: License/contract name
        - license_start_date: License start date (YYYY-MM-DD)
        - license_end_date: License end date (YYYY-MM-DD)
        - device_model: Device model (e.g., FortiWiFi-50G-5G)

    Returns:
        dict: Result with updated device info
    """
    manifest = load_manifest()

    if device_key not in manifest.get("devices", {}):
        return {"success": False, "error": f"Device '{device_key}' not found in manifest"}

    license_type = license_type.lower() if license_type else ""

    if license_type not in ["fortiflex", "standard"]:
        return {
            "success": False,
            "error": f"Invalid license_type: {license_type}",
            "valid_types": ["fortiflex", "standard"],
            "hint": "Use 'fortiflex' for VM deployments (requires token), 'standard' for hardware appliances"
        }

    result = {
        "success": True,
        "device_key": device_key,
        "device_name": manifest["devices"][device_key].get("device_name"),
        "license_type": license_type
    }

    # Update based on license type
    if license_type == "fortiflex":
        if not fortiflex_token:
            return {"success": False, "error": "fortiflex_token is required for FortiFlex license type"}

        manifest["devices"][device_key]["license_type"] = "fortiflex"
        manifest["devices"][device_key]["license"] = {
            "type": "fortiflex",
            "serial": fortiflex_serial,
            "token": fortiflex_token,
            "config_id": fortiflex_config_id,
            "config_name": fortiflex_config_name,
            "status": fortiflex_status or "ACTIVE",
            "end_date": fortiflex_end_date,
            "assigned_at": datetime.now().isoformat()
        }

        result["message"] = f"FortiFlex license assigned to {device_key}"
        result["license"] = manifest["devices"][device_key]["license"]
        result["license_command"] = f"execute vm-license install {fortiflex_token}"
        result["requires_token_application"] = True
        result["next_steps"] = [
            f"1. Deploy FortiGate VM",
            f"2. Run: execute vm-license install {fortiflex_token}",
            f"3. Wait for device reboot",
            f"4. Apply SD-WAN configuration"
        ]

    elif license_type == "standard":
        if not device_serial:
            return {"success": False, "error": "device_serial is required for Standard license type"}

        manifest["devices"][device_key]["license_type"] = "standard"
        manifest["devices"][device_key]["license"] = {
            "type": "standard",
            "device_serial": device_serial,
            "device_model": device_model,
            "license_name": license_name,
            "start_date": license_start_date,
            "end_date": license_end_date,
            "assigned_at": datetime.now().isoformat()
        }

        result["message"] = f"Standard hardware license assigned to {device_key}"
        result["license"] = manifest["devices"][device_key]["license"]
        result["requires_token_application"] = False
        result["next_steps"] = [
            f"1. Hardware device {device_serial} is pre-licensed",
            f"2. Apply SD-WAN configuration directly",
            f"3. No license token application required"
        ]

    save_manifest(manifest)
    return result


def export_manifest() -> dict:
    """Export the full manifest."""
    manifest = load_manifest()

    return {
        "success": True,
        "manifest": manifest,
        "manifest_path": str(MANIFEST_PATH)
    }


def main(context) -> dict[str, Any]:
    """
    SD-WAN Manifest Tracker - Single source of truth for SD-WAN network.

    Args:
        context: ExecutionContext with parameters:
            Required:
            - action: "absorb", "list", "get", "remove", "update-license", or "export"

            For absorb:
            - target_ip: FortiGate management IP to onboard

            For get/remove:
            - device_key: Device key (e.g., "spoke_192_168_209_30")

            For update-license:
            - device_key: Device key to assign license to
            - license_type: 'fortiflex' (VM token) or 'standard' (hardware)

            For FortiFlex license (VM deployments):
            - fortiflex_serial: FortiFlex serial number (FGVMXXXXXX)
            - fortiflex_token: FortiFlex license token (required for fortiflex type)
            - fortiflex_config_id: (optional) Config ID used to generate token
            - fortiflex_config_name: (optional) FortiFlex configuration name
            - fortiflex_end_date: (optional) License end date
            - fortiflex_status: (optional) License status (ACTIVE, PENDING, STOPPED)

            For Standard license (hardware devices):
            - device_serial: Hardware device serial number (required for standard type)
            - device_model: Device model (e.g., FortiWiFi-50G-5G)
            - license_name: License/contract name
            - license_start_date: License start date (YYYY-MM-DD)
            - license_end_date: License end date (YYYY-MM-DD)

    Returns:
        dict: Result with manifest data
    """
    if hasattr(context, "parameters"):
        args = context.parameters
    else:
        args = context

    action = args.get("action", "list").lower()

    try:
        if action == "absorb":
            target_ip = args.get("target_ip")
            if not target_ip:
                return {"success": False, "error": "target_ip is required for absorb action"}
            return absorb_device(target_ip)

        elif action == "list":
            return list_devices()

        elif action == "get":
            device_key = args.get("device_key")
            if not device_key:
                return {"success": False, "error": "device_key is required for get action"}
            return get_device(device_key)

        elif action == "remove":
            device_key = args.get("device_key")
            if not device_key:
                return {"success": False, "error": "device_key is required for remove action"}
            return remove_device(device_key)

        elif action == "update-license":
            device_key = args.get("device_key")
            license_type = args.get("license_type")

            if not device_key:
                return {"success": False, "error": "device_key is required for update-license action"}
            if not license_type:
                return {
                    "success": False,
                    "error": "license_type is required for update-license action",
                    "valid_types": ["fortiflex", "standard"],
                    "hint": "Use 'fortiflex' for VM deployments (requires token), 'standard' for hardware appliances"
                }

            return update_license(
                device_key=device_key,
                license_type=license_type,
                # FortiFlex parameters
                fortiflex_serial=args.get("fortiflex_serial"),
                fortiflex_token=args.get("fortiflex_token"),
                fortiflex_config_id=args.get("fortiflex_config_id"),
                fortiflex_config_name=args.get("fortiflex_config_name"),
                fortiflex_status=args.get("fortiflex_status", "ACTIVE"),
                fortiflex_end_date=args.get("fortiflex_end_date"),
                # Standard license parameters
                device_serial=args.get("device_serial"),
                device_model=args.get("device_model"),
                license_name=args.get("license_name"),
                license_start_date=args.get("license_start_date"),
                license_end_date=args.get("license_end_date")
            )

        elif action == "export":
            return export_manifest()

        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "valid_actions": ["absorb", "list", "get", "remove", "update-license", "export"]
            }

    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python tool.py <action> [args...]")
        print("Actions: absorb, list, get, remove, update-license, export")
        print("")
        print("Examples:")
        print("  python tool.py absorb 192.168.1.1")
        print("  python tool.py list")
        print("  python tool.py get spoke_192_168_1_1")
        print("")
        print("  # FortiFlex license (VM deployments):")
        print("  python tool.py update-license spoke_192_168_1_1 fortiflex FGVMMLTMWWWWWWWWW EF0AAE0ADA1B577453E3")
        print("")
        print("  # Standard license (hardware devices):")
        print("  python tool.py update-license spoke_192_168_1_1 standard FW50G5TKXXXXXXXXX")
        sys.exit(1)

    action = sys.argv[1]

    if action == "absorb" and len(sys.argv) >= 3:
        result = main({"action": "absorb", "target_ip": sys.argv[2]})
    elif action == "get" and len(sys.argv) >= 3:
        result = main({"action": "get", "device_key": sys.argv[2]})
    elif action == "remove" and len(sys.argv) >= 3:
        result = main({"action": "remove", "device_key": sys.argv[2]})
    elif action == "update-license" and len(sys.argv) >= 4:
        device_key = sys.argv[2]
        license_type = sys.argv[3]

        if license_type == "fortiflex" and len(sys.argv) >= 6:
            result = main({
                "action": "update-license",
                "device_key": device_key,
                "license_type": "fortiflex",
                "fortiflex_serial": sys.argv[4],
                "fortiflex_token": sys.argv[5],
                "fortiflex_config_id": sys.argv[6] if len(sys.argv) > 6 else None
            })
        elif license_type == "standard" and len(sys.argv) >= 5:
            result = main({
                "action": "update-license",
                "device_key": device_key,
                "license_type": "standard",
                "device_serial": sys.argv[4],
                "license_name": sys.argv[5] if len(sys.argv) > 5 else None
            })
        else:
            result = {"success": False, "error": "Invalid arguments for update-license"}
    else:
        result = main({"action": action})

    print(json.dumps(result, indent=2))
