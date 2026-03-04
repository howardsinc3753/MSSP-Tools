#!/usr/bin/env python3
"""
FortiGate SD-WAN Blueprint Planner

Generates CSV templates for new SD-WAN site deployments.
Reads filled templates and generates FortiOS configuration.

Workflow:
1. generate-template: Creates CSV with recommended next values
2. User fills in site-specific values
3. plan-site: Reads CSV and generates FortiOS CLI config

Based on Fortinet 4D-Demo configurations and SD-WAN manifest.
"""

import csv
import json
import os
import ipaddress
from pathlib import Path
from datetime import datetime
from typing import Any, Optional, Dict, List

# Manifest and template locations
MANIFEST_PATH = Path("C:/ProgramData/Ulysses/config/sdwan-manifest.yaml")
TEMPLATE_DIR = Path("C:/ProgramData/Ulysses/config/blueprints")


def load_manifest() -> dict:
    """Load the SD-WAN manifest."""
    import yaml

    if not MANIFEST_PATH.exists():
        return {"network": {}, "devices": {}}

    with open(MANIFEST_PATH) as f:
        return yaml.safe_load(f) or {"network": {}, "devices": {}}


def save_manifest(manifest: dict):
    """Save manifest to file."""
    import yaml
    manifest["last_updated"] = datetime.now().isoformat()
    with open(MANIFEST_PATH, 'w') as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def get_next_site_id(manifest: dict) -> int:
    """Calculate next available site ID."""
    max_id = 0
    for device in manifest.get("devices", {}).values():
        if device.get("role") == "spoke":
            # Try to extract site ID from device name or loopback
            loopback = device.get("interfaces", {}).get("loopback", [])
            for lo in loopback:
                ip = lo.get("ip", "").split()[0]
                if ip.startswith("172.16.0."):
                    try:
                        site_id = int(ip.split(".")[-1])
                        max_id = max(max_id, site_id)
                    except:
                        pass
    return max_id + 1


def get_next_loopback(manifest: dict, site_id: int = None) -> str:
    """Calculate next available loopback IP based on site_id.

    Args:
        manifest: The SD-WAN manifest
        site_id: Optional site ID to correlate loopback with (172.16.0.{site_id})

    Returns:
        Next available loopback IP
    """
    used_ips = set()

    for device in manifest.get("devices", {}).values():
        loopbacks = device.get("interfaces", {}).get("loopback", [])
        for lo in loopbacks:
            ip = lo.get("ip", "").split()[0]
            if ip and ip != "0.0.0.0":
                used_ips.add(ip)

    # If site_id provided, try to use correlated loopback 172.16.0.{site_id}
    if site_id is not None:
        candidate = f"172.16.0.{site_id}"
        if candidate not in used_ips:
            return candidate
        # If correlated IP is taken, find next available

    # Start from site_id or 1 and find next available
    start = site_id if site_id else 1
    for i in range(start, 255):
        candidate = f"172.16.0.{i}"
        if candidate not in used_ips:
            return candidate

    return "172.16.0.254"  # Fallback


def get_next_member_seq(manifest: dict, start: int = 3) -> tuple:
    """Calculate next available SD-WAN member sequence numbers."""
    used_seqs = set()

    for device in manifest.get("devices", {}).values():
        if device.get("role") == "spoke":
            members = device.get("sdwan", {}).get("members", [])
            for m in members:
                seq = m.get("seq_num", 0)
                if seq > 2:  # Skip 1,2 which are often WAN interfaces
                    used_seqs.add(seq)

    # Find next pair
    seq1, seq2 = start, start + 1
    while seq1 in used_seqs or seq2 in used_seqs:
        seq1 += 2
        seq2 += 2

    return seq1, seq2


def get_hub_info(manifest: dict) -> dict:
    """Extract hub information from manifest."""
    for key, device in manifest.get("devices", {}).items():
        if device.get("role") == "hub":
            # Get hub WAN IP
            wan_ip = device.get("management_ip", "")

            # Get hub loopbacks
            loopbacks = device.get("interfaces", {}).get("loopback", [])
            hub_lo = ""
            bgp_lo = ""
            for lo in loopbacks:
                name = lo.get("name", "").lower()
                ip = lo.get("ip", "").split()[0]
                if "hub" in name:
                    hub_lo = ip
                elif "bgp" in name:
                    bgp_lo = ip

            # Get hub IPsec network IDs
            phase1 = device.get("ipsec", {}).get("phase1", [])
            network_ids = [p.get("network_id", 0) for p in phase1]

            return {
                "wan_ip": wan_ip,
                "hub_loopback": hub_lo,
                "bgp_loopback": bgp_lo,
                "network_ids": network_ids,
                "vpn_names": [p.get("name", "") for p in phase1]
            }

    return {}


