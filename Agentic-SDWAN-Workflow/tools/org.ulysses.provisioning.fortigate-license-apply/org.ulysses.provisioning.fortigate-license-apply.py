#!/usr/bin/env python3
"""
FortiGate License Apply Tool

Apply FortiFlex license token to a FortiGate VM via SSH.
SSHs to the FortiGate and executes `execute vm-license install <token>`.

CRITICAL: After license application, FortiGate VM SHUTS DOWN (does NOT reboot!)
This tool handles that by:
1. Applying the license via SSH
2. Waiting for VM to shut down
3. SSHing to hypervisor and running 'virsh start'
4. Waiting for FortiGate SSH to come back
5. Verifying license status

Author: Trust-Bot Tool Maker
Version: 1.0.5
Created: 2026-01-25
Updated: 2026-01-25 - v1.0.5: Fixed command (no 'install' keyword), improved success detection
"""

import json
import logging
import os
import re
import socket
import time
from typing import Any, Dict, Optional

import paramiko
import yaml

logger = logging.getLogger(__name__)

# Default credentials
DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PASSWORD = "FG@dm!n2026!"

# Hypervisor defaults
DEFAULT_HYPERVISOR_HOST = "10.0.0.100"
DEFAULT_HYPERVISOR_USER = "root"
HYPERVISOR_CRED_PATH = os.path.expanduser("~/.config/mcp/hypervisor_credentials.yaml")


def load_hypervisor_credentials() -> Dict[str, Any]:
    """Load hypervisor credentials from config file."""
    try:
        if os.path.exists(HYPERVISOR_CRED_PATH):
            with open(HYPERVISOR_CRED_PATH, 'r') as f:
                config = yaml.safe_load(f)
            default_name = config.get('default_hypervisor', 'rocky-kvm-lab')
            return config.get('hypervisors', {}).get(default_name, {})
    except Exception as e:
        logger.warning(f"Could not load hypervisor credentials: {e}")
    return {}


def validate_token(token: str) -> bool:
    """Validate FortiFlex token format (20-char hex)."""
    if not token:
        return False
    # FortiFlex tokens are typically 20 uppercase hex characters
    return bool(re.match(r'^[A-F0-9]{20}$', token.upper()))


def validate_ip(ip: str) -> bool:
    """Validate IP address format."""
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False


def wait_for_ssh(ip: str, port: int = 22, timeout: int = 180) -> bool:
    """Wait for SSH to become available after reboot."""
    logger.info(f"Waiting for SSH on {ip}:{port} (timeout: {timeout}s)")
    start = time.time()

    while time.time() - start < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((ip, port))
            sock.close()

            if result == 0:
                logger.info(f"SSH is available on {ip}")
                # Give it a moment to fully initialize
                time.sleep(5)
                return True
        except Exception:
            pass

        time.sleep(5)

    return False


def wait_for_ssh_down(ip: str, port: int = 22, timeout: int = 60) -> bool:
    """Wait for SSH to go DOWN (VM shutting down)."""
    logger.info(f"Waiting for SSH on {ip}:{port} to go DOWN (timeout: {timeout}s)")
    start = time.time()

    while time.time() - start < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((ip, port))
            sock.close()

            if result != 0:
                logger.info(f"SSH is DOWN on {ip} - VM has shut down")
                return True
        except Exception:
            # Connection failed = SSH is down
            logger.info(f"SSH connection failed on {ip} - VM has shut down")
            return True

        time.sleep(2)

    return False


