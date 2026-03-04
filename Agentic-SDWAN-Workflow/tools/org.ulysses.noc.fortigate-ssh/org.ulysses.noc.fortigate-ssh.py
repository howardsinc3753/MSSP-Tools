#!/usr/bin/env python3
from __future__ import annotations
"""
FortiGate SSH Tool

Execute CLI commands on FortiGate via SSH with public key authentication.
Features:
- RSA-4096 key generation and management
- Auto-provisioning of tron-cli admin user via REST API
- Command allowlist for security
- Key storage at ~/.config/mcp/keys/
"""

import json
import os
import re
import socket
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional

# Try to import paramiko (SSH library)
try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False
    paramiko = None

# Try to import cryptography for key generation
try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


# Command allowlist - broad patterns for read-only commands
# Allows any show, get, diagnose, or execute (read-only) command
COMMAND_ALLOWLIST = [
    # All 'get' commands (read-only by design)
    r"^get\s+.+",

    # All 'show' commands (read-only by design)
    r"^show\s+.+",

    # All 'diagnose' commands (read-only diagnostics)
    r"^diagnose\s+.+",

    # Read-only execute commands
    r"^execute\s+ping\s+.+",
    r"^execute\s+ping-options\s+.+",
    r"^execute\s+traceroute\s+.+",
    r"^execute\s+telnet\s+.+",
    r"^execute\s+ssh\s+.+",
]

# Explicitly blocked dangerous commands (safety net)
COMMAND_BLOCKLIST = [
    r"^config\s+",           # No config changes
    r"^execute\s+shutdown",   # No shutdown
    r"^execute\s+reboot",     # No reboot
    r"^execute\s+format",     # No format
    r"^execute\s+restore",    # No restore
    r"^execute\s+backup",     # No backup (could leak config)
    r"^diagnose\s+debug\s+enable",  # No debug enable (performance impact)
]

# SSH CLI username for MCP tools
SSH_USERNAME = "tron-cli"
KEY_BITS = 4096


class SSHKeyManager:
    """Manages RSA keypair for SSH authentication."""

    def __init__(self, key_dir: Optional[Path] = None):
        """Initialize key manager.

        Args:
            key_dir: Directory for key storage. Defaults to ~/.config/mcp/keys/
        """
        if key_dir is None:
            key_dir = Path.home() / ".config" / "mcp" / "keys"
        self.key_dir = Path(key_dir)
        self.private_key_path = self.key_dir / "tron_cli_rsa"
        self.public_key_path = self.key_dir / "tron_cli_rsa.pub"

    def ensure_key_directory(self) -> None:
        """Create key directory with secure permissions."""
        self.key_dir.mkdir(parents=True, exist_ok=True)
        if os.name != 'nt':  # Unix permissions
            os.chmod(self.key_dir, 0o700)

    def keypair_exists(self) -> bool:
        """Check if keypair already exists."""
        return self.private_key_path.exists() and self.public_key_path.exists()

    def generate_keypair(self) -> tuple[str, str]:
        """Generate RSA-4096 keypair.

        Returns:
            Tuple of (private_key_pem, public_key_openssh)
        """
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("cryptography library not installed. Run: pip install cryptography")

        self.ensure_key_directory()

        # Generate RSA key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=KEY_BITS,
            backend=default_backend()
        )

        # Serialize private key (PEM format, no encryption)
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.OpenSSH,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')

        # Serialize public key (OpenSSH format)
        public_openssh = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.OpenSSH,
            format=serialization.PublicFormat.OpenSSH
        ).decode('utf-8')

        # Add comment to public key
        public_openssh = f"{public_openssh} tron-cli@mcp"

        # Save keys
        with open(self.private_key_path, 'w') as f:
            f.write(private_pem)
        if os.name != 'nt':
            os.chmod(self.private_key_path, 0o600)

        with open(self.public_key_path, 'w') as f:
            f.write(public_openssh)

        return private_pem, public_openssh

    def load_keypair(self) -> tuple[str, str]:
        """Load existing keypair from disk.

        Returns:
            Tuple of (private_key_pem, public_key_openssh)
        """
        if not self.keypair_exists():
            raise FileNotFoundError(f"Keypair not found at {self.key_dir}")

        with open(self.private_key_path, 'r') as f:
            private_pem = f.read()

        with open(self.public_key_path, 'r') as f:
            public_openssh = f.read().strip()

        return private_pem, public_openssh

    def get_or_create_keypair(self) -> tuple[str, str]:
        """Get existing keypair or create new one.

        Returns:
            Tuple of (private_key_pem, public_key_openssh)
        """
        if self.keypair_exists():
            return self.load_keypair()
        return self.generate_keypair()

    def get_private_key_for_paramiko(self):
        """Get paramiko RSAKey object for SSH connection."""
        if not PARAMIKO_AVAILABLE:
            raise RuntimeError("paramiko library not installed. Run: pip install paramiko")

        private_pem, _ = self.get_or_create_keypair()

        # Load into paramiko
        import io
        key_file = io.StringIO(private_pem)
        return paramiko.RSAKey.from_private_key(key_file)


