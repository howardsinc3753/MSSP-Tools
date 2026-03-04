#!/usr/bin/env python3
"""
KVM FortiOS Provisioning Tool

AI-driven tool to provision FortiGate VMs on KVM/Rocky Linux hypervisors.
Handles complete lifecycle: VM creation, initial config, license application.

Canonical ID: org.ulysses.sdwan.kvm-fortios-provision/1.0.0
"""

import os
import json
import sys
import re
import time
import secrets
import string
import socket
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    import paramiko
    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False


# =============================================================================
# CONSTANTS
# =============================================================================

FORTIGATE_BOOT_TIMEOUT = 180  # seconds to wait for FortiGate to boot
LICENSE_REBOOT_TIMEOUT = 180  # seconds to wait after license install
COMMAND_TIMEOUT = 30          # default command timeout
CONSOLE_ESCAPE = '\x1d'       # Ctrl+] to escape virsh console
DEFAULT_ADMIN_PASSWORD = "FG@dm!n2026!"  # Standard lab password

# FortiGate first-login behavior
# Login: admin, Password: blank, then MUST set new password (enter twice)

# Bootstrap ISO approach - more reliable than console automation
# FortiGate 7.6.x on KVM uses OpenStack cloud-init config-drive format
# See: https://docs.fortinet.com/document/fortigate/7.6.0/cloud-init-support


# =============================================================================
# BOOTSTRAP ISO GENERATION (OpenStack Config-Drive Format)
# =============================================================================

def generate_bootstrap_config(config: Dict[str, Any]) -> str:
    """
    Generate FortiOS bootstrap configuration (user_data format).

    FortiGate 7.6.x on KVM uses OpenStack cloud-init config-drive format:
    - Volume label: config-2 (with hyphen)
    - Directory structure: /openstack/latest/user_data
    - Config file: user_data (no extension)

    Configures:
    - Admin password
    - Interface configuration:
      - port1 (WAN): DHCP or static
      - port2 (LAN/BGP): Static IP on 10.254.{subnet_id}.{subnet_id}/24
    - Static routes (if static mode on port1)
    - Optional: FortiFlex license token
    """
    wan_ip = config.get("wan_ip")  # e.g., "192.168.1.100/24" or None for DHCP
    wan_gateway = config.get("wan_gateway")
    admin_password = config.get("admin_password", DEFAULT_ADMIN_PASSWORD)
    hostname = config.get("hostname", "FortiGate-VM")
    use_dhcp = config.get("use_dhcp", False) or not wan_ip
    subnet_id = config.get("subnet_id")  # For BGP network: 10.254.{subnet_id}.{subnet_id}/24
    lan_ip = config.get("lan_ip")  # e.g., "10.7.1.1/24" - FortiGate's LAN gateway IP
    site_id = config.get("site_id")  # If provided, derive lan_ip as 10.{site_id}.1.1/24

    # Build config - CRITICAL: password-policy disable must come FIRST
    # This prevents FortiOS from forcing password change on first login
    lines = [
        f"config system password-policy",
        f"    set status disable",
        f"end",
        f"",
        f"config system admin",
        f"    edit \"admin\"",
        f"        set password {admin_password}",
        f"        set force-password-change disable",
        f"    next",
        f"end",
        f"",
        f"config system global",
        f"    set hostname {hostname}",
        f"    set timezone 04",
        f"    set admintimeout 480",
        f"    set rest-api-key-url-query enable",  # CRITICAL: Required for REST API config push
        f"end",
        f"",
        f"config system interface",
        f"  edit port1",
    ]

    # port1 = WAN (DHCP or static)
    if use_dhcp:
        lines.extend([
            f"    set mode dhcp",
            f"    set allowaccess ping https ssh http fgfm",
            f"    set role wan",
        ])
    else:
        lines.extend([
            f"    set mode static",
            f"    set ip {wan_ip}",
            f"    set allowaccess ping https ssh http fgfm",
            f"    set role wan",
        ])

    lines.extend([
        f"  next",
    ])

    # port2 = LAN interface configuration
    # Priority: 1) explicit lan_ip, 2) derive from site_id, 3) subnet_id (legacy BGP)
    port2_ip = None
    port2_mask = "255.255.255.0"

    if lan_ip:
        # Explicit LAN IP provided (e.g., "10.7.1.1/24")
        if "/" in lan_ip:
            ip_part, cidr = lan_ip.split("/")
            port2_ip = ip_part
            # Convert CIDR to netmask (simple /24 handling)
            if cidr == "24":
                port2_mask = "255.255.255.0"
        else:
            port2_ip = lan_ip
    elif site_id:
        # Derive LAN IP from site_id: 10.{site_id}.1.1/24
        # This is the FortiGate's gateway address on the LAN subnet
        port2_ip = f"10.{site_id}.1.1"
    elif subnet_id:
        # Legacy BGP network format: 10.254.{subnet_id}.{subnet_id}/24
        port2_ip = f"10.254.{subnet_id}.{subnet_id}"

    if port2_ip:
        lines.extend([
            f"  edit port2",
            f"    set mode static",
            f"    set ip {port2_ip} {port2_mask}",
            f"    set allowaccess ping https ssh",
            f"    set role lan",
            f"  next",
        ])

    lines.extend([
        f"end",
    ])

    # Add static route only if not using DHCP
    if not use_dhcp and wan_gateway:
        lines.extend([
            f"",
            f"config router static",
            f"  edit 1",
            f"    set gateway {wan_gateway}",
            f"    set device port1",
            f"  next",
            f"end",
        ])

    return "\n".join(lines)