# CSV Template Schema
TEMPLATE_SCHEMA = [
    # Section: Site Identity
    {"variable": "site_name", "description": "Site name (e.g., Branch1, NYC-Office)", "example": "Branch1", "required": True, "category": "Identity"},
    {"variable": "site_id", "description": "Unique site number for tracking", "example": "1", "required": True, "category": "Identity"},
    {"variable": "loopback_ip", "description": "Site loopback IP (/32) - MUST BE UNIQUE", "example": "172.16.0.1", "required": True, "category": "Identity"},
    {"variable": "loopback_name", "description": "Loopback interface name", "example": "Spoke-Lo", "required": True, "category": "Identity"},

    # Section: WAN Interface
    {"variable": "wan_interface", "description": "WAN interface name", "example": "port1", "required": True, "category": "WAN"},
    {"variable": "wan_mode", "description": "WAN addressing mode: 'dhcp' (auto) or 'static' (manual)", "example": "dhcp", "required": True, "category": "WAN"},
    {"variable": "wan_ip", "description": "WAN IP address (required if wan_mode=static)", "example": "10.198.1.2", "required": False, "category": "WAN"},
    {"variable": "wan_netmask", "description": "WAN subnet mask (required if wan_mode=static)", "example": "255.255.255.248", "required": False, "category": "WAN"},
    {"variable": "wan_gateway", "description": "WAN default gateway (required if wan_mode=static)", "example": "10.198.1.1", "required": False, "category": "WAN"},

    # Section: LAN Interface
    {"variable": "lan_interface", "description": "LAN interface name", "example": "port2", "required": True, "category": "LAN"},
    {"variable": "lan_ip", "description": "LAN gateway IP (first usable in subnet)", "example": "10.1.1.1", "required": True, "category": "LAN"},
    {"variable": "lan_netmask", "description": "LAN subnet mask", "example": "255.255.255.0", "required": True, "category": "LAN"},
    {"variable": "lan_network", "description": "LAN network for BGP (CIDR)", "example": "10.1.1.0/24", "required": True, "category": "LAN"},
    {"variable": "lan_dhcp_server", "description": "Enable DHCP server on LAN: 'yes' or 'no'", "example": "yes", "required": True, "category": "LAN"},

    # Section: Hub Connection
    {"variable": "hub_wan_ip", "description": "Hub WAN IP (remote gateway)", "example": "10.198.5.2", "required": True, "category": "Hub"},
    {"variable": "hub_loopback", "description": "Hub loopback for health check", "example": "172.16.255.253", "required": True, "category": "Hub"},
    {"variable": "hub_bgp_loopback", "description": "Hub BGP loopback for peering", "example": "172.16.255.252", "required": True, "category": "Hub"},

    # Section: VPN Tunnels
    {"variable": "vpn1_name", "description": "VPN1 tunnel interface name", "example": "HUB1-VPN1", "required": True, "category": "VPN"},
    {"variable": "vpn1_localid", "description": "VPN1 local ID (no site suffix per GAP-42)", "example": "spoke-HUB1-VPN1", "required": True, "category": "VPN"},
    {"variable": "vpn1_network_id", "description": "VPN1 network-id (match hub)", "example": "1", "required": True, "category": "VPN"},
    {"variable": "vpn2_name", "description": "VPN2 tunnel interface name", "example": "HUB1-VPN2", "required": False, "category": "VPN"},
    {"variable": "vpn2_localid", "description": "VPN2 local ID (no site suffix per GAP-42)", "example": "spoke-HUB1-VPN2", "required": False, "category": "VPN"},
    {"variable": "vpn2_network_id", "description": "VPN2 network-id (match hub)", "example": "2", "required": False, "category": "VPN"},
    {"variable": "vpn_psk", "description": "Pre-shared key for IPsec - MUST match hub config", "example": "password", "required": True, "category": "VPN"},

    # Section: SD-WAN
    # NOTE: Zone and health check names MUST match BASELINE_TEMPLATE.yaml for BLOCK_4 verification
    {"variable": "sdwan_zone", "description": "SD-WAN zone name for overlay", "example": "SDWAN_OVERLAY", "required": True, "category": "SD-WAN"},
    {"variable": "member_seq_vpn1", "description": "SD-WAN member seq-num for VPN1", "example": "3", "required": True, "category": "SD-WAN"},
    {"variable": "member_seq_vpn2", "description": "SD-WAN member seq-num for VPN2", "example": "4", "required": False, "category": "SD-WAN"},
    {"variable": "member_priority", "description": "SD-WAN member priority", "example": "10", "required": True, "category": "SD-WAN"},
    {"variable": "health_check_name", "description": "SD-WAN health check name", "example": "HUB_Health", "required": True, "category": "SD-WAN"},

    # Section: BGP
    {"variable": "bgp_as", "description": "BGP AS number", "example": "65000", "required": True, "category": "BGP"},
    {"variable": "bgp_router_id", "description": "BGP router ID (usually loopback)", "example": "172.16.0.1", "required": True, "category": "BGP"},

    # Section: Licensing - REQUIRED to specify license type
    {"variable": "license_type", "description": "License type: 'fortiflex' (VM token) or 'standard' (hardware)", "example": "fortiflex", "required": True, "category": "Licensing"},
    {"variable": "device_model", "description": "Device model (e.g., FortiGate-VM, FortiWiFi-50G-5G)", "example": "FortiGate-VM", "required": False, "category": "Licensing"},

    # Section: Standard License (for hardware devices - FortiWiFi, FortiGate appliances)
    {"variable": "device_serial", "description": "Hardware device serial number (e.g., FW50G5TKXXXXXXXXX)", "example": "FW50G5TKXXXXXXXXX", "required": False, "category": "Standard License"},
    {"variable": "license_name", "description": "License/contract name", "example": "50G-Lab-FortiGate-SE", "required": False, "category": "Standard License"},
    {"variable": "license_start_date", "description": "License start date (YYYY-MM-DD)", "example": "2025-10-21", "required": False, "category": "Standard License"},
    {"variable": "license_end_date", "description": "License end date (YYYY-MM-DD)", "example": "2026-10-21", "required": False, "category": "Standard License"},

    # Section: FortiFlex License (for VM deployments - requires token application)
    {"variable": "fortiflex_token", "description": "FortiFlex license token (from fortiflex-token-create)", "example": "58A7B75F319C5518CD04", "required": False, "category": "FortiFlex License"},
    {"variable": "fortiflex_serial", "description": "FortiFlex serial number (FGVMXXXXXX)", "example": "FGVMMLTMXXXXXXXXX", "required": False, "category": "FortiFlex License"},
    {"variable": "fortiflex_config_id", "description": "FortiFlex config ID used to create token", "example": "53713", "required": False, "category": "FortiFlex License"},
    {"variable": "fortiflex_config_name", "description": "FortiFlex configuration name", "example": "FGT_VM_Lab1", "required": False, "category": "FortiFlex License"},
    {"variable": "fortiflex_status", "description": "FortiFlex entitlement status", "example": "ACTIVE", "required": False, "category": "FortiFlex License"},
    {"variable": "fortiflex_end_date", "description": "FortiFlex license end date (YYYY-MM-DD)", "example": "2027-05-29", "required": False, "category": "FortiFlex License"},
]