def start_vm_via_hypervisor(vm_name: str, hypervisor_host: str = None,
                            hypervisor_user: str = None, hypervisor_password: str = None) -> Dict[str, Any]:
    """SSH to hypervisor and start VM with virsh."""
    # Load credentials if not provided
    if not hypervisor_host or not hypervisor_password:
        creds = load_hypervisor_credentials()
        hypervisor_host = hypervisor_host or creds.get('host', DEFAULT_HYPERVISOR_HOST)
        hypervisor_user = hypervisor_user or creds.get('username', DEFAULT_HYPERVISOR_USER)
        hypervisor_password = hypervisor_password or creds.get('password')

    if not hypervisor_password:
        return {"success": False, "error": "No hypervisor password available"}

    logger.info(f"Connecting to hypervisor {hypervisor_host} to start VM {vm_name}")

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hypervisor_host,
            port=22,
            username=hypervisor_user,
            password=hypervisor_password,
            timeout=30,
            look_for_keys=False,
            allow_agent=False
        )

        # Check VM state first
        stdin, stdout, stderr = client.exec_command(f"virsh domstate {vm_name}")
        state = stdout.read().decode().strip()
        logger.info(f"VM {vm_name} state: {state}")

        if state == "running":
            client.close()
            return {"success": True, "message": f"VM {vm_name} is already running", "state": state}

        # Start the VM
        logger.info(f"Starting VM {vm_name} with virsh start")
        stdin, stdout, stderr = client.exec_command(f"virsh start {vm_name}")
        start_output = stdout.read().decode()
        start_error = stderr.read().decode()

        if "started" in start_output.lower() or "Domain" in start_output:
            client.close()
            return {"success": True, "message": f"VM {vm_name} started successfully", "output": start_output}
        elif start_error:
            client.close()
            return {"success": False, "error": f"virsh start failed: {start_error}"}
        else:
            client.close()
            return {"success": True, "message": start_output or "VM start command executed", "output": start_output}

    except paramiko.AuthenticationException as e:
        logger.error(f"Hypervisor authentication failed: {e}")
        return {"success": False, "error": f"Hypervisor auth failed: {e}"}
    except Exception as e:
        logger.exception(f"Error starting VM via hypervisor: {e}")
        return {"success": False, "error": str(e)}