def create_bootstrap_iso(client, config: Dict[str, Any],
                         iso_path: str = "/tmp/fgt-bootstrap.iso") -> Dict[str, Any]:
    """
    Create FortiOS bootstrap ISO on the hypervisor using OpenStack cloud-init config-drive format.

    FortiGate 7.6.x on KVM requires:
    - Volume label: config-2 (with hyphen, NOT config2)
    - Directory structure: /openstack/latest/user_data
    - Config file: user_data (no extension)

    FortiOS will read this config on first boot of a FRESH disk.
    """
    result = {
        "success": False,
        "iso_path": iso_path,
        "config_applied": []
    }

    try:
        # Generate bootstrap config
        bootstrap_config = generate_bootstrap_config(config)

        # Remove any existing ISO file (xorriso fails with permission error if file exists)
        exec_command(client, f"rm -f {iso_path}")

        # Create OpenStack cloud-init config-drive directory structure
        # CRITICAL: FortiGate 7.6.x expects /openstack/latest/user_data format
        # Also needs /openstack/content/0000 empty file (verified working procedure)
        exit_code, stdout, stderr = exec_command(
            client, "rm -rf /tmp/fgt-bootstrap && mkdir -p /tmp/fgt-bootstrap/openstack/content /tmp/fgt-bootstrap/openstack/latest"
        )

        # Create empty content file (required by FortiOS cloud-init)
        exec_command(client, "touch /tmp/fgt-bootstrap/openstack/content/0000")

        # Write config file to OpenStack cloud-init location
        # File must be named 'user_data' (no extension) at /openstack/latest/
        exit_code, stdout, stderr = exec_command(
            client, f"cat > /tmp/fgt-bootstrap/openstack/latest/user_data << 'FGTEOF'\n{bootstrap_config}\nFGTEOF"
        )
        if exit_code != 0:
            result["error"] = f"Failed to write bootstrap config: {stderr}"
            return result

        # Check which ISO tool is available
        exit_code, _, _ = exec_command(client, "which genisoimage")
        if exit_code == 0:
            iso_cmd = "genisoimage"
        else:
            exit_code, _, _ = exec_command(client, "which mkisofs")
            if exit_code == 0:
                iso_cmd = "mkisofs"
            else:
                # Try to install genisoimage
                exec_command(client, "dnf install -y genisoimage 2>/dev/null || yum install -y genisoimage 2>/dev/null")
                iso_cmd = "genisoimage"

        # Create ISO using verified working procedure from Rocky Linux testing
        # Use mkisofs -R -r (no volume label needed - FortiOS finds /openstack/latest/user_data)
        exit_code, stdout, stderr = exec_command(
            client,
            f"{iso_cmd} -R -r -o {iso_path} /tmp/fgt-bootstrap/",
            timeout=30
        )
        if exit_code != 0:
            result["error"] = f"Failed to create ISO: {stderr}"
            return result

        # Verify ISO was created
        exit_code, stdout, stderr = exec_command(client, f"ls -la {iso_path}")
        if exit_code != 0:
            result["error"] = "ISO file not created"
            return result

        result["success"] = True
        result["config_applied"] = [
            f"Admin password set",
            f"port1: {config.get('wan_ip')}",
            f"Gateway: {config.get('wan_gateway')}",
            f"Hostname: {config.get('hostname', 'FortiGate-VM')}"
        ]

        # Cleanup temp directory
        exec_command(client, "rm -rf /tmp/fgt-bootstrap")

    except Exception as e:
        result["error"] = f"Bootstrap ISO creation failed: {str(e)}"

    return result


# =============================================================================
# CREDENTIAL LOADING
# =============================================================================

def get_hypervisor_credentials() -> Dict[str, Any]:
    """Load hypervisor credentials from config file."""
    if not HAS_YAML:
        raise ImportError("PyYAML is required: pip install pyyaml")

    cred_file = Path.home() / ".config" / "mcp" / "hypervisor_credentials.yaml"
    if not cred_file.exists():
        return {"hypervisors": {}, "default_hypervisor": None}

    with open(cred_file, 'r') as f:
        return yaml.safe_load(f) or {}


def get_hypervisor(hypervisor_id: str = None) -> Tuple[str, Dict[str, Any]]:
    """Get hypervisor config by ID or return default."""
    config = get_hypervisor_credentials()

    if not hypervisor_id:
        hypervisor_id = config.get("default_hypervisor")

    if not hypervisor_id:
        raise ValueError("No hypervisor specified and no default set. "
                         "Use hypervisor-credential-manager to add one.")

    hypervisors = config.get("hypervisors", {})
    if hypervisor_id not in hypervisors:
        raise ValueError(f"Hypervisor '{hypervisor_id}' not found in credentials")

    return hypervisor_id, hypervisors[hypervisor_id]


# =============================================================================
# PASSWORD GENERATION
# =============================================================================

def generate_admin_password(length: int = 16) -> str:
    """Generate strong random password for FortiGate admin."""
    # FortiGate password requirements:
    # - At least 8 characters
    # - Mix of uppercase, lowercase, numbers, special chars
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"

    # Ensure at least one of each category
    password = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*")
    ]
    password += [secrets.choice(alphabet) for _ in range(length - 4)]
    secrets.SystemRandom().shuffle(password)
    return ''.join(password)


# =============================================================================
# SSH CONNECTION
# =============================================================================

def connect_ssh(hv_config: Dict[str, Any]) -> paramiko.SSHClient:
    """Create SSH connection to hypervisor."""
    if not HAS_PARAMIKO:
        raise ImportError("paramiko is required: pip install paramiko")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    auth_method = hv_config.get("auth_method", "password")

    if auth_method == "key":
        key_path = Path(hv_config["ssh_key_path"]).expanduser()
        private_key = paramiko.RSAKey.from_private_key_file(str(key_path))
        client.connect(
            hostname=hv_config["host"],
            port=hv_config.get("port", 22),
            username=hv_config.get("username", "root"),
            pkey=private_key,
            timeout=30,
            look_for_keys=False,
            allow_agent=False
        )
    else:
        client.connect(
            hostname=hv_config["host"],
            port=hv_config.get("port", 22),
            username=hv_config.get("username", "root"),
            password=hv_config.get("password"),
            timeout=30,
            look_for_keys=False,
            allow_agent=False
        )

    return client


def exec_command(client: paramiko.SSHClient, cmd: str,
                 timeout: int = COMMAND_TIMEOUT) -> Tuple[int, str, str]:
    """Execute command and return (exit_code, stdout, stderr)."""
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    return exit_code, stdout.read().decode('utf-8'), stderr.read().decode('utf-8')


# =============================================================================
# PRE-FLIGHT CHECKS
# =============================================================================