def generate_template(output_path: str = None) -> dict:
    """Generate a CSV template with recommended next values."""
    manifest = load_manifest()
    hub_info = get_hub_info(manifest)

    # Calculate recommended values
    next_site_id = get_next_site_id(manifest)
    next_loopback = get_next_loopback(manifest, site_id=next_site_id)
    next_seq1, next_seq2 = get_next_member_seq(manifest)

    # Build recommended values
    recommendations = {
        "site_name": f"Branch{next_site_id}",
        "site_id": str(next_site_id),
        "loopback_ip": next_loopback,
        "loopback_name": "Spoke-Lo",
        "wan_interface": "port1",
        "wan_mode": "dhcp",  # DHCP by default for lab environments
        "wan_ip": "",  # Not needed if wan_mode=dhcp
        "wan_netmask": "",  # Not needed if wan_mode=dhcp
        "wan_gateway": "",  # Not needed if wan_mode=dhcp
        "lan_interface": "port2",
        "lan_ip": f"10.{next_site_id}.1.1",
        "lan_netmask": "255.255.255.0",
        "lan_network": f"10.{next_site_id}.1.0/24",
        "lan_dhcp_server": "yes",  # Enable DHCP server on LAN by default
        "hub_wan_ip": hub_info.get("wan_ip", "10.0.1.1"),
        "hub_loopback": hub_info.get("hub_loopback", "172.16.255.253"),
        "hub_bgp_loopback": hub_info.get("bgp_loopback", "172.16.255.252"),
        "vpn1_name": "HUB1-VPN1",
        "vpn1_localid": "spoke-HUB1-VPN1",  # GAP-42: no site suffix, matches working spoke-07
        "vpn1_network_id": "1",
        "vpn2_name": "HUB1-VPN2",
        "vpn2_localid": "spoke-HUB1-VPN2",  # GAP-42: no site suffix, matches working spoke-07
        "vpn2_network_id": "2",
        "vpn_psk": "password",
        "sdwan_zone": "SDWAN_OVERLAY",  # MUST match BASELINE_TEMPLATE.yaml for BLOCK_4 verification
        "member_seq_vpn1": str(next_seq1),
        "member_seq_vpn2": str(next_seq2),
        "member_priority": "10",
        "health_check_name": "HUB_Health",  # MUST match BASELINE_TEMPLATE.yaml for BLOCK_4 verification
        "bgp_as": manifest.get("network", {}).get("as_number", "65000"),
        "bgp_router_id": next_loopback,
        # Licensing - user MUST specify type
        "license_type": "",  # Required: 'fortiflex' or 'standard'
        "device_model": "",
        # Standard License fields (for hardware devices)
        "device_serial": "",
        "license_name": "",
        "license_start_date": "",
        "license_end_date": "",
        # FortiFlex License fields (for VM deployments)
        "fortiflex_token": "",
        "fortiflex_serial": "",
        "fortiflex_config_id": "",
        "fortiflex_config_name": "",
        "fortiflex_status": "",
        "fortiflex_end_date": "",
    }

    # Ensure output directory exists
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

    # Generate output path
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(TEMPLATE_DIR / f"sdwan_site_template_{timestamp}.csv")

    # Write CSV
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Header row
        writer.writerow(["Variable", "Value", "Description", "Required", "Category"])

        # Write each variable with recommended value
        for item in TEMPLATE_SCHEMA:
            var = item["variable"]
            writer.writerow([
                var,
                recommendations.get(var, item.get("example", "")),
                item["description"],
                "YES" if item["required"] else "NO",
                item["category"]
            ])

    return {
        "success": True,
        "action": "generate-template",
        "output_path": output_path,
        "recommendations": recommendations,
        "existing_sites": len([d for d in manifest.get("devices", {}).values() if d.get("role") == "spoke"]),
        "next_site_id": next_site_id,
        "next_loopback": next_loopback,
        "message": f"Template generated at {output_path}. Edit values and run plan-site."
    }


def read_template(csv_path: str) -> dict:
    """Read a filled CSV template."""
    values = {}

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            var = row.get("Variable", "")
            val = row.get("Value", "")
            if var and val:
                values[var] = val

    return values


