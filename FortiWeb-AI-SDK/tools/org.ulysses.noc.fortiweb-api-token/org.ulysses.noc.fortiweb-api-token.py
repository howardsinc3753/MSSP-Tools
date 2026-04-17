#!/usr/bin/env python3
from __future__ import annotations
"""
FortiWeb API Token Manager

Lists and manages admin accounts on FortiWeb 8.0+ via REST API.
Can be used to verify API connectivity and inspect admin configuration.

FortiWeb 8.0 REST API Auth Model:
  - Base64-encode a JSON object: {"username":"...","password":"...","vdom":"..."}
  - Pass the result in the Authorization header on every request
  - No session/login endpoint needed — each request is independently authenticated
  - Base path for CMDB config: /api/v2.0/cmdb
  - Base path for Monitor: /api/v2.0/

Author: Ulysses Project
Version: 1.1.0
"""

import urllib.request
import urllib.error
import ssl
import json
import base64
import os
from pathlib import Path
from typing import Any, Optional


def load_credentials(target_ip: str) -> Optional[dict]:
    """Load admin credentials from local config file.

    MCP credential search order (uses FIRST match):
    1. ~/.config/mcp/ (PRIMARY)
    2. ~/AppData/Local/mcp/ (Windows secondary)
    3. C:/ProgramData/mcp/ or /etc/mcp/ (System-wide)
    4. C:/ProgramData/Ulysses/config/ (Ulysses platform)
    """
    config_paths = [
        Path.home() / ".config" / "mcp" / "fortiweb_credentials.yaml",
    ]

    if os.name == 'nt':
        config_paths.append(Path.home() / "AppData" / "Local" / "mcp" / "fortiweb_credentials.yaml")
        config_paths.append(Path("C:/ProgramData/mcp/fortiweb_credentials.yaml"))
        config_paths.append(Path("C:/ProgramData/Ulysses/config/fortiweb_credentials.yaml"))
    else:
        config_paths.append(Path("/etc/mcp/fortiweb_credentials.yaml"))

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


def build_auth_token(username: str, password: str, vdom: str = "root") -> str:
    """Build FortiWeb Base64 authorization token.

    FortiWeb REST API auth: Base64-encode a JSON object containing
    username, password, and vdom. Pass result in Authorization header.

    Example:
        {"username":"admin","password":"pass","vdom":"root"}
        -> base64 encode -> "eyJ1c2Vybm..."
        -> Header: Authorization: eyJ1c2Vybm...
    """
    auth_obj = json.dumps({
        "username": username,
        "password": password,
        "vdom": vdom,
    })
    return base64.b64encode(auth_obj.encode()).decode()


def make_api_request(host: str, endpoint: str, auth_token: str,
                     method: str = "GET", data: Optional[dict] = None,
                     verify_ssl: bool = False, timeout: int = 30) -> dict:
    """Make a request to FortiWeb REST API.

    Args:
        host: FortiWeb IP address
        endpoint: API endpoint path (e.g., /api/v2.0/cmdb/system/admin)
        auth_token: Base64-encoded authorization token
        method: HTTP method (GET, POST, PUT, DELETE)
        data: Request body for POST/PUT
        verify_ssl: Whether to verify SSL certificate
        timeout: Request timeout in seconds

    Returns:
        Parsed JSON response
    """
    url = f"https://{host}{endpoint}"

    if not verify_ssl:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    else:
        ctx = ssl.create_default_context()

    payload = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=payload, method=method)
    req.add_header("Accept", "application/json")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", auth_token)

    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
        raw = response.read().decode()
        if raw:
            return json.loads(raw)
        return {}


def list_admins(host: str, auth_token: str, verify_ssl: bool = False,
                timeout: int = 30) -> dict:
    """List all admin accounts.

    Endpoint: GET /api/v2.0/cmdb/system/admin
    """
    return make_api_request(
        host, "/api/v2.0/cmdb/system/admin",
        auth_token, "GET", verify_ssl=verify_ssl, timeout=timeout
    )


def get_admin(host: str, auth_token: str, admin_name: str,
              verify_ssl: bool = False, timeout: int = 30) -> dict:
    """Get a specific admin account by name.

    Endpoint: GET /api/v2.0/cmdb/system/admin?mkey=<name>
    """
    return make_api_request(
        host, f"/api/v2.0/cmdb/system/admin?mkey={admin_name}",
        auth_token, "GET", verify_ssl=verify_ssl, timeout=timeout
    )


def create_admin(host: str, auth_token: str, admin_name: str,
                 password: str, accprofile: str = "prof_admin",
                 verify_ssl: bool = False, timeout: int = 30) -> dict:
    """Create a new admin account.

    Endpoint: POST /api/v2.0/cmdb/system/admin
    """
    payload = {
        "data": {
            "name": admin_name,
            "password": password,
            "access-profile": accprofile,
        }
    }
    return make_api_request(
        host, "/api/v2.0/cmdb/system/admin",
        auth_token, "POST", data=payload,
        verify_ssl=verify_ssl, timeout=timeout
    )