def preflight_check(client: paramiko.SSHClient, hv_config: Dict[str, Any],
                    site_name: str) -> Dict[str, Any]:
    """Run pre-flight checks before provisioning."""
    results = {
        "passed": True,
        "checks": []
    }

    vm_name = f"FortiGate-{site_name}"

    # Check libvirtd running
    exit_code, stdout, stderr = exec_command(client, "systemctl is-active libvirtd")
    check = {"name": "libvirtd_running", "passed": exit_code == 0}
    if not check["passed"]:
        check["error"] = "libvirtd service is not running"
        results["passed"] = False
    results["checks"].append(check)

    # Check base image exists
    base_image = hv_config.get("base_image_path", "/home/libvirt/images/fortios-7.6.5-base.qcow2")
    exit_code, stdout, stderr = exec_command(client, f"test -f {base_image}")
    check = {"name": "base_image_exists", "path": base_image, "passed": exit_code == 0}
    if not check["passed"]:
        check["error"] = f"Base image not found: {base_image}"
        results["passed"] = False
    results["checks"].append(check)

    # Check WAN bridge exists
    wan_bridge = hv_config.get("wan_bridge", "br0")
    exit_code, stdout, stderr = exec_command(client, f"ip link show {wan_bridge}")
    check = {"name": "wan_bridge_exists", "bridge": wan_bridge, "passed": exit_code == 0}
    if not check["passed"]:
        check["error"] = f"WAN bridge not found: {wan_bridge}"
        results["passed"] = False
    results["checks"].append(check)

    # Check VM name not already used
    exit_code, stdout, stderr = exec_command(client, f"virsh dominfo {vm_name} 2>/dev/null")
    check = {"name": "vm_name_available", "vm_name": vm_name, "passed": exit_code != 0}
    if not check["passed"]:
        check["error"] = f"VM already exists: {vm_name}"
        results["passed"] = False
    results["checks"].append(check)

    # Check disk space (need at least 5GB)
    vm_image_path = hv_config.get("vm_image_path", "/home/libvirt/images/")
    exit_code, stdout, stderr = exec_command(
        client, f"df -BG {vm_image_path} | tail -1 | awk '{{print $4}}'"
    )
    if exit_code == 0:
        free_space = stdout.strip().replace('G', '')
        try:
            free_gb = int(free_space)
            check = {"name": "disk_space", "free_gb": free_gb, "passed": free_gb >= 5}
            if not check["passed"]:
                check["error"] = f"Insufficient disk space: {free_gb}GB (need 5GB+)"
                results["passed"] = False
        except ValueError:
            check = {"name": "disk_space", "passed": False, "error": "Could not parse disk space"}
            results["passed"] = False
    else:
        check = {"name": "disk_space", "passed": False, "error": "Could not check disk space"}
        results["passed"] = False
    results["checks"].append(check)

    return results


# =============================================================================
# NETWORK CREATION
# =============================================================================

def create_virtual_network(client: paramiko.SSHClient, subnet_id: int) -> Dict[str, Any]:
    """Create virtual network VM-Net-XX for BGP peering."""
    net_name = f"VM-Net-{subnet_id}"
    bridge_name = f"virbr{subnet_id}"
    subnet = f"10.254.{subnet_id}.0/24"
    gateway = f"10.254.{subnet_id}.1"

    # Check if network already exists
    exit_code, stdout, stderr = exec_command(client, f"virsh net-info {net_name} 2>/dev/null")
    if exit_code == 0:
        # Network exists, ensure it's started
        exec_command(client, f"virsh net-start {net_name} 2>/dev/null")
        return {
            "success": True,
            "action": "existing",
            "name": net_name,
            "bridge": bridge_name,
            "subnet": subnet,
            "gateway": gateway
        }

    # Create network XML
    net_xml = f"""<network>
  <name>{net_name}</name>
  <bridge name='{bridge_name}' stp='on' delay='0'/>
  <ip address='{gateway}' netmask='255.255.255.0'>
  </ip>
</network>"""

    # Write XML to temp file
    exit_code, stdout, stderr = exec_command(
        client, f"cat > /tmp/{net_name}.xml << 'NETEOF'\n{net_xml}\nNETEOF"
    )

    # Define network
    exit_code, stdout, stderr = exec_command(client, f"virsh net-define /tmp/{net_name}.xml")
    if exit_code != 0:
        return {"success": False, "error": f"Failed to define network: {stderr}"}

    # Start network
    exit_code, stdout, stderr = exec_command(client, f"virsh net-start {net_name}")
    if exit_code != 0:
        return {"success": False, "error": f"Failed to start network: {stderr}"}

    # Autostart network
    exec_command(client, f"virsh net-autostart {net_name}")

    # Cleanup temp file
    exec_command(client, f"rm -f /tmp/{net_name}.xml")

    return {
        "success": True,
        "action": "created",
        "name": net_name,
        "bridge": bridge_name,
        "subnet": subnet,
        "gateway": gateway
    }


# =============================================================================
# VM CREATION
# =============================================================================