def load_api_credentials(target_ip: str) -> Optional[dict]:
    """Load API credentials for REST API provisioning.

    This uses the same credential file as other FortiGate tools.
    """
    config_paths = [
        Path.home() / ".config" / "mcp" / "fortigate_credentials.yaml",
    ]

    if os.name == 'nt':
        config_paths.append(Path.home() / "AppData" / "Local" / "mcp" / "fortigate_credentials.yaml")
        config_paths.append(Path("C:/ProgramData/mcp/fortigate_credentials.yaml"))
        config_paths.append(Path("C:/ProgramData/Ulysses/config/fortigate_credentials.yaml"))
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


def make_api_request(host: str, endpoint: str, api_token: str,
                     method: str = "GET", data: Optional[dict] = None,
                     verify_ssl: bool = False, timeout: int = 30) -> dict:
    """Make a request to FortiGate REST API."""
    url = f"https://{host}{endpoint}?access_token={api_token}"

    if not verify_ssl:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    else:
        ctx = ssl.create_default_context()

    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")

    body = None
    if data:
        body = json.dumps(data).encode('utf-8')

    with urllib.request.urlopen(req, data=body, timeout=timeout, context=ctx) as response:
        return json.loads(response.read().decode())


def get_available_accprofiles(target_ip: str, api_token: str,
                              verify_ssl: bool = False) -> list[str]:
    """Get list of available admin access profiles.

    Returns:
        List of profile names, with preferred profiles first
    """
    try:
        result = make_api_request(
            target_ip, "/api/v2/cmdb/system/accprofile",
            api_token, verify_ssl=verify_ssl
        )
        profiles = [p.get("name") for p in result.get("results", [])]

        # Prioritize profiles with admin/full access
        preferred = ["prof_admin", "super_admin", "API_ADMIN_FULL"]
        sorted_profiles = []
        for pref in preferred:
            if pref in profiles:
                sorted_profiles.append(pref)
        for p in profiles:
            if p not in sorted_profiles:
                sorted_profiles.append(p)

        return sorted_profiles
    except Exception:
        return ["prof_admin"]  # Default fallback


def check_user_exists(target_ip: str, api_token: str, username: str,
                      verify_ssl: bool = False) -> bool:
    """Check if admin user exists on FortiGate."""
    try:
        result = make_api_request(
            target_ip,
            f"/api/v2/cmdb/system/admin/{username}",
            api_token,
            verify_ssl=verify_ssl
        )
        return result.get("http_status") == 200 or "results" in result
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise


