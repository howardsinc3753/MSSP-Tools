#!/usr/bin/env python3
from __future__ import annotations
"""
FortiGate Onboard Tool

Complete onboarding workflow for new FortiGate devices:
1. SSH into device with admin credentials
2. Create REST API admin user via CLI
3. Generate API key
4. Test API connectivity
5. Register device in local credentials file

This tool handles the full provisioning workflow including:
- FortiOS password prompts during admin creation
- Trusthost configuration for API access
- Bearer token authentication (required for FortiOS 7.6+)
"""

import os
import re
import time
import json
import ssl
import gzip
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Optional

try:
    import paramiko
except ImportError:
    paramiko = None

try:
    import yaml
except ImportError:
    yaml = None


def ssh_connect(host: str, username: str, password: str,
                port: int = 22, timeout: int = 30) -> paramiko.SSHClient:
    """Establish SSH connection to FortiGate."""
    if not paramiko:
        raise ImportError("paramiko is required: pip install paramiko")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=host,
        port=port,
        username=username,
        password=password,
        timeout=timeout,
        look_for_keys=False,
        allow_agent=False
    )
    return client


def enable_api_settings_via_ssh(shell) -> bool:
    """Enable REST API key URL query in system global settings."""

    def send_cmd(cmd, wait=0.5):
        shell.send(cmd + "\n")
        time.sleep(wait)
        output = ""
        for _ in range(10):
            if shell.recv_ready():
                output += shell.recv(4096).decode()
            time.sleep(0.1)
        return output

    # Clear any existing config state
    send_cmd("end")
    send_cmd("end")

    # Enable rest-api-key-url-query in system global
    send_cmd("config system global")
    send_cmd("set rest-api-key-url-query enable")
    send_cmd("end")

    return True


def create_api_user_via_ssh(
    shell,
    api_username: str,
    admin_password: str,
    accprofile: str = "super_admin",
    trusthosts: list = None,
    comments: str = "Created by Project Ulysses"
) -> bool:
    """Create REST API admin user via SSH CLI commands."""

    if trusthosts is None:
        # Default trusthosts - allow common private ranges
        trusthosts = [
            ("192.168.0.0", "255.255.0.0"),
            ("10.0.0.0", "255.0.0.0"),
            ("172.16.0.0", "255.240.0.0")
        ]

    def send_cmd(cmd, wait=0.5):
        shell.send(cmd + "\n")
        time.sleep(wait)
        output = ""
        for _ in range(10):
            if shell.recv_ready():
                output += shell.recv(4096).decode()
            time.sleep(0.1)
        return output

    # Clear any existing config state
    send_cmd("end")
    send_cmd("end")

    # Delete existing user if present (ignore errors)
    send_cmd("config system api-user")
    send_cmd(f"delete {api_username}")
    send_cmd("end")

    # Create new API user
    send_cmd("config system api-user")
    send_cmd(f"edit {api_username}")
    send_cmd(f'set comments "{comments}"')
    send_cmd(f"set accprofile {accprofile}")

    # Configure trusthosts
    send_cmd("config trusthost")
    for i, (ip, mask) in enumerate(trusthosts, 1):
        send_cmd(f"edit {i}")
        send_cmd(f"set ipv4-trusthost {ip} {mask}")
        send_cmd("next")
    send_cmd("end")  # end trusthost

    # Save api-user entry - this prompts for password
    shell.send("next\n")
    time.sleep(1)

    output = ""
    for _ in range(20):
        if shell.recv_ready():
            output += shell.recv(4096).decode()
        time.sleep(0.2)

    if "password" in output.lower():
        shell.send(admin_password + "\n")
        time.sleep(2)
        for _ in range(10):
            if shell.recv_ready():
                shell.recv(4096)
            time.sleep(0.1)

    # End api-user config
    send_cmd("end")

    return True


def generate_api_key_via_ssh(shell, api_username: str, admin_password: str) -> Optional[str]:
    """Generate API key for the user via CLI command."""

    shell.send(f"execute api-user generate-key {api_username}\n")
    time.sleep(2)

    output = ""
    for _ in range(20):
        if shell.recv_ready():
            output += shell.recv(4096).decode()
        time.sleep(0.2)

    if "password" in output.lower():
        shell.send(admin_password + "\n")
        time.sleep(3)

        output = ""
        for _ in range(30):
            if shell.recv_ready():
                output += shell.recv(4096).decode()
            time.sleep(0.2)

    # Extract API key from output
    match = re.search(r'New API key:\s*(\S+)', output)
    if match:
        return match.group(1)

    return None


def test_api_key(host: str, api_token: str, verify_ssl: bool = False,
                 timeout: int = 30) -> dict:
    """Test API key using Bearer authentication."""
    url = f"https://{host}/api/v2/monitor/system/status"

    ctx = ssl.create_default_context()
    if not verify_ssl:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {api_token}")

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
            data = response.read()
            if data[:2] == b'\x1f\x8b':
                data = gzip.decompress(data)
            return json.loads(data.decode())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