def create_fortigate_vm(client: paramiko.SSHClient, hv_config: Dict[str, Any],
                        site_name: str, memory_mb: int = 4096,
                        vcpus: int = 2, bootstrap_iso: str = None,
                        bgp_network: str = None) -> Dict[str, Any]:
    """Create FortiGate VM with proper SCSI disk configuration.

    Args:
        client: Paramiko SSH client connected to hypervisor
        hv_config: Hypervisor configuration dict
        site_name: Site name for VM naming
        memory_mb: Memory in MB (default 4096)
        vcpus: Number of vCPUs (default 2)
        bootstrap_iso: Path to bootstrap ISO for initial config (optional)
        bgp_network: Name of BGP/LAN network (e.g., "VM-Net-4") for port2

    NIC Order (CRITICAL - determines FortiOS port mapping):
        - First --network = port1 (WAN - br0 bridge, DHCP)
        - Second --network = port2 (LAN - BGP network, static IP)
    """
    vm_name = f"FortiGate-{site_name}"
    base_image = hv_config.get("base_image_path", "/home/libvirt/images/fortios-7.6.5-base.qcow2")
    vm_image_path = hv_config.get("vm_image_path", "/home/libvirt/images/")
    wan_bridge = hv_config.get("wan_bridge", "br0")

    # Target image path
    target_image = f"{vm_image_path}fortigate-{site_name}.qcow2"

    # CRITICAL: FortiOS only reads bootstrap ISO on FIRST BOOT of a FRESH disk
    # If the disk exists from a previous attempt, FortiOS will ignore the ISO
    # and boot to factory defaults (192.168.1.99)
    #
    # Must remove any existing disk before copying fresh base image
    exit_code, stdout, stderr = exec_command(client, f"rm -f {target_image}")

    # Copy FRESH base image (not a previously-booted disk)
    exit_code, stdout, stderr = exec_command(
        client, f"cp {base_image} {target_image}", timeout=120
    )
    if exit_code != 0:
        return {"success": False, "error": f"Failed to copy image: {stderr}"}

    # Verify we have a fresh copy (should be similar size to base image)
    exit_code, stdout, stderr = exec_command(client, f"ls -la {target_image}")
    if exit_code != 0:
        return {"success": False, "error": f"Target image not created: {target_image}"}

    # Set ownership
    exec_command(client, f"chown qemu:qemu {target_image}")

    # Build virt-install command
    # CRITICAL: Use SCSI disk bus (FortiOS lacks virtio disk drivers at boot)
    # CRITICAL: NIC order determines FortiOS port mapping!
    #   - First NIC = port1 (WAN)
    #   - Second NIC = port2 (LAN/BGP)
    virt_cmd = f"""virt-install \\
  --name {vm_name} \\
  --memory {memory_mb} \\
  --vcpus {vcpus} \\
  --cpu host-passthrough \\
  --disk path={target_image},bus=scsi,format=qcow2 \\
  --controller type=scsi,model=virtio-scsi \\
  --network bridge={wan_bridge},model=virtio \\
  --network network={bgp_network},model=virtio \\
  --os-variant linux2024 \\
  --graphics vnc,listen=0.0.0.0 \\
  --serial pty \\
  --console pty,target_type=serial \\
  --import \\
  --noautoconsole"""

    # Add bootstrap ISO if provided (FortiOS reads fgt-vm.conf on first boot)
    if bootstrap_iso:
        virt_cmd += f" \\\n  --cdrom {bootstrap_iso}"

    virt_cmd += " \\\n  --boot hd"

    # Execute virt-install
    exit_code, stdout, stderr = exec_command(client, virt_cmd, timeout=120)
    if exit_code != 0:
        # Cleanup on failure
        exec_command(client, f"rm -f {target_image}")
        return {"success": False, "error": f"virt-install failed: {stderr}"}

    # Get VNC port
    exit_code, stdout, stderr = exec_command(client, f"virsh vncdisplay {vm_name}")
    vnc_display = stdout.strip() if exit_code == 0 else ":0"
    vnc_port = 5900 + int(vnc_display.replace(':', '').split()[0]) if vnc_display else 5900

    # Get VM state
    exit_code, stdout, stderr = exec_command(client, f"virsh domstate {vm_name}")
    vm_state = stdout.strip() if exit_code == 0 else "unknown"

    return {
        "success": True,
        "vm_name": vm_name,
        "state": vm_state,
        "vnc_display": vnc_display,
        "vnc_port": vnc_port,
        "disk_image": target_image
    }


def attach_bgp_network(client: paramiko.SSHClient, vm_name: str,
                       network_name: str) -> Dict[str, Any]:
    """Attach BGP/SD-WAN network to VM as third interface."""
    # Attach interface (both config and live)
    cmd = f"virsh attach-interface {vm_name} network {network_name} --model virtio --config --live"
    exit_code, stdout, stderr = exec_command(client, cmd)

    if exit_code != 0:
        return {"success": False, "error": f"Failed to attach interface: {stderr}"}

    return {"success": True, "network": network_name}


def get_vm_interfaces(client: paramiko.SSHClient, vm_name: str) -> List[Dict[str, Any]]:
    """Get list of VM interfaces with MAC addresses."""
    exit_code, stdout, stderr = exec_command(client, f"virsh domiflist {vm_name}")
    if exit_code != 0:
        return []

    interfaces = []
    port_num = 1

    for line in stdout.strip().split('\n')[2:]:  # Skip header lines
        parts = line.split()
        if len(parts) >= 5:
            interfaces.append({
                "fortigate_port": f"port{port_num}",
                "interface": parts[0],
                "type": parts[1],
                "source": parts[2],
                "model": parts[3],
                "mac_address": parts[4]
            })
            port_num += 1

    return interfaces


def discover_dhcp_ip(client: paramiko.SSHClient, vm_name: str,
                     bridge: str = "br0", timeout: int = 60) -> Optional[str]:
    """
    Discover DHCP-assigned IP for a VM by correlating MAC address with ARP table.

    Args:
        client: SSH client connected to hypervisor
        vm_name: Name of the VM
        bridge: Bridge interface to look for (default: br0)
        timeout: Maximum seconds to wait for DHCP (default: 60)

    Returns:
        IP address if found, None otherwise
    """
    # Get VM's MAC address on the bridge
    interfaces = get_vm_interfaces(client, vm_name)
    mac_address = None

    for iface in interfaces:
        if iface.get("source") == bridge:
            mac_address = iface.get("mac_address")
            break

    if not mac_address:
        # Try first interface if specific bridge not found
        if interfaces:
            mac_address = interfaces[0].get("mac_address")

    if not mac_address:
        return None

    # Wait for DHCP with retry
    start_time = time.time()
    while time.time() - start_time < timeout:
        # Broadcast ping to populate ARP table
        exec_command(client, "ping -c 1 -b 10.0.0.255 2>/dev/null || true")

        # Check ARP table for the MAC
        exit_code, stdout, stderr = exec_command(
            client,
            f"arp -an | grep -i '{mac_address}' | awk -F'[()]' '{{print $2}}'"
        )

        if exit_code == 0 and stdout.strip():
            ip_address = stdout.strip().split('\n')[0]  # Take first match
            if ip_address and re.match(r'^\d+\.\d+\.\d+\.\d+$', ip_address):
                return ip_address

        time.sleep(5)

    return None


# =============================================================================
# FORTIGATE CONSOLE AUTOMATION
# =============================================================================

def wait_for_pattern(channel, pattern: str, timeout: int = 60) -> Tuple[bool, str]:
    """Wait for a pattern in channel output."""
    buffer = ""
    start_time = time.time()

    while time.time() - start_time < timeout:
        if channel.recv_ready():
            data = channel.recv(4096).decode('utf-8', errors='ignore')
            buffer += data
            if pattern.lower() in buffer.lower():
                return True, buffer
        time.sleep(0.5)

    return False, buffer