def validate_site_values(values: dict) -> tuple:
    """Validate site values from template."""
    errors = []
    warnings = []

    # Check required fields
    for item in TEMPLATE_SCHEMA:
        if item["required"] and not values.get(item["variable"]):
            errors.append(f"Missing required field: {item['variable']}")

    # Validate IP addresses
    ip_fields = ["loopback_ip", "wan_ip", "wan_gateway", "lan_ip", "hub_wan_ip", "hub_loopback", "hub_bgp_loopback", "bgp_router_id"]
    for field in ip_fields:
        val = values.get(field, "")
        if val:
            try:
                ipaddress.ip_address(val)
            except ValueError:
                errors.append(f"Invalid IP address for {field}: {val}")

    # Validate network
    lan_network = values.get("lan_network", "")
    if lan_network:
        try:
            ipaddress.ip_network(lan_network, strict=False)
        except ValueError:
            errors.append(f"Invalid network for lan_network: {lan_network}")

    # Check for uniqueness against manifest
    manifest = load_manifest()
    loopback = values.get("loopback_ip", "")
    localid1 = values.get("vpn1_localid", "")
    localid2 = values.get("vpn2_localid", "")

    for device in manifest.get("devices", {}).values():
        # Check loopback uniqueness
        for lo in device.get("interfaces", {}).get("loopback", []):
            if lo.get("ip", "").split()[0] == loopback:
                errors.append(f"Loopback IP {loopback} already in use")

        # Check localid uniqueness
        for p1 in device.get("ipsec", {}).get("phase1", []):
            if p1.get("localid") == localid1:
                errors.append(f"VPN localid {localid1} already in use")
            if localid2 and p1.get("localid") == localid2:
                errors.append(f"VPN localid {localid2} already in use")

    return errors, warnings


