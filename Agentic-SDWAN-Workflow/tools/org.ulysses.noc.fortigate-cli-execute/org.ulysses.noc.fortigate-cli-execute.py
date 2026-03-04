"""
FortiGate CLI Execute - SSH Write Command Tool

Execute CLI commands on FortiGate via SSH with password authentication.
Supports write commands (config, execute) for initial device setup.

Use cases:
- Apply FortiFlex license (execute vm-license)
- Configure interfaces before API user exists
- Set admin password on first login
- Any CLI command not supported by REST API

WARNING: This tool executes write commands. Use with caution.
"""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import paramiko
import yaml


def load_credentials(target_ip: str) -> Optional[Dict[str, str]]:
    """Load credentials from local config file."""
    creds_paths = [
        Path.home() / ".config" / "mcp" / "fortigate_credentials.yaml",
        Path("config") / "fortigate_credentials.yaml",
        Path("C:/ProgramData/Ulysses/config/fortigate_credentials.yaml"),
    ]

    for creds_path in creds_paths:
        if creds_path.exists():
            try:
                with open(creds_path, "r") as f:
                    data = yaml.safe_load(f)

                # Check default_lookup for IP -> device mapping
                default_lookup = data.get("default_lookup", {})
                device_id = default_lookup.get(target_ip)

                if device_id:
                    device = data.get("devices", {}).get(device_id, {})
                    if device:
                        return {
                            "username": device.get("ssh_username", device.get("username", "admin")),
                            "password": device.get("ssh_password", device.get("password", "")),
                        }

                # Direct device lookup by IP
                for dev_id, dev_data in data.get("devices", {}).items():
                    if dev_data.get("host") == target_ip:
                        return {
                            "username": dev_data.get("ssh_username", dev_data.get("username", "admin")),
                            "password": dev_data.get("ssh_password", dev_data.get("password", "")),
                        }
            except Exception:
                continue

    return None


def execute_commands_shell(
    client: paramiko.SSHClient,
    commands: List[str],
    timeout: int,
    interactive_responses: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """Execute commands using interactive shell (for config blocks)."""
    results = []
    channel = client.invoke_shell()
    time.sleep(1)

    # Clear initial banner
    if channel.recv_ready():
        channel.recv(65535)

    for cmd in commands:
        try:
            # Send command
            channel.send(cmd + "\n")
            time.sleep(0.5)

            # Collect output
            output = ""
            start_time = time.time()

            while time.time() - start_time < timeout:
                if channel.recv_ready():
                    chunk = channel.recv(65535).decode("utf-8", errors="replace")
                    output += chunk

                    # Check for interactive prompts
                    if interactive_responses:
                        for prompt, response in interactive_responses.items():
                            if prompt in chunk:
                                channel.send(response + "\n")
                                time.sleep(0.5)
                                break

                    # Check for command completion (prompt returned)
                    if output.rstrip().endswith("#") or output.rstrip().endswith("$"):
                        break
                else:
                    time.sleep(0.1)

            results.append({
                "command": cmd,
                "output": output.strip(),
                "success": True,
            })

        except Exception as e:
            results.append({
                "command": cmd,
                "output": str(e),
                "success": False,
            })

    channel.close()
    return results


def execute_commands_exec(
    client: paramiko.SSHClient,
    commands: List[str],
    timeout: int,
) -> List[Dict[str, Any]]:
    """Execute commands using exec_command (for single commands)."""
    results = []

    for cmd in commands:
        try:
            stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
            output = stdout.read().decode("utf-8", errors="replace")
            error = stderr.read().decode("utf-8", errors="replace")

            results.append({
                "command": cmd,
                "output": output.strip() if output else error.strip(),
                "success": True,
            })

        except Exception as e:
            results.append({
                "command": cmd,
                "output": str(e),
                "success": False,
            })

    return results


def main(context) -> Dict[str, Any]:
    """
    Execute CLI commands on FortiGate via SSH.

    Args:
        context: ExecutionContext with parameters

    Returns:
        Dict with command results
    """
    params = getattr(context, "parameters", {})

    # Required parameters
    target_ip = params.get("target_ip")
    commands = params.get("commands", [])

    if not target_ip:
        return {"success": False, "error": "target_ip is required"}

    if not commands:
        return {"success": False, "error": "commands list is required"}

    # Optional parameters
    username = params.get("username", "admin")
    password = params.get("password")
    ssh_port = params.get("ssh_port", 22)
    timeout = params.get("timeout", 30)
    use_shell = params.get("use_shell", True)
    interactive_responses = params.get("interactive_responses", {})

    # Try to load credentials if password not provided
    if not password:
        creds = load_credentials(target_ip)
        if creds:
            username = creds.get("username", username)
            password = creds.get("password", "")

    if password is None:
        password = ""

    # Connect via SSH
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=target_ip,
            port=ssh_port,
            username=username,
            password=password,
            timeout=timeout,
            allow_agent=False,
            look_for_keys=False,
        )

        # Execute commands
        if use_shell:
            results = execute_commands_shell(
                client, commands, timeout, interactive_responses
            )
        else:
            results = execute_commands_exec(client, commands, timeout)

        # Check overall success
        all_success = all(r.get("success", False) for r in results)

        return {
            "success": all_success,
            "target_ip": target_ip,
            "commands_executed": len(results),
            "results": results,
        }

    except paramiko.AuthenticationException:
        return {
            "success": False,
            "target_ip": target_ip,
            "error": f"Authentication failed for {username}@{target_ip}",
        }

    except paramiko.SSHException as e:
        return {
            "success": False,
            "target_ip": target_ip,
            "error": f"SSH error: {str(e)}",
        }

    except Exception as e:
        return {
            "success": False,
            "target_ip": target_ip,
            "error": f"Connection error: {str(e)}",
        }

    finally:
        client.close()