def register_device(device_id: str, host: str, api_token: str,
                    verify_ssl: bool = False, model: str = None,
                    firmware: str = None) -> dict:
    """Register device in local credentials file."""
    if not yaml:
        raise ImportError("PyYAML is required: pip install pyyaml")

    # Find credentials file
    config_paths = [
        Path("config/fortigate_credentials.yaml"),
    ]
    try:
        config_paths.insert(0, Path(__file__).parent.parent.parent / "config" / "fortigate_credentials.yaml")
    except NameError:
        pass

    cred_path = None
    for path in config_paths:
        if path.exists():
            cred_path = path
            break

    if not cred_path:
        cred_path = config_paths[0]

    # Load or create config
    if cred_path.exists():
        with open(cred_path) as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {}

    if "devices" not in config:
        config["devices"] = {}
    if "default_lookup" not in config:
        config["default_lookup"] = {}

    # Add device entry
    device_entry = {
        "host": host,
        "api_token": api_token,
        "verify_ssl": verify_ssl,
        "_metadata": {
            "model": model,
            "firmware": firmware,
            "registered_at": datetime.now(timezone.utc).isoformat()
        }
    }

    config["devices"][device_id] = device_entry
    config["default_lookup"][host] = device_id

    # Save config
    cred_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cred_path, 'w') as f:
        f.write("# FortiGate Credentials - DO NOT COMMIT\n")
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    return {"success": True, "credentials_file": str(cred_path)}


def main(context) -> dict[str, Any]:
    """
    FortiGate Onboard - Complete device onboarding workflow.

    This tool performs full onboarding of a new FortiGate device:
    1. Connects via SSH using admin credentials
    2. Creates a REST API admin user
    3. Generates an API key
    4. Tests API connectivity
    5. Registers the device in local credentials

    Args:
        context: ExecutionContext containing:
            - parameters:
                - target_ip: FortiGate management IP
                - admin_user: Admin username (default: admin)
                - admin_password: Admin password
                - device_id: Unique device identifier (e.g., "lab-vm02")
                - api_username: Name for API admin (default: ulysses-api)
                - accprofile: Admin profile (default: super_admin)
                - trusthosts: List of allowed source networks (optional)
                - ssh_port: SSH port (default: 22)
                - timeout: Operation timeout (default: 60)
                - verify_ssl: Verify SSL certs (default: false)

    Returns:
        dict: Onboarding result including:
            - success: Whether onboarding completed
            - device_id: Registered device ID
            - api_token: Generated API token
            - device_info: Basic device information
            - error: Error message if failed
    """
    # Support both context formats
    if hasattr(context, "parameters"):
        args = context.parameters
    else:
        args = context

    target_ip = args.get("target_ip")
    admin_user = args.get("admin_user", "admin")
    admin_password = args.get("admin_password")
    device_id = args.get("device_id")
    api_username = args.get("api_username", "ulysses-api")
    accprofile = args.get("accprofile", "super_admin")
    trusthosts = args.get("trusthosts")
    ssh_port = args.get("ssh_port", 22)
    timeout = args.get("timeout", 60)
    verify_ssl = args.get("verify_ssl", False)

    # Validate required parameters
    if not target_ip:
        return {"success": False, "error": "target_ip is required"}
    if not admin_password:
        return {"success": False, "error": "admin_password is required"}
    if not device_id:
        return {"success": False, "error": "device_id is required (e.g., 'lab-vm02')"}

    result = {
        "success": False,
        "target_ip": target_ip,
        "device_id": device_id,
        "steps_completed": []
    }

    client = None
    try:
        # Step 1: SSH Connect
        client = ssh_connect(target_ip, admin_user, admin_password, ssh_port, timeout)
        result["steps_completed"].append("ssh_connect")

        shell = client.invoke_shell()
        time.sleep(1)
        shell.recv(4096)  # Clear initial prompt

        # Step 2: Enable API settings (rest-api-key-url-query)
        enable_api_settings_via_ssh(shell)
        result["steps_completed"].append("enable_api_settings")

        # Step 3: Create API user
        create_api_user_via_ssh(
            shell, api_username, admin_password, accprofile, trusthosts
        )
        result["steps_completed"].append("create_api_user")

        # Step 3: Generate API key
        api_token = generate_api_key_via_ssh(shell, api_username, admin_password)
        if not api_token:
            result["error"] = "Failed to generate API key"
            return result
        result["steps_completed"].append("generate_api_key")
        result["api_token"] = api_token

        # Step 4: Test API connectivity
        api_result = test_api_key(target_ip, api_token, verify_ssl, timeout)
        if "error" in api_result:
            result["error"] = f"API test failed: {api_result['error']}"
            result["api_token"] = api_token  # Still return token for debugging
            return result
        result["steps_completed"].append("test_api")

        # Extract device info
        device_info = {
            "hostname": api_result.get("results", {}).get("hostname"),
            "serial": api_result.get("serial"),
            "version": api_result.get("version"),
            "model": api_result.get("results", {}).get("model_name")
        }
        result["device_info"] = device_info

        # Step 5: Register device
        reg_result = register_device(
            device_id, target_ip, api_token, verify_ssl,
            model=device_info.get("model"),
            firmware=device_info.get("version")
        )
        result["steps_completed"].append("register_device")
        result["credentials_file"] = reg_result.get("credentials_file")

        result["success"] = True
        result["message"] = f"Device '{device_id}' onboarded successfully"

    except paramiko.AuthenticationException:
        result["error"] = f"SSH authentication failed for {admin_user}@{target_ip}"
    except Exception as e:
        result["error"] = f"Onboarding failed: {str(e)}"
    finally:
        if client:
            client.close()

    return result


if __name__ == "__main__":
    import getpass

    target = input("FortiGate IP: ")
    device = input("Device ID (e.g., lab-vm02): ")
    user = input("Admin username [admin]: ") or "admin"
    password = getpass.getpass("Admin password: ")

    result = main({
        "target_ip": target,
        "device_id": device,
        "admin_user": user,
        "admin_password": password
    })

    print(json.dumps(result, indent=2))