def generate_fortios_config(values: dict) -> str:
    """Generate FortiOS CLI configuration from template values."""
    config = []

    site_name = values.get("site_name", "Branch")
    site_id = values.get("site_id", "0")
    # Hostname MUST follow sdwan-spoke-{site_id} pattern per CONTRACT_SCHEMA
    hostname = f"sdwan-spoke-{site_id.zfill(2)}"
    loopback_ip = values.get("loopback_ip", "")
    loopback_name = values.get("loopback_name", "Spoke-Lo")

    # Licensing - determine type and extract relevant fields
    license_type = values.get("license_type", "").lower()
    device_model = values.get("device_model", "")

    # Standard license fields (hardware devices)
    device_serial = values.get("device_serial", "")
    license_name = values.get("license_name", "")
    license_start_date = values.get("license_start_date", "")
    license_end_date = values.get("license_end_date", "")

    # FortiFlex license fields (VM deployments)
    fortiflex_token = values.get("fortiflex_token", "")
    fortiflex_serial = values.get("fortiflex_serial", "")
    fortiflex_config_id = values.get("fortiflex_config_id", "")
    fortiflex_config_name = values.get("fortiflex_config_name", "")
    fortiflex_status = values.get("fortiflex_status", "")
    fortiflex_end_date = values.get("fortiflex_end_date", "")

    wan_interface = values.get("wan_interface", "port1")
    wan_mode = values.get("wan_mode", "dhcp").lower()  # "dhcp" or "static"
    wan_ip = values.get("wan_ip", "")
    wan_netmask = values.get("wan_netmask", "255.255.255.248")
    wan_gateway = values.get("wan_gateway", "")

    lan_interface = values.get("lan_interface", "port2")
    lan_ip = values.get("lan_ip", "")
    lan_netmask = values.get("lan_netmask", "255.255.255.0")
    lan_network = values.get("lan_network", "")
    lan_dhcp_server = values.get("lan_dhcp_server", "yes").lower()  # "yes" or "no"

    hub_wan_ip = values.get("hub_wan_ip", "")
    hub_loopback = values.get("hub_loopback", "")
    hub_bgp_loopback = values.get("hub_bgp_loopback", "")

    vpn1_name = values.get("vpn1_name", "HUB1-VPN1")
    vpn1_localid = values.get("vpn1_localid", "")
    vpn1_network_id = values.get("vpn1_network_id", "1")
    vpn2_name = values.get("vpn2_name", "")
    vpn2_localid = values.get("vpn2_localid", "")
    vpn2_network_id = values.get("vpn2_network_id", "2")
    vpn_psk = values.get("vpn_psk", "password")

    sdwan_zone = values.get("sdwan_zone", "SDWAN_OVERLAY")  # MUST match BASELINE_TEMPLATE.yaml
    member_seq_vpn1 = values.get("member_seq_vpn1", "3")
    member_seq_vpn2 = values.get("member_seq_vpn2", "4")
    member_priority = values.get("member_priority", "10")
    health_check_name = values.get("health_check_name", "HUB_Health")  # MUST match BASELINE_TEMPLATE.yaml

    bgp_as = values.get("bgp_as", "65000")
    bgp_router_id = values.get("bgp_router_id", loopback_ip)

    # ============ HEADER ============
    config.append(f"""# ============================================
# SD-WAN Spoke Configuration: {site_name}
# Hostname: {hostname}
# Site ID: {site_id}
# Generated: {datetime.now().isoformat()}
# ============================================
""")

    # ============ LICENSE INFORMATION ============
    if license_type == "fortiflex" and fortiflex_token:
        config.append(f"""# ============================================
# LICENSE TYPE: FortiFlex (VM Token-Based)
# ============================================
# Model: {device_model or 'FortiGate-VM'}
# FortiFlex Serial: {fortiflex_serial or 'N/A'}
# Config ID: {fortiflex_config_id or 'N/A'}
# Config Name: {fortiflex_config_name or 'N/A'}
# Status: {fortiflex_status or 'PENDING'}
# End Date: {fortiflex_end_date or 'N/A'}
#
# IMPORTANT: Run this command FIRST after initial VM boot:
#   execute vm-license {fortiflex_token}
#
# After license installation, the device will reboot.
# Then apply the remaining configuration below.
""")
    elif license_type == "standard" and device_serial:
        config.append(f"""# ============================================
# LICENSE TYPE: Standard (Hardware-Based)
# ============================================
# Model: {device_model or 'FortiGate Appliance'}
# Device Serial: {device_serial}
# License Name: {license_name or 'N/A'}
# Start Date: {license_start_date or 'N/A'}
# End Date: {license_end_date or 'N/A'}
#
# Hardware devices are pre-licensed. No token application required.
# Apply configuration directly to the device.
""")
    elif not license_type:
        config.append(f"""# ============================================
# WARNING: LICENSE TYPE NOT SPECIFIED
# ============================================
# Please specify license_type in the template:
#   - 'fortiflex' for VM deployments (requires token)
#   - 'standard' for hardware appliances (pre-licensed)
""")

    # ============ SYSTEM GLOBAL ============
    # Hostname follows sdwan-spoke-{site_id} pattern per CONTRACT_SCHEMA
    # rest-api-key-url-query REQUIRED for REST API operations
    config.append(f"""# System Global
config system global
    set hostname "{hostname}"
    set rest-api-key-url-query enable
end
""")

    # ============ SYSTEM SETTINGS ============
    # ike-tcp-port 11443 and location-id REQUIRED per CONTRACT_SCHEMA
    config.append(f"""# System Settings
config system settings
    set ike-tcp-port 11443
    set location-id {loopback_ip}
end
""")

    # ============ INTERFACES ============
    # WAN interface - DHCP or Static based on wan_mode
    if wan_mode == "dhcp":
        wan_config = f"""    edit "{wan_interface}"
        set vdom "root"
        set mode dhcp
        set allowaccess ping fgfm
        set alias "WAN1"
        set role wan
    next"""
    else:
        wan_config = f"""    edit "{wan_interface}"
        set vdom "root"
        set ip {wan_ip} {wan_netmask}
        set allowaccess ping fgfm
        set alias "WAN1"
        set role wan
    next"""

    config.append(f"""# Interfaces
config system interface
{wan_config}
    edit "{lan_interface}"
        set vdom "root"
        set ip {lan_ip} {lan_netmask}
        set allowaccess ping https ssh
        set alias "LAN"
        set device-identification enable
        set role lan
    next
    edit "{loopback_name}"
        set vdom "root"
        set ip {loopback_ip} 255.255.255.255
        set allowaccess ping
        set type loopback
    next
end
""")
    # NOTE: Do NOT pre-define tunnel interfaces (HUB1-VPN1, HUB1-VPN2) here.
    # GAP-40: Tunnel interfaces are auto-created by FortiOS when config vpn ipsec
    # phase1-interface creates the IPsec tunnels. Pre-defining with "set type tunnel"
    # causes a parse error and corrupts the SSH session buffer.

    # ============ LAN DHCP SERVER ============
    # Only add if lan_dhcp_server is enabled
    if lan_dhcp_server == "yes" and lan_network:
        try:
            net = ipaddress.ip_network(lan_network, strict=False)
            dhcp_gateway = str(list(net.hosts())[0])  # First usable IP (e.g., 10.5.1.1)
            dhcp_start = str(list(net.hosts())[1])    # Second usable IP (e.g., 10.5.1.2)
            dhcp_end = str(list(net.hosts())[-1])     # Last usable IP (e.g., 10.5.1.254)
            dhcp_netmask = str(net.netmask)
            config.append(f"""# LAN DHCP Server
config system dhcp server
    edit 1
        set dns-service default
        set default-gateway {dhcp_gateway}
        set netmask {dhcp_netmask}
        set interface "{lan_interface}"
        config ip-range
            edit 1
                set start-ip {dhcp_start}
                set end-ip {dhcp_end}
            next
        end
    next
end
""")
        except Exception as e:
            config.append(f"# DHCP server config skipped: could not parse lan_network ({e})\n")

    # ============ IPSEC PHASE1 ============
    # transport udp REQUIRED per CONTRACT_SCHEMA (TCP causes GUI issues)
    config.append(f"""# IPsec Phase1
config vpn ipsec phase1-interface
    edit "{vpn1_name}"
        set interface "{wan_interface}"
        set ike-version 2
        set peertype any
        set net-device enable
        set exchange-ip-addr4 {loopback_ip}
        set proposal aes256-sha256
        set add-route disable
        set localid "{vpn1_localid}"
        set dpd on-idle
        set idle-timeout enable
        set auto-discovery-sender enable
        set auto-discovery-receiver enable
        set network-overlay enable
        set network-id {vpn1_network_id}
        set remote-gw {hub_wan_ip}
        set psksecret {vpn_psk}
        set dpd-retrycount 2
        set dpd-retryinterval 2
        set transport udp
    next""")

    if vpn2_name:
        config.append(f"""    edit "{vpn2_name}"
        set interface "{wan_interface}"
        set ike-version 2
        set peertype any
        set net-device enable
        set exchange-ip-addr4 {loopback_ip}
        set proposal aes256-sha256
        set add-route disable
        set localid "{vpn2_localid}"
        set dpd on-idle
        set idle-timeout enable
        set auto-discovery-sender enable
        set auto-discovery-receiver enable
        set network-overlay enable
        set network-id {vpn2_network_id}
        set remote-gw {hub_wan_ip}
        set psksecret {vpn_psk}
        set dpd-retrycount 2
        set dpd-retryinterval 2
        set transport udp
    next""")

    config.append("end\n")

    # ============ IPSEC PHASE2 ============
    config.append(f"""# IPsec Phase2
config vpn ipsec phase2-interface
    edit "{vpn1_name}"
        set phase1name "{vpn1_name}"
        set proposal aes256-sha256
        set auto-negotiate enable
    next""")

    if vpn2_name:
        config.append(f"""    edit "{vpn2_name}"
        set phase1name "{vpn2_name}"
        set proposal aes256-sha256
        set auto-negotiate enable
    next""")

    config.append("end\n")

    # ============ STATIC ROUTES ============
    # Default WAN gateway route (static mode only)
    if wan_mode == "static" and wan_gateway:
        config.append(f"""# Static Routes
config router static
    edit 1
        set gateway {wan_gateway}
        set device "{wan_interface}"
    next""")
    else:
        config.append("""# Static Routes
# Note: WAN is DHCP mode - default gateway obtained automatically
config router static""")

    # CRITICAL: Routes to hub loopbacks via VPN tunnels (required for BGP)
    # These routes must exist BEFORE BGP can establish with the hub
    # Without them, BGP stays in "Connect" state indefinitely
    # Use already-extracted variables (hub_bgp_loopback from line 431, hub_loopback from line 430)
    # Fallback to defaults if empty
    if not hub_bgp_loopback:
        hub_bgp_loopback = "172.16.255.252"
    hub_health_loopback = hub_loopback if hub_loopback else "172.16.255.253"

    config.append(f"""
    # Hub loopback routes via VPN tunnels (REQUIRED FOR BGP)
    # Primary path via VPN1
    edit 100
        set dst {hub_bgp_loopback}/32
        set device "{vpn1_name}"
        set comment "BGP peer - primary"
    next
    edit 101
        set dst {hub_health_loopback}/32
        set device "{vpn1_name}"
        set comment "Health check - primary"
    next""")

    if vpn2_name:
        config.append(f"""    # ECMP path via VPN2 (equal distance for BGP multipath - GAP-27)
    edit 102
        set dst {hub_bgp_loopback}/32
        set device "{vpn2_name}"
        set comment "BGP peer - VPN2"
    next
    edit 103
        set dst {hub_health_loopback}/32
        set device "{vpn2_name}"
        set comment "Health check - VPN2"
    next""")

    config.append("""end
""")

    # ============ FIREWALL ADDRESSES ============
    # Convert CIDR to network mask
    try:
        net = ipaddress.ip_network(lan_network, strict=False)
        lan_network_addr = str(net.network_address)
        lan_network_mask = str(net.netmask)
    except:
        lan_network_addr = lan_network.split('/')[0]
        lan_network_mask = "255.255.0.0"

    config.append(f"""# Firewall Addresses
config firewall address
    edit "{site_name}-LAN"
        set subnet {lan_network_addr} {lan_network_mask}
    next
    edit "ACME_Loopback"
        set subnet 172.16.0.0 255.255.0.0
    next
end
""")

    # ============ SD-WAN ============
    members_str = member_seq_vpn1
    if vpn2_name:
        members_str = f"{member_seq_vpn1} {member_seq_vpn2}"

    config.append(f"""# SD-WAN Configuration
config system sdwan
    set status enable
    config zone
        edit "virtual-wan-link"
        next
        edit "{sdwan_zone}"
            set advpn-select enable
            set advpn-health-check "{health_check_name}"
        next
    end
    config members
        edit {member_seq_vpn1}
            set interface "{vpn1_name}"
            set zone "{sdwan_zone}"
            set source {loopback_ip}
            set priority {member_priority}
            set priority-out-sla 20
        next""")

    if vpn2_name:
        config.append(f"""        edit {member_seq_vpn2}
            set interface "{vpn2_name}"
            set zone "{sdwan_zone}"
            set source {loopback_ip}
            set priority {member_priority}
            set priority-out-sla 20
        next""")

    config.append(f"""    end
    config health-check
        edit "{health_check_name}"
            set server "{hub_loopback}"
            set update-cascade-interface disable
            set update-static-route disable
            set embed-measured-health enable
            set sla-id-redistribute 1
            set members {members_str}
            config sla
                edit 1
                    set latency-threshold 200
                    set jitter-threshold 50
                    set packetloss-threshold 5
                next
            end
        next
    end
    config neighbor
        edit "{hub_bgp_loopback}"
            set member {members_str}
            set route-metric priority
            set health-check "{health_check_name}"
        next
    end
end
""")

    # ============ BGP ============
    config.append(f"""# BGP Configuration
config router bgp
    set as {bgp_as}
    set router-id {bgp_router_id}
    set ibgp-multipath enable
    set recursive-next-hop enable
    set graceful-restart enable
    config neighbor
        edit "{hub_bgp_loopback}"
            set advertisement-interval 1
            set capability-graceful-restart enable
            set soft-reconfiguration enable
            set interface "{loopback_name}"
            set remote-as {bgp_as}
            set connect-timer 1
            set update-source "{loopback_name}"
        next
    end
    config neighbor-group
        edit "DYN_EDGE"
            set advertisement-interval 1
            set capability-graceful-restart enable
            set next-hop-self enable
            set soft-reconfiguration enable
            set interface "{loopback_name}"
            set remote-as {bgp_as}
            set update-source "{loopback_name}"
        next
    end
    config neighbor-range
        edit 1
            set prefix 172.16.0.0 255.255.0.0
            set neighbor-group "DYN_EDGE"
        next
    end
    config redistribute "connected"
        set status enable
    end
end
""")

    # ============ FIREWALL POLICIES ============
    config.append(f"""# Firewall Policies
config firewall policy
    edit 1
        set name "{site_name} to Corporate"
        set srcintf "{lan_interface}"
        set dstintf "{sdwan_zone}"
        set action accept
        set srcaddr "{site_name}-LAN"
        set dstaddr "all"
        set schedule "always"
        set service "ALL"
        set logtraffic all
    next
    edit 2
        set name "Corporate to {site_name}"
        set srcintf "{sdwan_zone}"
        set dstintf "{lan_interface}"
        set action accept
        set srcaddr "all"
        set dstaddr "{site_name}-LAN"
        set schedule "always"
        set service "ALL"
        set logtraffic all
    next
    edit 3
        set name "Health Check - Peering"
        set srcintf "{loopback_name}" "{sdwan_zone}"
        set dstintf "{loopback_name}" "{sdwan_zone}"
        set action accept
        set srcaddr "ACME_Loopback"
        set dstaddr "ACME_Loopback"
        set schedule "always"
        set service "ALL"
    next
end
""")

    return "\n".join(config)