def ssh_connect(ip: str, username: str, password: str, timeout: int = 30) -> paramiko.SSHClient:
    """Create SSH connection to FortiGate."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    logger.info(f"Connecting to {ip} as {username}")
    client.connect(
        ip,
        port=22,
        username=username,
        password=password,
        timeout=timeout,
        look_for_keys=False,
        allow_agent=False
    )

    return client


def apply_license(client: paramiko.SSHClient, token: str) -> Dict[str, Any]:
    """
    Apply FortiFlex license via SSH using expect-like pattern.

    Returns dict with:
    - output: Raw command output
    - success: Whether command executed
    - reboot_triggered: Whether reboot was triggered
    """
    # Use transport channel with PTY for proper interactive behavior
    transport = client.get_transport()
    channel = transport.open_session()
    channel.get_pty(term='vt100', width=200, height=50)
    channel.invoke_shell()

    time.sleep(2)

    # Clear initial banner/prompt
    while channel.recv_ready():
        channel.recv(4096)

    output = ""

    # Send the license command (no "install" keyword!)
    command = f"execute vm-license {token}"
    logger.info(f"Sending command: {command}")
    channel.send(command + "\n")

    # Wait for (y/n) prompt with timeout
    logger.info("Waiting for confirmation prompt...")
    start_time = time.time()
    while time.time() - start_time < 15:
        if channel.recv_ready():
            chunk = channel.recv(4096).decode('utf-8', errors='ignore')
            output += chunk
            logger.info(f"Received: {repr(chunk)}")

            # Check for the confirmation prompt
            if "(y/n)" in output:
                logger.info("Found (y/n) prompt, sending 'y'")
                time.sleep(0.3)
                channel.send("y")
                break
        time.sleep(0.3)

    # Wait for license validation (Fortinet server contact takes time)
    logger.info("Waiting for license download and validation...")
    time.sleep(45)

    # Collect remaining output
    end_time = time.time() + 10
    while time.time() < end_time:
        if channel.recv_ready():
            chunk = channel.recv(4096).decode('utf-8', errors='ignore')
            output += chunk
            logger.info(f"Received: {repr(chunk)}")
        time.sleep(0.5)

    channel.close()

    logger.info(f"Complete output: {output}")

    # Determine success/failure
    output_lower = output.lower()

    # Error indicators - if ANY of these appear, it failed
    error_indicators = [
        'failed to download',
        'curl forticare failed',
        'invalid license',
        'license error',
        'network unreachable',
        'command fail'
    ]
    has_error = any(ind in output_lower for ind in error_indicators)

    # Success indicators - note: successful license often just returns to prompt
    # The VM will shut down (not reboot) after successful license
    success_indicators = [
        'your license has been downloaded',
        'license installed',
        'rebooting'
    ]
    has_explicit_success = any(ind in output_lower for ind in success_indicators)

    # If we got y/n prompt and no error, consider it a success
    # (VM will shut down after successful license application)
    got_confirmation = '(y/n)' in output and 'y' in output
    has_success = has_explicit_success or (got_confirmation and not has_error)

    # Reboot/shutdown will be triggered if successful
    reboot_triggered = has_success

    return {
        "output": output,
        "success": has_success,
        "reboot_triggered": reboot_triggered,
        "error": output if has_error else None
    }


def get_license_status(client: paramiko.SSHClient) -> Dict[str, Any]:
    """Get current license status from FortiGate."""
    shell = client.invoke_shell()
    time.sleep(2)

    # Clear buffer
    while shell.recv_ready():
        shell.recv(4096)

    # Get system status
    shell.send("get system status\n")
    time.sleep(3)

    output = ""
    while shell.recv_ready():
        output += shell.recv(4096).decode('utf-8', errors='ignore')

    # Parse license info
    license_status = "Unknown"
    serial_number = "Unknown"

    for line in output.split('\n'):
        line = line.strip()
        if 'License Status' in line:
            license_status = line.split(':')[-1].strip()
        elif 'Serial-Number' in line:
            serial_number = line.split(':')[-1].strip()

    return {
        "license_status": license_status,
        "serial_number": serial_number,
        "raw_output": output
    }


def execute(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the tool."""
    logger.info("Executing FortiGate License Apply v1.0.4")

    # Extract parameters
    target_ip = params.get("target_ip")
    admin_user = params.get("admin_user", DEFAULT_ADMIN_USER)
    admin_password = params.get("admin_password", DEFAULT_ADMIN_PASSWORD)
    fortiflex_token = params.get("fortiflex_token")
    wait_for_reboot = params.get("wait_for_reboot", True)
    reboot_timeout = params.get("reboot_timeout", 180)
    vm_name = params.get("vm_name")  # Optional - for hypervisor start
    hypervisor_host = params.get("hypervisor_host")
    hypervisor_user = params.get("hypervisor_user")
    hypervisor_password = params.get("hypervisor_password")

    # Validate inputs
    if not target_ip:
        return {"success": False, "error": "Missing required parameter: target_ip"}

    if not validate_ip(target_ip):
        return {"success": False, "error": f"Invalid IP address: {target_ip}"}

    if not fortiflex_token:
        return {"success": False, "error": "Missing required parameter: fortiflex_token"}

    if not validate_token(fortiflex_token):
        return {"success": False, "error": f"Invalid token format: {fortiflex_token} (expected 20-char hex)"}

    try:
        # Connect to FortiGate
        client = ssh_connect(target_ip, admin_user, admin_password)

        # Apply license
        license_result = apply_license(client, fortiflex_token)

        # Close connection - VM will shut down (NOT reboot!)
        client.close()

        if not license_result["success"]:
            return {
                "success": False,
                "error": license_result.get("error", "License application failed"),
                "license_output": license_result["output"]
            }

        # CRITICAL: FortiGate VM SHUTS DOWN after license (does NOT reboot!)
        # We must start it via hypervisor
        vm_started = False
        if license_result["reboot_triggered"] and wait_for_reboot:
            logger.info("License applied - VM will SHUT DOWN (not reboot)")
            logger.info("Waiting for VM to shut down...")

            # Wait for SSH to go down (VM shutting down)
            if wait_for_ssh_down(target_ip, timeout=60):
                logger.info("VM has shut down, waiting 5 seconds before starting...")
                time.sleep(5)

                # Start VM via hypervisor if vm_name provided
                if vm_name:
                    logger.info(f"Starting VM {vm_name} via hypervisor...")
                    start_result = start_vm_via_hypervisor(
                        vm_name, hypervisor_host, hypervisor_user, hypervisor_password
                    )

                    if start_result["success"]:
                        logger.info(f"VM start result: {start_result['message']}")
                        vm_started = True
                    else:
                        return {
                            "success": False,
                            "error": f"Failed to start VM via hypervisor: {start_result['error']}",
                            "license_output": license_result["output"],
                            "note": "License was applied but VM could not be started. Use: virsh start <vm_name>"
                        }
                else:
                    # No vm_name provided - return instructions
                    return {
                        "success": True,
                        "license_applied": True,
                        "vm_shutdown": True,
                        "license_output": license_result["output"],
                        "note": "License applied. VM has SHUT DOWN (not rebooted). Start manually: virsh start <vm_name>"
                    }

            # Wait for FortiGate SSH to come back up
            if vm_started:
                logger.info(f"Waiting for FortiGate SSH on {target_ip}...")
                if wait_for_ssh(target_ip, timeout=reboot_timeout):
                    logger.info("FortiGate is back online")
                else:
                    return {
                        "success": False,
                        "error": f"Timeout waiting for FortiGate SSH (>{reboot_timeout}s)",
                        "license_output": license_result["output"],
                        "note": "VM was started but SSH not available. Check VM status."
                    }

        # Get final license status
        if vm_started or not license_result["reboot_triggered"]:
            time.sleep(5)  # Brief pause for services to stabilize
            try:
                client = ssh_connect(target_ip, admin_user, admin_password)
                status = get_license_status(client)
                client.close()
            except Exception as e:
                logger.warning(f"Could not get license status: {e}")
                status = {"license_status": "Applied (verify manually)", "serial_number": "Unknown"}
        else:
            status = {"license_status": "Pending VM start", "serial_number": "Unknown"}

        return {
            "success": True,
            "license_status": status["license_status"],
            "serial_number": status["serial_number"],
            "license_output": license_result["output"],
            "vm_started": vm_started,
            "note": "License applied and VM started successfully" if vm_started else "License applied"
        }

    except paramiko.AuthenticationException as e:
        logger.error(f"SSH authentication failed: {e}")
        return {
            "success": False,
            "error": f"SSH authentication failed. Check admin_user/admin_password. Error: {e}"
        }
    except paramiko.SSHException as e:
        logger.error(f"SSH error: {e}")
        return {"success": False, "error": f"SSH error: {e}"}
    except socket.timeout as e:
        logger.error(f"Connection timeout: {e}")
        return {"success": False, "error": f"Connection timeout: {e}"}
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return {"success": False, "error": str(e)}


def main(context) -> Dict[str, Any]:
    """Entry point for MCP execution."""
    if hasattr(context, "parameters"):
        params = context.parameters
    elif isinstance(context, dict):
        params = context
    else:
        params = {}

    return execute(params)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 3:
        print("Usage: python tool.py <target_ip> <fortiflex_token> [admin_password]")
        sys.exit(1)

    test_params = {
        "target_ip": sys.argv[1],
        "fortiflex_token": sys.argv[2]
    }
    if len(sys.argv) > 3:
        test_params["admin_password"] = sys.argv[3]

    result = main(test_params)
    print(json.dumps(result, indent=2))