def provision_ssh_user(target_ip: str, api_token: str, username: str,
                       public_key: str, trusthost_network: str = "0.0.0.0 0.0.0.0",
                       accprofile: str = "prof_admin",
                       verify_ssl: bool = False) -> dict:
    """Create or update tron-cli admin user with SSH public key.

    Args:
        target_ip: FortiGate IP address
        api_token: REST API token
        username: Admin username to create
        public_key: SSH public key (OpenSSH format)
        trusthost_network: Allowed network in "IP NETMASK" format
        accprofile: Admin access profile name (default: prof_admin)
        verify_ssl: Whether to verify SSL certificate

    Returns:
        API response dict
    """
    # Extract just the key part (remove 'ssh-rsa' prefix and comment)
    key_parts = public_key.strip().split()
    if len(key_parts) >= 2:
        # FortiGate wants just: "ssh-rsa AAAA...key..."
        ssh_key_value = f"{key_parts[0]} {key_parts[1]}"
    else:
        ssh_key_value = public_key.strip()

    # Parse trusthost (format: "IP NETMASK")
    trusthost_parts = trusthost_network.split()
    if len(trusthost_parts) == 2:
        trusthost_ip = trusthost_parts[0]
        trusthost_mask = trusthost_parts[1]
    else:
        trusthost_ip = "0.0.0.0"
        trusthost_mask = "0.0.0.0"

    user_config = {
        "name": username,
        "accprofile": accprofile,  # Use discovered or specified profile
        "trusthost1": f"{trusthost_ip} {trusthost_mask}",
        "ssh-public-key1": ssh_key_value,  # Format: "ssh-rsa AAAA...key..."
        "comments": "MCP tron-cli SSH access - auto-provisioned"
    }

    # Check if user exists
    user_exists = check_user_exists(target_ip, api_token, username, verify_ssl)

    if user_exists:
        # Update existing user
        endpoint = f"/api/v2/cmdb/system/admin/{username}"
        method = "PUT"
    else:
        # Create new user
        endpoint = "/api/v2/cmdb/system/admin"
        method = "POST"

    return make_api_request(
        target_ip, endpoint, api_token,
        method=method, data=user_config,
        verify_ssl=verify_ssl
    )


def is_command_allowed(command: str) -> bool:
    """Check if command is allowed (allowlist) and not blocked (blocklist).

    Args:
        command: CLI command to validate

    Returns:
        True if command matches an allowlist pattern and not in blocklist
    """
    command = command.strip()

    # Check blocklist first (safety)
    for pattern in COMMAND_BLOCKLIST:
        if re.match(pattern, command, re.IGNORECASE):
            return False

    # Check allowlist
    for pattern in COMMAND_ALLOWLIST:
        if re.match(pattern, command, re.IGNORECASE):
            return True

    return False


def execute_ssh_command(target_ip: str, username: str, private_key,
                        command: str, port: int = 22,
                        timeout: int = 30) -> tuple[str, str, int]:
    """Execute command via SSH.

    Args:
        target_ip: FortiGate IP address
        username: SSH username
        private_key: paramiko RSAKey object
        command: CLI command to execute
        port: SSH port (default 22)
        timeout: Connection timeout

    Returns:
        Tuple of (stdout, stderr, exit_status)
    """
    if not PARAMIKO_AVAILABLE:
        raise RuntimeError("paramiko library not installed. Run: pip install paramiko")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=target_ip,
            port=port,
            username=username,
            pkey=private_key,
            timeout=timeout,
            allow_agent=False,
            look_for_keys=False
        )

        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        exit_status = stdout.channel.recv_exit_status()

        return stdout.read().decode('utf-8'), stderr.read().decode('utf-8'), exit_status

    finally:
        client.close()