def plan_site(csv_path: str, output_config: str = None, add_to_manifest: bool = False) -> dict:
    """Read a filled CSV and generate FortiOS configuration."""
    if not os.path.exists(csv_path):
        return {"success": False, "error": f"CSV file not found: {csv_path}"}

    # Read template values
    values = read_template(csv_path)

    # Validate
    errors, warnings = validate_site_values(values)

    if errors:
        return {
            "success": False,
            "errors": errors,
            "warnings": warnings,
            "message": "Validation failed. Fix errors and try again."
        }

    # Generate config
    config = generate_fortios_config(values)

    # Determine output path
    if not output_config:
        TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
        site_name = values.get("site_name", "site")
        output_config = str(TEMPLATE_DIR / f"{site_name}_config.txt")

    # Write config
    with open(output_config, 'w') as f:
        f.write(config)

    # Validate against contract schema
    validation = validate_against_contract(config)

    # Build result
    result = {
        "success": True,
        "action": "plan-site",
        "site_name": values.get("site_name"),
        "site_id": values.get("site_id"),
        "loopback_ip": values.get("loopback_ip"),
        "config_path": output_config,
        "config_lines": len(config.split("\n")),
        "warnings": warnings,
        "message": f"Configuration generated at {output_config}",
        # Contract validation results
        "contract_validation": validation,
        "contract_valid": validation["valid"],
        "contract_errors": validation["errors"],
        "contract_checks_passed": validation["checks_passed"],
        "contract_checks_total": validation["checks_total"]
    }

    # Include license info based on type
    license_type = values.get("license_type", "").lower()
    result["license_type"] = license_type or "not_specified"

    if license_type == "fortiflex":
        fortiflex_token = values.get("fortiflex_token", "")
        fortiflex_serial = values.get("fortiflex_serial", "")
        fortiflex_config_id = values.get("fortiflex_config_id", "")
        fortiflex_config_name = values.get("fortiflex_config_name", "")
        fortiflex_status = values.get("fortiflex_status", "")
        fortiflex_end_date = values.get("fortiflex_end_date", "")

        result["license"] = {
            "type": "fortiflex",
            "serial": fortiflex_serial,
            "token": fortiflex_token,
            "config_id": fortiflex_config_id,
            "config_name": fortiflex_config_name,
            "status": fortiflex_status or "PENDING",
            "end_date": fortiflex_end_date,
            "requires_token_application": True,
            "license_command": f"execute vm-license {fortiflex_token}" if fortiflex_token else None
        }

    elif license_type == "standard":
        device_serial = values.get("device_serial", "")
        license_name = values.get("license_name", "")
        license_start_date = values.get("license_start_date", "")
        license_end_date = values.get("license_end_date", "")

        result["license"] = {
            "type": "standard",
            "device_serial": device_serial,
            "license_name": license_name,
            "start_date": license_start_date,
            "end_date": license_end_date,
            "requires_token_application": False,
            "note": "Hardware device is pre-licensed. Apply config directly."
        }

    # Add to manifest if requested
    if add_to_manifest:
        manifest = load_manifest()
        site_id = values.get("site_id", "0")
        device_key = f"spoke_blueprint_{site_id}"

        device_entry = {
            "role": "spoke",
            "management_ip": values.get("wan_ip"),
            "device_name": values.get("site_name"),
            "loopback_ip": values.get("loopback_ip"),
            "status": "planned",
            "planned_at": datetime.now().isoformat(),
            "template_values": values,
            "license_type": license_type or "not_specified",
            "device_model": values.get("device_model", "")
        }

        # Add license info based on type
        if license_type == "fortiflex":
            device_entry["license"] = {
                "type": "fortiflex",
                "serial": values.get("fortiflex_serial", ""),
                "token": values.get("fortiflex_token", ""),
                "config_id": values.get("fortiflex_config_id", ""),
                "config_name": values.get("fortiflex_config_name", ""),
                "status": values.get("fortiflex_status", "PENDING"),
                "end_date": values.get("fortiflex_end_date", ""),
                "assigned_at": datetime.now().isoformat()
            }
        elif license_type == "standard":
            device_entry["license"] = {
                "type": "standard",
                "device_serial": values.get("device_serial", ""),
                "license_name": values.get("license_name", ""),
                "start_date": values.get("license_start_date", ""),
                "end_date": values.get("license_end_date", "")
            }

        manifest.setdefault("devices", {})[device_key] = device_entry
        save_manifest(manifest)
        result["added_to_manifest"] = True
        result["device_key"] = device_key

    return result


