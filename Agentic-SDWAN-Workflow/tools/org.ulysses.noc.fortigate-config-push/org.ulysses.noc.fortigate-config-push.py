#!/usr/bin/env python3
"""
FortiGate Config Push Tool v2.0

Pushes FortiOS CLI configuration to a FortiGate device via SSH.
Sends CLI commands directly - no API translation required.

This is the correct approach for pushing complex configs like SD-WAN.

Workflow:
1. Generate complete CLI config (flat format from atomic template)
2. SSH into device
3. Push CLI commands section by section
4. Verify each section completes without errors

GAP-26 FIX: Previous version tried CLI->API translation which failed for:
- system settings (no API mapping)
- Nested SD-WAN configs
- Multi-interface firewall policies

This version pushes CLI directly via SSH - works for ALL config types.
"""

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple
from datetime import datetime

# Credentials path - canonical production location (GAP-15 fix)
CREDS_PATH = Path("C:/ProgramData/Ulysses/config/fortigate_credentials.yaml")


def load_credentials() -> dict:
    """Load FortiGate credentials from config file."""
    import yaml
    if not CREDS_PATH.exists():
        raise FileNotFoundError(f"Credentials file not found: {CREDS_PATH}")
    with open(CREDS_PATH) as f:
        return yaml.safe_load(f)


def get_device_creds(host: str, creds: dict) -> Dict[str, Any]:
    """Get SSH credentials for a device."""
    devices = creds.get("devices", {})

    # Try default_lookup table (IP -> device name)
    default_lookup = creds.get("default_lookup", {})
    device_name = default_lookup.get(host)

    if device_name and device_name in devices:
        dev = devices[device_name]
        return {
            "host": dev.get("host", host),
            "username": dev.get("ssh_username", "admin"),
            "password": dev.get("ssh_password", ""),
            "api_token": dev.get("api_token", ""),
            "verify_ssl": dev.get("verify_ssl", False)
        }

    # Try exact key match (device name or IP)
    if host in devices:
        dev = devices[host]
        return {
            "host": dev.get("host", host),
            "username": dev.get("ssh_username", "admin"),
            "password": dev.get("ssh_password", ""),
            "api_token": dev.get("api_token", ""),
            "verify_ssl": dev.get("verify_ssl", False)
        }

    # Try searching by host field
    for name, dev in devices.items():
        if dev.get("host") == host:
            return {
                "host": dev.get("host", host),
                "username": dev.get("ssh_username", "admin"),
                "password": dev.get("ssh_password", ""),
                "api_token": dev.get("api_token", ""),
                "verify_ssl": dev.get("verify_ssl", False)
            }

    return {"host": host, "username": "admin", "password": "", "api_token": "", "verify_ssl": False}


def split_config_sections(config_text: str) -> List[Dict[str, str]]:
    """
    Split CLI config into sections for sequential push.

    Each section is a complete 'config ... end' block that can be
    pushed independently.
    """
    sections = []
    current_section = []
    section_name = None
    depth = 0

    lines = config_text.strip().split('\n')

    for line in lines:
        stripped = line.strip()

        # Skip comments and empty lines at top level
        if depth == 0 and (not stripped or stripped.startswith('#')):
            continue

        # Track config depth
        if stripped.startswith('config '):
            if depth == 0:
                section_name = stripped[7:].strip()
                current_section = [line]
            else:
                current_section.append(line)
            depth += 1
        elif stripped == 'end':
            current_section.append(line)
            depth -= 1
            if depth == 0:
                sections.append({
                    "name": section_name,
                    "commands": '\n'.join(current_section)
                })
                current_section = []
                section_name = None
        else:
            if depth > 0:
                current_section.append(line)

    return sections