def main(context) -> dict[str, Any]:
    """
    FortiGate SSH - Execute CLI commands via SSH with public key auth.

    This tool:
    1. Generates RSA-4096 keypair if not exists (~/.config/mcp/keys/)
    2. Auto-provisions tron-cli user on FortiGate if needed (via REST API)
    3. Executes the command via SSH
    4. Returns command output

    Args:
        context: ExecutionContext containing:
            - parameters.target_ip: FortiGate management IP
            - parameters.command: CLI command to execute
            - parameters.provision_user: Whether to auto-provision user (default: true)
            - parameters.trusthost: Allowed source network (default: 0.0.0.0 0.0.0.0)

    Returns:
        dict: Command output and execution status
    """
    # Check dependencies
    if not PARAMIKO_AVAILABLE:
        return {
            "success": False,
            "error": "paramiko library not installed. Run: pip install paramiko",
            "dependency_missing": "paramiko"
        }

    if not CRYPTO_AVAILABLE:
        return {
            "success": False,
            "error": "cryptography library not installed. Run: pip install cryptography",
            "dependency_missing": "cryptography"
        }

    # Parse context
    if hasattr(context, "parameters"):
        args = context.parameters
    else:
        args = context

    target_ip = args.get("target_ip")
    command = args.get("command", "")
    provision_user = args.get("provision_user", True)
    trusthost = args.get("trusthost", "0.0.0.0 0.0.0.0")
    ssh_port = args.get("ssh_port", 22)
    timeout = args.get("timeout", 30)
    verify_ssl = args.get("verify_ssl", False)

    if not target_ip:
        return {
            "success": False,
            "error": "target_ip is required"
        }

    if not command:
        return {
            "success": False,
            "error": "command is required"
        }

    # Validate command against allowlist
    if not is_command_allowed(command):
        return {
            "success": False,
            "error": f"Command not allowed: {command}",
            "hint": "Only read-only diagnostic commands are permitted. See Skills.md for allowed commands.",
            "command_blocked": True
        }

    # Initialize key manager
    key_manager = SSHKeyManager()

    try:
        # Get or create keypair
        private_pem, public_key = key_manager.get_or_create_keypair()
        key_created = not key_manager.keypair_exists()

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to manage SSH keys: {str(e)}",
            "key_path": str(key_manager.key_dir)
        }

    # Provision user if requested
    user_provisioned = False
    api_permission_error = False
    creds = load_api_credentials(target_ip)

    if provision_user:
        if not creds:
            # No credentials - try SSH anyway (user may have been created manually)
            api_permission_error = True
        elif not creds.get("api_token"):
            # No API token - try SSH anyway
            api_permission_error = True
        else:
            api_token = creds.get("api_token")
            try:
                # Check if user already exists
                user_exists = check_user_exists(target_ip, api_token, SSH_USERNAME, verify_ssl)

                if not user_exists:
                    # Discover available access profiles
                    profiles = get_available_accprofiles(target_ip, api_token, verify_ssl)
                    accprofile = profiles[0] if profiles else "prof_admin"

                    provision_result = provision_ssh_user(
                        target_ip, api_token, SSH_USERNAME,
                        public_key, trusthost, accprofile, verify_ssl
                    )
                    user_provisioned = True

            except urllib.error.HTTPError as e:
                if e.code in (401, 403):
                    # API token lacks permission to check/create admin users
                    # This is common for read-only tokens - try SSH anyway
                    # The user may have been created manually
                    api_permission_error = True
                else:
                    return {
                        "success": False,
                        "error": f"Failed to provision user: HTTP {e.code} - {e.reason}",
                        "target_ip": target_ip
                    }
            except Exception as e:
                # Other API errors - try SSH anyway
                api_permission_error = True

    # Execute SSH command
    try:
        private_key = key_manager.get_private_key_for_paramiko()

        stdout, stderr, exit_status = execute_ssh_command(
            target_ip, SSH_USERNAME, private_key,
            command, port=ssh_port, timeout=timeout
        )

        result = {
            "success": exit_status == 0,
            "target_ip": target_ip,
            "command": command,
            "output": stdout.strip(),
            "stderr": stderr.strip() if stderr.strip() else None,
            "exit_status": exit_status,
            "ssh_user": SSH_USERNAME,
            "user_provisioned": user_provisioned,
            "key_path": str(key_manager.private_key_path)
        }
        if api_permission_error:
            result["api_permission_skipped"] = True
            result["hint"] = "API check skipped (401/403). SSH auth succeeded using manually-provisioned user."
        return result

    except paramiko.AuthenticationException:
        return {
            "success": False,
            "error": "SSH authentication failed. The tron-cli user may not have the correct public key.",
            "target_ip": target_ip,
            "hint": "Try with provision_user=true to update the SSH key on FortiGate"
        }
    except paramiko.SSHException as e:
        return {
            "success": False,
            "error": f"SSH error: {str(e)}",
            "target_ip": target_ip
        }
    except socket.timeout:
        return {
            "success": False,
            "error": f"SSH connection timeout after {timeout}s",
            "target_ip": target_ip
        }
    except socket.error as e:
        return {
            "success": False,
            "error": f"Network error: {str(e)}",
            "target_ip": target_ip
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "target_ip": target_ip
        }


if __name__ == "__main__":
    # Test execution
    result = main({
        "target_ip": "10.0.0.62",
        "command": "get system status"
    })
    print(json.dumps(result, indent=2))