def validate_against_contract(config_text: str) -> dict:
    """
    Validate generated CLI config against SD-WAN spoke contract schema.

    Checks for required sections and critical settings based on CONTRACT_SCHEMA.yaml.
    All configs must pass validation before showing to user or saving.

    Args:
        config_text: Generated FortiOS CLI configuration string

    Returns:
        dict: {
            "valid": bool,
            "errors": list[str],      # Critical issues (block deployment)
            "warnings": list[str],    # Non-critical issues
            "checks_passed": int,
            "checks_total": int,
            "summary": dict
        }
    """
    errors = []
    warnings = []
    sections_found = []

    # Define required checks from CONTRACT_SCHEMA.yaml
    required_checks = [
        # (pattern, description, is_critical)
        ('set hostname "sdwan-spoke-', "Hostname must follow sdwan-spoke-{site_id} pattern", True),
        ("set rest-api-key-url-query enable", "API token URL query enabled", True),
        ("set ike-tcp-port 11443", "IKE port 11443 (not 443)", True),
        ('edit "Spoke-Lo"', "Loopback interface Spoke-Lo", True),
        ('edit "HUB1-VPN1"', "VPN tunnel HUB1-VPN1", True),
        ('edit "HUB1-VPN2"', "VPN tunnel HUB1-VPN2", True),
        ("set transport udp", "Transport UDP (not TCP)", True),
        ("set ike-version 2", "IKE version 2", True),
        ("set as 65000", "BGP AS 65000", True),
        ("set status enable", "SD-WAN enabled", True),
        ("config zone", "SD-WAN zone configured", True),
        ("config members", "SD-WAN members configured", True),
        ("config health-check", "SD-WAN health-check configured", True),
        ("set location-id", "Location ID set", True),
        ("172.16.255.252", "Static route to hub primary loopback", False),
        ("172.16.255.253", "Static route to hub secondary loopback", False),
    ]

    # Check for forbidden patterns (synced with CONTRACT_SCHEMA.yaml)
    forbidden_checks = [
        ("set transport tcp", "TCP transport causes GUI issues"),
        ("set ike-tcp-port 443", "Port 443 conflicts with HTTPS"),
        ("set add-route enable", "Routes should be via BGP"),
        ("set tunnel-search selectors", "Not supported in FortiOS 7.6.5 - parse error (GAP-45)"),
        ("set mode-cfg enable", "mode-cfg must be DISABLE - hub has it disabled (GAP-46)"),
        ("set type tunnel", "Tunnel interfaces auto-created by phase1 - pre-defining causes parse error (GAP-40)"),
    ]

    checks_passed = 0
    checks_total = len(required_checks)

    # Validate required patterns
    for pattern, description, is_critical in required_checks:
        if pattern in config_text:
            checks_passed += 1
            sections_found.append(description)
        else:
            if is_critical:
                errors.append(f"MISSING: {description} ({pattern})")
            else:
                warnings.append(f"MISSING: {description} ({pattern})")

    # Check for forbidden patterns
    for pattern, reason in forbidden_checks:
        if pattern in config_text:
            errors.append(f"FORBIDDEN: {reason} (found: {pattern})")

    # Determine validity
    is_valid = len(errors) == 0

    return {
        "valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "checks_passed": checks_passed,
        "checks_total": checks_total,
        "summary": {
            "sections_found": sections_found,
            "sections_missing": [e.split(": ")[1].split(" (")[0] for e in errors if e.startswith("MISSING")],
            "critical_settings_ok": is_valid,
            "validation_message": "All contract checks passed" if is_valid else f"{len(errors)} errors found"
        }
    }