def push_via_ssh(host: str, username: str, password: str,
                 config_text: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Push CLI config via SSH.

    Uses paramiko to SSH into device and send commands.
    """
    try:
        import paramiko
    except ImportError:
        return {
            "success": False,
            "error": "paramiko not installed. Run: pip install paramiko"
        }

    results = []
    sections = split_config_sections(config_text)

    if not sections:
        return {"success": False, "error": "No config sections found"}

    try:
        # Connect via SSH
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=host,
            username=username,
            password=password,
            timeout=timeout,
            look_for_keys=False,
            allow_agent=False
        )

        # Open shell channel for interactive session
        shell = client.invoke_shell()
        time.sleep(1)

        # Clear initial banner
        if shell.recv_ready():
            shell.recv(65535)

        success_count = 0
        fail_count = 0

        for section in sections:
            section_name = section["name"]
            commands = section["commands"]

            # Send section commands
            shell.send(commands + '\n')
            time.sleep(0.5)

            # Wait for prompt (indicates command completed)
            output = ""
            wait_time = 0
            while wait_time < timeout:
                if shell.recv_ready():
                    chunk = shell.recv(65535).decode('utf-8', errors='replace')
                    output += chunk
                    # Check for prompt (hostname followed by # or $)
                    if re.search(r'\S+\s*[#$]\s*$', output):
                        break
                time.sleep(0.2)
                wait_time += 0.2

            # Check for errors in output
            error_patterns = [
                r'Command fail',
                r'object set operator error',
                r'entry not found',
                r'invalid',
                r'Unknown action',
                r'parse error'
            ]

            has_error = any(re.search(pattern, output, re.IGNORECASE) for pattern in error_patterns)

            if has_error:
                fail_count += 1
                results.append({
                    "section": section_name,
                    "success": False,
                    "output": output[-500:] if len(output) > 500 else output
                })
            else:
                success_count += 1
                results.append({
                    "section": section_name,
                    "success": True,
                    "output": "OK"
                })

        client.close()

        return {
            "success": fail_count == 0,
            "target": host,
            "method": "SSH_CLI",
            "sections_total": len(sections),
            "sections_success": success_count,
            "sections_failed": fail_count,
            "results": results,
            "pushed_at": datetime.now().isoformat()
        }

    except paramiko.AuthenticationException:
        return {"success": False, "error": f"SSH authentication failed for {username}@{host}"}
    except paramiko.SSHException as e:
        return {"success": False, "error": f"SSH error: {e}"}
    except Exception as e:
        return {"success": False, "error": f"Connection error: {e}"}


def push_config(host: str, config_text: str = None, config_path: str = None,
                dry_run: bool = False) -> dict:
    """
    Push FortiOS CLI configuration to a device via SSH.

    Args:
        host: Target FortiGate IP/hostname
        config_text: CLI config as string
        config_path: Path to CLI config file
        dry_run: Parse only, don't push

    Returns:
        dict with success status and details
    """
    # Load config
    if config_path:
        with open(config_path, 'r') as f:
            config_text = f.read()
    elif not config_text:
        return {"success": False, "error": "No config provided"}

    # Parse sections for preview
    sections = split_config_sections(config_text)

    if dry_run:
        return {
            "success": True,
            "mode": "dry_run",
            "target": host,
            "sections_parsed": len(sections),
            "sections": [{"name": s["name"], "lines": len(s["commands"].split('\n'))} for s in sections]
        }

    # Load credentials
    try:
        creds = load_credentials()
        device_creds = get_device_creds(host, creds)

        if not device_creds.get("password"):
            return {"success": False, "error": f"No SSH password for {host}. Add ssh_password to credentials."}
    except Exception as e:
        return {"success": False, "error": f"Credentials error: {e}"}

    # Push via SSH
    return push_via_ssh(
        host=device_creds["host"],
        username=device_creds["username"],
        password=device_creds["password"],
        config_text=config_text
    )


def main(context) -> dict[str, Any]:
    """
    FortiGate Config Push v2.0 - Push CLI config via SSH.

    Args:
        context: ExecutionContext with parameters:
            Required:
            - target_ip: FortiGate management IP

            One of:
            - config_path: Path to CLI config file
            - config_text: CLI config as string

            Optional:
            - dry_run: Parse only, don't push (default: false)

    Returns:
        dict: Push results with success/failure details
    """
    if hasattr(context, "parameters"):
        args = context.parameters
    else:
        args = context

    target_ip = args.get("target_ip")
    if not target_ip:
        return {"success": False, "error": "target_ip is required"}

    config_path = args.get("config_path")
    config_text = args.get("config_text")
    dry_run = args.get("dry_run", False)

    if not config_path and not config_text:
        return {"success": False, "error": "config_path or config_text required"}

    # Load config for parsing
    if config_path:
        try:
            with open(config_path, 'r') as f:
                config_text = f.read()
        except Exception as e:
            return {"success": False, "error": f"Failed to read config: {e}"}

    return push_config(target_ip, config_text=config_text, dry_run=dry_run)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python tool.py <target_ip> <config_file> [--dry-run]")
        sys.exit(1)

    target_ip = sys.argv[1]
    config_file = sys.argv[2]
    dry_run = "--dry-run" in sys.argv

    result = main({
        "target_ip": target_ip,
        "config_path": config_file,
        "dry_run": dry_run
    })

    print(json.dumps(result, indent=2))
