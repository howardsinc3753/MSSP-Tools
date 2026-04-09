"""
FortiBot NOC - SSH CLI Tool
Execute CLI commands on FortiGate devices via SSH using paramiko.
"""
import re
import time
import socket
import paramiko


# Commands that are always blocked (safety guardrails)
BLOCKED_COMMANDS = [
    r"^execute\s+factoryreset\b",
    r"^execute\s+formatlogdisk\b",
    r"^execute\s+shutdown\b",
    r"^execute\s+reboot\b",
    r"^execute\s+restore\s+image\b",
    r"^execute\s+batch\b",
    r"^execute\s+script\b",
    r"^execute\s+ha\s+manage\b",
    r"^config\s+system\s+admin\b",
    r"^config\s+firewall\b",
    r"^config\s+router\b",
    r"^config\s+vpn\b",
    r"^config\s+system\s+interface\b",
    r"^config\s+system\s+global\b",
    r"^set\s+password\b",
    r"^diagnose\s+sys\s+kill\b",
    r"^diagnose\s+debug\s+reset\b",
]


def _is_blocked(command: str) -> bool:
    cmd = command.strip().lower()
    return any(re.match(p, cmd) for p in BLOCKED_COMMANDS)


def _has_prompt(text: str) -> bool:
    """Check if text ends with a FortiGate CLI prompt."""
    stripped = text.rstrip()
    if stripped.endswith(" #") or stripped.endswith(" $"):
        return True
    if stripped.endswith(") #") or stripped.endswith(") $"):
        return True
    lines = stripped.split("\n")
    if lines:
        last = lines[-1].strip()
        if re.search(r"[a-zA-Z0-9_-]+\s*(\([^)]+\))?\s*[#$]\s*$", last):
            return True
    return False


def run_ssh_command(device: dict, command: str, timeout: int = 30) -> dict:
    """Execute a single CLI command on a FortiGate device via SSH.

    Args:
        device: Device dict with ip, ssh_port, ssh_user, ssh_pass.
        command: CLI command to execute.
        timeout: Timeout in seconds (default 30).

    Returns:
        dict with 'success', 'output', and optionally 'error'.
    """
    if _is_blocked(command):
        return {"success": False, "error": f"Command blocked for safety: {command}"}

    if not device.get("ssh_user"):
        return {"success": False, "error": "SSH credentials not configured for this device."}

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            device["ip"],
            port=device.get("ssh_port", 22),
            username=device["ssh_user"],
            password=device.get("ssh_pass"),
            timeout=15,
            allow_agent=False,
            look_for_keys=False,
        )

        # Use interactive shell for FortiGate compatibility
        shell = client.invoke_shell(width=200, height=50)
        shell.settimeout(timeout)

        # Wait for initial prompt
        output = ""
        start = time.time()
        while time.time() - start < 10:
            if shell.recv_ready():
                output += shell.recv(4096).decode("utf-8", errors="replace")
                if _has_prompt(output):
                    break
            else:
                time.sleep(0.1)

        # Disable CLI pagination so long output doesn't hang on --More--
        shell.send("config system console\n")
        time.sleep(0.3)
        shell.send("set output standard\n")
        time.sleep(0.3)
        shell.send("end\n")
        time.sleep(0.5)
        # Drain the pagination config output
        while shell.recv_ready():
            shell.recv(4096)

        # Send command
        shell.send(command + "\n")
        time.sleep(0.2)

        # Read response
        cmd_output = ""
        start = time.time()
        while time.time() - start < timeout:
            if shell.recv_ready():
                chunk = shell.recv(4096).decode("utf-8", errors="replace")
                cmd_output += chunk
                if _has_prompt(cmd_output):
                    break
            else:
                time.sleep(0.1)

        shell.close()
        client.close()

        # Strip the echoed command and trailing prompt
        lines = cmd_output.split("\n")
        # Remove first line (echoed command) and last line (prompt)
        if len(lines) >= 2:
            clean_output = "\n".join(lines[1:-1])
        else:
            clean_output = cmd_output

        return {"success": True, "command": command, "output": clean_output}

    except paramiko.AuthenticationException:
        return {"success": False, "error": f"SSH authentication failed for {device.get('ssh_user')}@{device['ip']}"}
    except socket.timeout:
        return {"success": False, "error": f"SSH timeout to {device['ip']}:{device.get('ssh_port', 22)}"}
    except Exception as e:
        return {"success": False, "error": f"SSH error: {str(e)}"}
    finally:
        try:
            client.close()
        except Exception:
            pass