def configure_fortigate_console(client: paramiko.SSHClient, vm_name: str,
                                config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Configure FortiGate via virsh console.

    FortiGate first-login behavior:
    1. Login: admin
    2. Password: blank (press Enter)
    3. MUST set new password (enter twice)
    4. Then configure interfaces and apply license
    """
    result = {
        "success": False,
        "steps_completed": [],
        "steps_failed": [],
        "console_log": ""
    }

    try:
        # Open interactive shell
        channel = client.invoke_shell()
        channel.settimeout(300)
        time.sleep(1)

        # Start virsh console
        channel.send(f"virsh console {vm_name}\n")
        time.sleep(2)

        # Wait for console connection message, then press Enter to get login prompt
        found, output = wait_for_pattern(channel, "Escape character", timeout=10)
        result["console_log"] += output

        # Send Enter to wake up console
        channel.send("\n")
        time.sleep(1)

        # Wait for login prompt (FortiGate boot can take 2-3 minutes)
        found, output = wait_for_pattern(channel, "login:", timeout=FORTIGATE_BOOT_TIMEOUT)
        result["console_log"] += output

        if not found:
            result["steps_failed"].append("Wait for login prompt")
            result["error"] = "FortiGate did not reach login prompt within timeout"
            # Escape console
            channel.send(CONSOLE_ESCAPE)
            return result

        result["steps_completed"].append("FortiGate booted")

        # Login as admin with blank password
        channel.send("admin\n")
        time.sleep(1)

        found, output = wait_for_pattern(channel, "Password:", timeout=10)
        result["console_log"] += output

        if found:
            # Send blank password (factory default)
            channel.send("\n")
            time.sleep(2)

            # Check for "New Password" prompt (first-login password change)
            found, output = wait_for_pattern(channel, "New Password:", timeout=10)
            result["console_log"] += output

            if found:
                # FortiGate requires setting new password
                admin_password = config.get("admin_password", generate_admin_password())
                config["admin_password"] = admin_password  # Store generated password

                # Enter new password
                channel.send(f"{admin_password}\n")
                time.sleep(1)

                # Confirm new password
                found, output = wait_for_pattern(channel, "Confirm Password:", timeout=10)
                result["console_log"] += output
                channel.send(f"{admin_password}\n")
                time.sleep(2)

                result["steps_completed"].append("Admin password set")
            else:
                # May already be at CLI prompt
                pass

        # Wait for CLI prompt (# or $)
        found, output = wait_for_pattern(channel, "#", timeout=30)
        result["console_log"] += output

        if not found:
            result["steps_failed"].append("Reach CLI prompt")
            result["error"] = "Could not reach FortiGate CLI prompt"
            channel.send(CONSOLE_ESCAPE)
            return result

        result["steps_completed"].append("Logged into CLI")

        # Configure port1 (WAN)
        wan_ip = config.get("wan_ip")
        if wan_ip:
            commands = [
                "config system interface",
                "edit port1",
                f"set ip {wan_ip}",
                "set allowaccess ping https ssh http",
                "next",
                "end"
            ]
            for cmd in commands:
                channel.send(f"{cmd}\n")
                time.sleep(0.5)

            found, output = wait_for_pattern(channel, "#", timeout=10)
            result["console_log"] += output
            result["steps_completed"].append(f"Configured port1: {wan_ip}")

        # Configure default gateway
        wan_gateway = config.get("wan_gateway")
        if wan_gateway:
            commands = [
                "config router static",
                "edit 1",
                f"set gateway {wan_gateway}",
                "set device port1",
                "next",
                "end"
            ]
            for cmd in commands:
                channel.send(f"{cmd}\n")
                time.sleep(0.5)

            found, output = wait_for_pattern(channel, "#", timeout=10)
            result["console_log"] += output
            result["steps_completed"].append(f"Configured default route via {wan_gateway}")

        # Apply FortiFlex license if provided
        fortiflex_token = config.get("fortiflex_token")
        if fortiflex_token:
            channel.send(f"execute vm-license install {fortiflex_token}\n")
            time.sleep(5)

            found, output = wait_for_pattern(channel, "Rebooting", timeout=30)
            result["console_log"] += output

            if found or "success" in output.lower():
                result["steps_completed"].append("FortiFlex license applied")
                result["license_applied"] = True
                result["will_reboot"] = True
            else:
                result["steps_failed"].append("Apply FortiFlex license")
                result["license_error"] = output

        # Escape from console
        time.sleep(1)
        channel.send(CONSOLE_ESCAPE)
        time.sleep(1)

        result["success"] = len(result["steps_failed"]) == 0
        result["admin_password"] = config.get("admin_password")

    except Exception as e:
        result["error"] = f"Console automation error: {str(e)}"
        result["steps_failed"].append(f"Exception: {str(e)}")

    return result


# =============================================================================
# POST-REBOOT VALIDATION
# =============================================================================

def wait_for_fortigate_online(client: paramiko.SSHClient, vm_name: str,
                              wan_ip: str, timeout: int = LICENSE_REBOOT_TIMEOUT) -> Dict[str, Any]:
    """Wait for FortiGate to come back online after license reboot."""
    result = {
        "online": False,
        "waited_seconds": 0
    }

    # Extract just the IP without mask
    ip_only = wan_ip.split('/')[0] if '/' in wan_ip else wan_ip

    start_time = time.time()
    while time.time() - start_time < timeout:
        # Check if VM is running
        exit_code, stdout, stderr = exec_command(client, f"virsh domstate {vm_name}")
        if exit_code != 0 or "running" not in stdout.lower():
            time.sleep(5)
            continue

        # Try to ping the FortiGate
        exit_code, stdout, stderr = exec_command(
            client, f"ping -c 1 -W 2 {ip_only}", timeout=10
        )
        if exit_code == 0:
            result["online"] = True
            result["waited_seconds"] = int(time.time() - start_time)
            break

        time.sleep(5)

    return result


# =============================================================================
# ACTION HANDLERS
# =============================================================================

def action_provision(params: Dict[str, Any]) -> Dict[str, Any]:
    """Full provisioning workflow: create VM with bootstrap config.

    Uses bootstrap ISO for initial configuration (more reliable than console automation).
    FortiOS reads fgt-vm.conf from attached ISO on first boot.
    """
    site_name = params.get("site_name")
    subnet_id = params.get("subnet_id")
    wan_ip = params.get("wan_ip")  # Optional if use_dhcp=True
    wan_gateway = params.get("wan_gateway")  # Optional if use_dhcp=True
    use_dhcp = params.get("use_dhcp", False)
    memory_mb = params.get("memory_mb", 4096)
    vcpus = params.get("vcpus", 2)
    admin_password = params.get("admin_password", DEFAULT_ADMIN_PASSWORD)
    fortiflex_token = params.get("fortiflex_token")
    hypervisor_id = params.get("hypervisor")

    # Validate required params
    if not site_name:
        return {"success": False, "error": "site_name is required"}
    if not subnet_id:
        return {"success": False, "error": "subnet_id is required (e.g., 30 for 10.254.30.0/24)"}
    if not use_dhcp and not wan_ip:
        return {"success": False, "error": "wan_ip is required (or set use_dhcp=true)"}
    if not use_dhcp and not wan_gateway:
        return {"success": False, "error": "wan_gateway is required (or set use_dhcp=true)"}

    result = {
        "success": False,
        "site_name": site_name,
        "phases": {}
    }

    bootstrap_iso = f"/tmp/fgt-bootstrap-{site_name}.iso"

    try:
        # Get hypervisor config
        hv_id, hv_config = get_hypervisor(hypervisor_id)
        result["hypervisor"] = {"id": hv_id, "host": hv_config["host"]}

        # Connect to hypervisor
        client = connect_ssh(hv_config)
        result["phases"]["ssh_connect"] = {"success": True}

        # Phase 1: Pre-flight checks
        preflight = preflight_check(client, hv_config, site_name)
        result["phases"]["preflight"] = preflight
        if not preflight["passed"]:
            client.close()
            result["error"] = "Pre-flight checks failed"
            return result

        # Phase 2: Create virtual network for BGP
        network = create_virtual_network(client, subnet_id)
        result["phases"]["network"] = network
        if not network["success"]:
            client.close()
            return result

        # Phase 3: Create bootstrap ISO
        # Includes port1 (WAN) and port2 (LAN/BGP) configuration
        bootstrap_config = {
            "wan_ip": wan_ip,
            "wan_gateway": wan_gateway,
            "use_dhcp": use_dhcp,
            "admin_password": admin_password,
            "hostname": f"FortiGate-{site_name}",
            "subnet_id": subnet_id  # For port2 BGP IP: 10.254.{subnet_id}.{subnet_id}/24
        }
        iso_result = create_bootstrap_iso(client, bootstrap_config, bootstrap_iso)
        result["phases"]["bootstrap_iso"] = iso_result
        if not iso_result["success"]:
            client.close()
            result["error"] = f"Bootstrap ISO creation failed: {iso_result.get('error')}"
            return result

        # Phase 4: Create FortiGate VM with bootstrap ISO and BGP network attached
        # CRITICAL: BGP network is attached at creation time to ensure correct NIC order
        #   - port1 = br0 (WAN - DHCP)
        #   - port2 = VM-Net-{subnet_id} (LAN - BGP static IP)
        vm = create_fortigate_vm(client, hv_config, site_name, memory_mb, vcpus,
                                 bootstrap_iso, bgp_network=network["name"])
        result["phases"]["vm_create"] = vm
        if not vm["success"]:
            # Cleanup ISO on failure
            exec_command(client, f"rm -f {bootstrap_iso}")
            client.close()
            return result

        result["vm"] = {
            "name": vm["vm_name"],
            "state": vm["state"],
            "vnc_port": vm["vnc_port"]
        }

        # Phase 5: BGP network already attached at VM creation (for correct NIC order)
        result["phases"]["attach_network"] = {"success": True, "network": network["name"],
                                               "note": "Attached at VM creation for correct port order"}

        # Get interface info
        interfaces = get_vm_interfaces(client, vm["vm_name"])
        result["interfaces"] = interfaces

        # Store credentials
        result["credentials"] = {
            "admin_password": admin_password,
            "management_ip": wan_ip.split('/')[0] if wan_ip and '/' in wan_ip else (wan_ip or "DHCP")
        }

        # Phase 6: Wait for FortiGate to boot and apply bootstrap config
        # CRITICAL: FortiOS needs 60+ seconds to boot, mount ISO, read config, and apply settings
        # The ISO MUST remain available during this entire boot process
        result["phases"]["bootstrap_apply"] = {
            "status": "pending",
            "note": "FortiOS will apply bootstrap config on first boot (60-90 seconds)"
        }

        # Track ISO cleanup - only delete after confirmed success
        iso_cleanup_ok = False

        # If DHCP mode, wait for boot then try to discover the assigned IP
        if use_dhcp:
            # Wait for FortiOS to boot, read ISO config, and get DHCP lease
            # CRITICAL: Must wait long enough for FortiOS to fully read the bootstrap ISO
            time.sleep(60)  # Increased from 30 to 60 seconds for reliable ISO read

            # Try to discover DHCP-assigned IP via MAC-to-ARP correlation
            wan_bridge = hv_config.get("wan_bridge", "br0")
            discovered_ip = discover_dhcp_ip(client, vm["vm_name"], bridge=wan_bridge, timeout=60)

            if discovered_ip:
                result["credentials"]["management_ip"] = discovered_ip
                result["phases"]["bootstrap_apply"]["status"] = "success"
                result["phases"]["bootstrap_apply"]["dhcp_ip"] = discovered_ip

                # Verify connectivity
                exit_code, _, _ = exec_command(client, f"ping -c 2 -W 2 {discovered_ip}")
                result["phases"]["bootstrap_apply"]["reachable"] = (exit_code == 0)
                if exit_code == 0:
                    iso_cleanup_ok = True  # Safe to delete ISO - FortiOS has applied config

                result["next_steps"] = [
                    f"VM booted with DHCP IP: {discovered_ip}",
                    f"VNC access: {hv_config['host']}:{vm['vnc_port']}",
                    f"Login: admin / {admin_password}",
                    "Run sdwan-blueprint-planner for full SD-WAN configuration"
                ]
            else:
                result["credentials"]["management_ip"] = "DHCP discovery pending - check manually"
                result["phases"]["bootstrap_apply"]["status"] = "pending"
                result["phases"]["bootstrap_apply"]["note"] = "DHCP IP not yet discovered - VM may still be booting"
                result["phases"]["bootstrap_apply"]["iso_path"] = bootstrap_iso  # For manual cleanup
                result["next_steps"] = [
                    "VM is booting with DHCP mode - IP not yet discovered",
                    f"VNC access: {hv_config['host']}:{vm['vnc_port']}",
                    f"Check ARP table: arp -an | grep {vm['interfaces'][0]['mac_address'] if vm.get('interfaces') else '52:54:00'}",
                    f"Login: admin / {admin_password}",
                    f"ISO left in place for boot: {bootstrap_iso} (cleanup after confirmed success)"
                ]
        else:
            # Static IP mode: Wait for boot, then test connectivity
            # CRITICAL: Increased to 60 seconds for reliable ISO read
            time.sleep(60)  # Give FortiOS time to boot and apply config
            ip_only = wan_ip.split('/')[0] if '/' in wan_ip else wan_ip
            exit_code, _, _ = exec_command(client, f"ping -c 2 -W 2 {ip_only}")
            if exit_code == 0:
                result["phases"]["bootstrap_apply"]["status"] = "success"
                result["phases"]["bootstrap_apply"]["reachable"] = True
                iso_cleanup_ok = True  # Safe to delete ISO - FortiOS has applied config
            else:
                result["phases"]["bootstrap_apply"]["status"] = "pending"
                result["phases"]["bootstrap_apply"]["reachable"] = False
                result["phases"]["bootstrap_apply"]["note"] = "Still booting - check VNC or wait 30 more seconds"
                result["phases"]["bootstrap_apply"]["iso_path"] = bootstrap_iso  # For manual cleanup

        # Cleanup bootstrap ISO only if confirmed success (device is reachable)
        # CRITICAL: DO NOT delete ISO while FortiOS may still be reading it
        if iso_cleanup_ok:
            exec_command(client, f"rm -f {bootstrap_iso}")
            result["phases"]["bootstrap_apply"]["iso_cleaned"] = True
        else:
            result["phases"]["bootstrap_apply"]["iso_cleaned"] = False
            result["phases"]["bootstrap_apply"]["iso_note"] = f"ISO preserved at {bootstrap_iso} - delete after manual verification"

        # Build network info
        result["network"] = {
            "name": network["name"],
            "bridge": network["bridge"],
            "subnet": network["subnet"],
            "gateway": network["gateway"]
        }

        # License info (FortiFlex token will be applied after boot via SSH)
        if fortiflex_token:
            result["license"] = {
                "type": "fortiflex",
                "token": fortiflex_token,
                "status": "pending_application",
                "note": "Apply via SSH after device is reachable: execute vm-license install <token>"
            }

        # Build next steps
        if not use_dhcp:
            ip_display = wan_ip.split('/')[0] if '/' in wan_ip else wan_ip
            result["next_steps"] = [
                "VM created with bootstrap config",
                f"VNC access: {hv_config['host']}:{vm['vnc_port']}",
                f"Expected management IP: {ip_display}",
                f"Login: admin / {admin_password}",
                "Run sdwan-blueprint-planner for full SD-WAN configuration"
            ]
            if fortiflex_token:
                result["next_steps"].insert(3, f"Apply license: execute vm-license install {fortiflex_token}")
        # DHCP next_steps already set above

        client.close()
        result["success"] = True

    except Exception as e:
        result["error"] = str(e)
        result["success"] = False

    return result


def action_status(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get status of a FortiGate VM."""
    site_name = params.get("site_name")
    hypervisor_id = params.get("hypervisor")

    if not site_name:
        return {"success": False, "error": "site_name is required"}

    vm_name = f"FortiGate-{site_name}"

    try:
        hv_id, hv_config = get_hypervisor(hypervisor_id)
        client = connect_ssh(hv_config)

        # Get VM state
        exit_code, stdout, stderr = exec_command(client, f"virsh domstate {vm_name}")
        if exit_code != 0:
            client.close()
            return {"success": False, "error": f"VM not found: {vm_name}"}

        vm_state = stdout.strip()

        # Get VNC port
        exit_code, stdout, stderr = exec_command(client, f"virsh vncdisplay {vm_name}")
        vnc_display = stdout.strip() if exit_code == 0 else "N/A"

        # Get interfaces
        interfaces = get_vm_interfaces(client, vm_name)

        client.close()

        return {
            "success": True,
            "vm_name": vm_name,
            "state": vm_state,
            "vnc_display": vnc_display,
            "interfaces": interfaces,
            "hypervisor": hv_config["host"]
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def action_start(params: Dict[str, Any]) -> Dict[str, Any]:
    """Start a stopped FortiGate VM.

    Primary use case: Restart VM after FortiFlex license application causes shutdown.
    Optionally discovers the DHCP-assigned management IP after boot.

    Parameters:
        site_name: Name of the site (e.g., "sdwan-spoke-08")
        hypervisor: Hypervisor name (default: auto-detect)
        wait_for_boot: Wait for FortiOS to boot and discover IP (default: True)
        boot_timeout: Seconds to wait for DHCP IP discovery (default: 120)
    """
    site_name = params.get("site_name")
    hypervisor_id = params.get("hypervisor")
    wait_for_boot = params.get("wait_for_boot", True)
    boot_timeout = params.get("boot_timeout", 120)

    if not site_name:
        return {"success": False, "error": "site_name is required"}

    vm_name = f"FortiGate-{site_name}"

    try:
        hv_id, hv_config = get_hypervisor(hypervisor_id)
        client = connect_ssh(hv_config)

        # Check current state first
        exit_code, stdout, stderr = exec_command(client, f"virsh domstate {vm_name}")
        if exit_code != 0:
            client.close()
            return {"success": False, "error": f"VM not found: {vm_name}"}

        current_state = stdout.strip()

        if current_state == "running":
            # Already running — return status with IP discovery
            management_ip = None
            if wait_for_boot:
                management_ip = discover_dhcp_ip(client, vm_name, timeout=30)
            interfaces = get_vm_interfaces(client, vm_name)
            client.close()
            return {
                "success": True,
                "vm_name": vm_name,
                "state": "running",
                "message": "VM is already running",
                "management_ip": management_ip,
                "interfaces": interfaces,
                "hypervisor": hv_config["host"]
            }

        # Start the VM
        exit_code, stdout, stderr = exec_command(client, f"virsh start {vm_name}")
        if exit_code != 0:
            client.close()
            return {
                "success": False,
                "error": f"Failed to start VM: {stderr.strip()}",
                "vm_name": vm_name,
                "previous_state": current_state
            }

        # Verify it's running
        time.sleep(3)
        exit_code, stdout, stderr = exec_command(client, f"virsh domstate {vm_name}")
        new_state = stdout.strip() if exit_code == 0 else "unknown"

        result = {
            "success": True,
            "vm_name": vm_name,
            "previous_state": current_state,
            "state": new_state,
            "message": f"VM {vm_name} started successfully",
            "hypervisor": hv_config["host"]
        }

        # Wait for boot and discover IP if requested
        if wait_for_boot and new_state == "running":
            management_ip = discover_dhcp_ip(client, vm_name, timeout=boot_timeout)
            result["management_ip"] = management_ip
            if management_ip:
                result["message"] += f" — management IP: {management_ip}"
            else:
                result["message"] += " — DHCP IP not yet discovered (VM may still be booting)"
                result["note"] = "Try action=status later to discover IP"

        # Get interface info
        interfaces = get_vm_interfaces(client, vm_name)
        result["interfaces"] = interfaces

        client.close()
        return result

    except Exception as e:
        return {"success": False, "error": str(e)}


def action_stop(params: Dict[str, Any]) -> Dict[str, Any]:
    """Gracefully stop a running FortiGate VM.

    Parameters:
        site_name: Name of the site (e.g., "sdwan-spoke-08")
        hypervisor: Hypervisor name (default: auto-detect)
        force: Use 'virsh destroy' (hard stop) instead of 'virsh shutdown' (default: False)
    """
    site_name = params.get("site_name")
    hypervisor_id = params.get("hypervisor")
    force = params.get("force", False)

    if not site_name:
        return {"success": False, "error": "site_name is required"}

    vm_name = f"FortiGate-{site_name}"

    try:
        hv_id, hv_config = get_hypervisor(hypervisor_id)
        client = connect_ssh(hv_config)

        # Check current state
        exit_code, stdout, stderr = exec_command(client, f"virsh domstate {vm_name}")
        if exit_code != 0:
            client.close()
            return {"success": False, "error": f"VM not found: {vm_name}"}

        current_state = stdout.strip()

        if current_state == "shut off":
            client.close()
            return {
                "success": True,
                "vm_name": vm_name,
                "state": "shut off",
                "message": "VM is already stopped"
            }

        # Stop the VM
        stop_cmd = f"virsh destroy {vm_name}" if force else f"virsh shutdown {vm_name}"
        exit_code, stdout, stderr = exec_command(client, stop_cmd)
        if exit_code != 0:
            client.close()
            return {
                "success": False,
                "error": f"Failed to stop VM: {stderr.strip()}",
                "vm_name": vm_name,
                "previous_state": current_state
            }

        # Wait for shutdown
        time.sleep(5)
        exit_code, stdout, stderr = exec_command(client, f"virsh domstate {vm_name}")
        new_state = stdout.strip() if exit_code == 0 else "unknown"

        client.close()
        return {
            "success": True,
            "vm_name": vm_name,
            "previous_state": current_state,
            "state": new_state,
            "method": "force" if force else "graceful",
            "message": f"VM {vm_name} stop initiated",
            "hypervisor": hv_config["host"]
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def action_destroy(params: Dict[str, Any]) -> Dict[str, Any]:
    """Destroy a FortiGate VM and optionally its resources."""
    site_name = params.get("site_name")
    remove_disk = params.get("remove_disk", True)
    remove_network = params.get("remove_network", False)
    subnet_id = params.get("subnet_id")
    hypervisor_id = params.get("hypervisor")

    if not site_name:
        return {"success": False, "error": "site_name is required"}

    vm_name = f"FortiGate-{site_name}"

    try:
        hv_id, hv_config = get_hypervisor(hypervisor_id)
        client = connect_ssh(hv_config)

        result = {
            "success": True,
            "vm_name": vm_name,
            "actions": []
        }

        # Stop VM if running
        exec_command(client, f"virsh destroy {vm_name} 2>/dev/null")
        result["actions"].append("VM stopped")

        # Undefine VM
        exit_code, stdout, stderr = exec_command(client, f"virsh undefine {vm_name}")
        if exit_code == 0:
            result["actions"].append("VM undefined")

        # Remove disk if requested
        if remove_disk:
            vm_image_path = hv_config.get("vm_image_path", "/home/libvirt/images/")
            disk_path = f"{vm_image_path}fortigate-{site_name}.qcow2"
            exec_command(client, f"rm -f {disk_path}")
            result["actions"].append(f"Disk removed: {disk_path}")

        # Remove network if requested
        if remove_network and subnet_id:
            net_name = f"VM-Net-{subnet_id}"
            exec_command(client, f"virsh net-destroy {net_name} 2>/dev/null")
            exec_command(client, f"virsh net-undefine {net_name} 2>/dev/null")
            result["actions"].append(f"Network removed: {net_name}")

        client.close()
        return result

    except Exception as e:
        return {"success": False, "error": str(e)}


def action_list(params: Dict[str, Any]) -> Dict[str, Any]:
    """List FortiGate VMs on the hypervisor."""
    hypervisor_id = params.get("hypervisor")

    try:
        hv_id, hv_config = get_hypervisor(hypervisor_id)
        client = connect_ssh(hv_config)

        # List all VMs starting with FortiGate-
        exit_code, stdout, stderr = exec_command(
            client, "virsh list --all | grep FortiGate- | awk '{print $2, $3}'"
        )

        vms = []
        for line in stdout.strip().split('\n'):
            if line:
                parts = line.split()
                if len(parts) >= 1:
                    vm_name = parts[0]
                    state = parts[1] if len(parts) > 1 else "unknown"
                    vms.append({"name": vm_name, "state": state})

        client.close()

        return {
            "success": True,
            "hypervisor": hv_config["host"],
            "vms": vms,
            "count": len(vms)
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main(context) -> Dict[str, Any]:
    """Main entry point for the tool."""
    # Handle both ExecutionContext (MCP) and dict (CLI)
    if hasattr(context, 'parameters'):
        params = context.parameters
    else:
        params = context

    action = params.get("action", "provision")

    try:
        if action == "provision":
            return action_provision(params)
        elif action == "start":
            return action_start(params)
        elif action == "stop":
            return action_stop(params)
        elif action == "status":
            return action_status(params)
        elif action == "destroy":
            return action_destroy(params)
        elif action == "list":
            return action_list(params)
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "valid_actions": ["provision", "start", "stop", "status", "destroy", "list"]
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


if __name__ == "__main__":
    if len(sys.argv) > 1:
        params = {"action": sys.argv[1]}
        for arg in sys.argv[2:]:
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
        result = main({"action": "list"})

    print(json.dumps(result, indent=2))