def main(context) -> dict[str, Any]:
    """
    SD-WAN Blueprint Planner - Generate templates for new site deployments.

    Args:
        context: ExecutionContext with parameters:
            Required:
            - action: "generate-template" or "plan-site"

            For plan-site:
            - csv_path: Path to filled CSV template
            - output_config: (optional) Output path for FortiOS config
            - add_to_manifest: (optional) Add planned site to manifest

    Returns:
        dict: Result with template or config details
    """
    if hasattr(context, "parameters"):
        args = context.parameters
    else:
        args = context

    action = args.get("action", "").lower()

    try:
        if action == "generate-template":
            output_path = args.get("output_path")
            return generate_template(output_path)

        elif action == "plan-site":
            csv_path = args.get("csv_path")
            if not csv_path:
                return {"success": False, "error": "csv_path is required for plan-site action"}

            output_config = args.get("output_config")
            add_to_manifest = args.get("add_to_manifest", False)

            return plan_site(csv_path, output_config, add_to_manifest)

        elif action == "validate":
            # Validate an existing config file against contract
            config_path = args.get("config_path")
            config_text = args.get("config_text")

            if not config_path and not config_text:
                return {"success": False, "error": "config_path or config_text required for validate action"}

            if config_path and not config_text:
                try:
                    with open(config_path, 'r') as f:
                        config_text = f.read()
                except Exception as e:
                    return {"success": False, "error": f"Failed to read config file: {e}"}

            validation = validate_against_contract(config_text)
            return {
                "success": True,
                "action": "validate",
                "config_path": config_path,
                "validation": validation,
                "valid": validation["valid"],
                "errors": validation["errors"],
                "warnings": validation["warnings"],
                "checks_passed": validation["checks_passed"],
                "checks_total": validation["checks_total"],
                "message": validation["summary"]["validation_message"]
            }

        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "valid_actions": ["generate-template", "plan-site", "validate"]
            }

    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python tool.py <action> [csv_path]")
        print("Actions: generate-template, plan-site")
        sys.exit(1)

    action = sys.argv[1]

    if action == "generate-template":
        result = main({"action": "generate-template"})
    elif action == "plan-site" and len(sys.argv) >= 3:
        result = main({"action": "plan-site", "csv_path": sys.argv[2]})
    else:
        result = main({"action": action})

    print(json.dumps(result, indent=2))