def delete_admin(host: str, auth_token: str, admin_name: str,
                 verify_ssl: bool = False, timeout: int = 30) -> dict:
    """Delete an admin account.

    Endpoint: DELETE /api/v2.0/cmdb/system/admin?mkey=<name>
    """
    return make_api_request(
        host, f"/api/v2.0/cmdb/system/admin?mkey={admin_name}",
        auth_token, "DELETE", verify_ssl=verify_ssl, timeout=timeout
    )


def test_auth(host: str, auth_token: str, verify_ssl: bool = False,
              timeout: int = 30) -> dict:
    """Test API authentication by fetching system status.

    Uses a lightweight read-only call to verify credentials work.
    """
    return make_api_request(
        host, "/api/v2.0/cmdb/system/admin",
        auth_token, "GET", verify_ssl=verify_ssl, timeout=timeout
    )


def main(context) -> dict[str, Any]:
    """
    FortiWeb API Token Manager - manage admin accounts and test API auth.

    Supports actions: list, get, create, delete, test

    Auth model: Base64({"username":"...","password":"...","vdom":"..."})
    passed in Authorization header on every request.

    Args:
        context: ExecutionContext or dict with parameters

    Returns:
        dict: Operation result
    """
    if hasattr(context, "parameters"):
        args = context.parameters
        creds = getattr(context, "credentials", None)
    else:
        args = context
        creds = None

    target_ip = args.get("target_ip")
    action = args.get("action", "test")
    admin_name = args.get("admin_name")
    new_password = args.get("new_password")
    vdom = args.get("vdom", "root")
    accprofile = args.get("accprofile", "prof_admin")
    timeout = args.get("timeout", 30)
    verify_ssl = args.get("verify_ssl", False)

    if not target_ip:
        return {"error": "target_ip is required", "success": False}

    # Get admin credentials for auth
    username = None
    password = None

    if creds:
        username = creds.get("username")
        password = creds.get("password")
        if creds.get("verify_ssl") is not None:
            verify_ssl = creds["verify_ssl"]

    if not username:
        local_creds = load_credentials(target_ip)
        if local_creds:
            username = local_creds.get("username")
            password = local_creds.get("password")
            if local_creds.get("verify_ssl") is not None:
                verify_ssl = local_creds["verify_ssl"]

    if not username or not password:
        return {
            "error": f"No admin credentials found for {target_ip}. "
                     f"Configure in ~/.config/mcp/fortiweb_credentials.yaml",
            "success": False,
        }

    # Build Base64 auth token
    auth_token = build_auth_token(username, password, vdom)

    try:
        if action == "test":
            result = test_auth(target_ip, auth_token, verify_ssl, timeout)
            return {
                "success": True,
                "target_ip": target_ip,
                "action": "test",
                "message": "Authentication successful — API access verified",
                "auth_method": "Base64 header (stateless)",
                "vdom": vdom,
            }

        elif action == "list":
            result = list_admins(target_ip, auth_token, verify_ssl, timeout)
            admins = result.get("results", result.get("data", []))
            if isinstance(admins, dict):
                admins = [admins]
            return {
                "success": True,
                "target_ip": target_ip,
                "action": "list",
                "admin_count": len(admins),
                "admins": admins,
            }

        elif action == "get":
            if not admin_name:
                return {"error": "admin_name required for get action", "success": False}
            result = get_admin(target_ip, auth_token, admin_name, verify_ssl, timeout)
            return {
                "success": True,
                "target_ip": target_ip,
                "action": "get",
                "admin": result.get("results", result.get("data", {})),
            }

        elif action == "create":
            if not admin_name:
                return {"error": "admin_name required for create action", "success": False}
            if not new_password:
                return {"error": "new_password required for create action", "success": False}
            result = create_admin(target_ip, auth_token, admin_name,
                                  new_password, accprofile, verify_ssl, timeout)
            return {
                "success": True,
                "target_ip": target_ip,
                "action": "create",
                "admin_name": admin_name,
                "accprofile": accprofile,
                "message": f"Admin '{admin_name}' created. Use build_auth_token() "
                           f"with the new credentials to authenticate API calls.",
            }

        elif action == "delete":
            if not admin_name:
                return {"error": "admin_name required for delete action", "success": False}
            delete_admin(target_ip, auth_token, admin_name, verify_ssl, timeout)
            return {
                "success": True,
                "target_ip": target_ip,
                "action": "delete",
                "admin_name": admin_name,
                "message": f"Admin '{admin_name}' deleted.",
            }

        else:
            return {"success": False, "error": f"Unknown action: {action}. Use: test, list, get, create, delete"}

    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode()
        except Exception:
            pass
        return {
            "success": False,
            "error": f"HTTP {e.code}: {e.reason}. {error_body}",
            "target_ip": target_ip,
        }
    except urllib.error.URLError as e:
        return {
            "success": False,
            "error": f"Connection failed: {e.reason}",
            "target_ip": target_ip,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "target_ip": target_ip,
        }


if __name__ == "__main__":
    # Test: verify API auth against lab FortiWeb
    result = main({
        "target_ip": "192.168.209.31",
        "action": "test",
    })
    print(json.dumps(result, indent=2))
