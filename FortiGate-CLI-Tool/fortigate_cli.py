#!/usr/bin/env python3
"""
FortiGate CLI Tool — Execute CLI commands via FortiOS REST API
Author: Daniel Howard, MSSP Solutions Engineer

================================================================================
DISCLAIMER AND TERMS OF USE
================================================================================
This script is provided by the author for educational and diagnostic purposes
only. It is NOT an official Fortinet product, tool, or support utility, and is
not endorsed, tested, or maintained by Fortinet, Inc.

Use of this script is at your own risk. The author and Fortinet, Inc. assume
no responsibility or liability for:
    - Any direct, indirect, incidental, or consequential damages
    - System outages, configuration errors, or performance impacts
    - Improper or unauthorized application in production environments

By using, copying, or distributing this script, you agree that:
    1. It is provided "AS IS" without warranties of any kind
    2. You will test and validate in a non-production environment first
    3. You assume full responsibility for its operation and outcomes

© 2026 Daniel Howard. Licensed under MIT License.
================================================================================

Uses the FortiOS REST API to query device state and deploy configuration
remotely — no SSH or paramiko required. Works with FortiOS 7.2+ using
Bearer token authentication.

Architecture:
  - READ operations (get/show/diagnose) → structured JSON monitor API endpoints
  - WRITE operations (config scripts)   → POST /api/v2/monitor/system/config-script/upload
  - CMDB reads (show config equivalent) → GET /api/v2/cmdb/{path}

The config-script/upload endpoint accepts multi-line CLI config blocks via
multipart file upload. The script executes immediately on upload and returns
CLI output (including errors) in the response body.

Requirements:
    - Python 3.8+
    - requests library
    - FortiGate API token with appropriate admin profile permissions
"""

import io
import json
import re
from typing import Any, Dict, List, Optional

import requests
import urllib3

# Suppress SSL warnings for self-signed certs (common in lab/MSSP environments)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ============================================================================
# SAFETY CONTROLS
# ============================================================================

# Config commands that are always blocked (destructive operations)
BLOCKED_CONFIG_PATTERNS = [
    r"^config\s+system\s+admin\b",
    r"^set\s+password\b",
    r"^delete\s+system\s+admin\b",
    r"^execute\s+factoryreset\b",
    r"^execute\s+formatlogdisk\b",
    r"^execute\s+shutdown\b",
    r"^execute\s+reboot\b",
    r"^execute\s+restore\s+image\b",
    r"^diagnose\s+sys\s+kill\b",
]


def is_config_blocked(command: str) -> bool:
    """Check if a config command is on the blocklist."""
    cmd = command.strip().lower()
    return any(re.match(p, cmd) for p in BLOCKED_CONFIG_PATTERNS)


def validate_config_script(script: str) -> tuple:
    """Validate a config script against safety rules.

    Returns:
        (is_valid, blocked_commands)
    """
    blocked = []
    for line in script.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if is_config_blocked(line):
            blocked.append(line)
    return (len(blocked) == 0, blocked)


# ============================================================================
# CLI COMMAND → API ENDPOINT MAPPING
# ============================================================================

# Maps common CLI commands to their REST API equivalents.
# Each entry: (endpoint, description, result_key)
# result_key is the key in the API response that holds the useful data.
MONITOR_API_MAP = {
    # System status
    "get system status":                ("/monitor/system/status", "System status"),
    "get system performance status":    ("/monitor/system/performance/status", "CPU/memory performance"),
    "get system interface":             ("/monitor/system/interface", "Interface details"),
    "get system interface physical":    ("/monitor/system/available-interfaces", "Physical interfaces"),

    # Routing
    "get router info routing-table all": ("/monitor/router/ipv4", "IPv4 routing table"),

    # SD-WAN
    "diagnose sys sdwan health-check":  ("/monitor/virtual-wan/health-check", "SD-WAN health checks"),
    "diagnose sys sdwan member":        ("/monitor/virtual-wan/members", "SD-WAN members"),
    "diagnose sys sdwan intf-sla-log":  ("/monitor/virtual-wan/sla-log", "SD-WAN SLA logs"),

    # VPN
    "get vpn ipsec tunnel summary":     ("/monitor/vpn/ipsec", "IPsec tunnels"),

    # BGP
    "get router info bgp summary":      ("/monitor/router/bgp/neighbors", "BGP neighbors"),

    # HA
    "diagnose sys ha status":           ("/monitor/system/ha-peer", "HA peer status"),

    # Resources
    "get system performance":           ("/monitor/system/resource/usage", "Resource usage"),
    "diagnose sys session stat":        ("/monitor/firewall/session", "Session statistics"),

    # DHCP
    "get system dhcp":                  ("/monitor/system/dhcp", "DHCP leases"),

    # NTP
    "get system ntp":                   ("/monitor/system/ntp/status", "NTP status"),
}


def find_api_endpoint(command: str) -> Optional[tuple]:
    """Try to match a CLI command to a known REST API endpoint.

    Returns:
        (endpoint, description) or None if no match
    """
    cmd = command.strip().lower()
    # Exact match first
    if cmd in MONITOR_API_MAP:
        ep, desc = MONITOR_API_MAP[cmd]
        return ep, desc
    # Prefix match (e.g., "get system status" matches "get system status foo")
    for pattern, (ep, desc) in MONITOR_API_MAP.items():
        if cmd.startswith(pattern):
            return ep, desc
    return None


# ============================================================================
# FORTIGATE CLIENT
# ============================================================================

class FortiGateCLI:
    """Query FortiGate devices and deploy configuration via REST API.

    Two modes of operation:
      1. QUERY mode — translates CLI commands to monitor API endpoints,
         returns structured JSON data. No SSH needed.
      2. CONFIG mode — uploads config scripts via config-script/upload,
         executes them on the device, returns CLI output.

    Example:
        fg = FortiGateCLI("192.168.1.1", api_token="your_token")

        # Query mode — returns structured JSON
        result = fg.query("get system status")
        print(result.data)  # dict with hostname, firmware, serial, etc.

        # Config mode — deploys configuration
        result = fg.deploy_config('''
            config system automation-trigger
                edit "CPU-High"
                    set trigger-type event-based
                next
            end
        ''')
        print(result.output)  # CLI output from device

        # Direct API access
        status = fg.api_get("/monitor/system/status")
    """

    def __init__(
        self,
        host: str,
        api_token: str,
        *,
        verify_ssl: bool = False,
        timeout: int = 30,
        port: int = 443,
    ):
        self.host = host
        self.port = port
        self.base_url = f"https://{host}:{port}/api/v2"
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {api_token}",
        })
        self._session.verify = verify_ssl

    def close(self):
        """Close the underlying HTTP session."""
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ------------------------------------------------------------------
    # Low-level API methods
    # ------------------------------------------------------------------

    def api_get(self, endpoint: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """GET request to FortiOS API. Returns parsed JSON."""
        url = f"{self.base_url}{endpoint}"
        resp = self._session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def api_post(self, endpoint: str, data: Dict[str, Any] | None = None, timeout: int | None = None) -> Dict[str, Any]:
        """POST JSON to FortiOS API."""
        url = f"{self.base_url}{endpoint}"
        resp = self._session.post(
            url, json=data,
            headers={"Content-Type": "application/json"},
            timeout=timeout or self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # QUERY mode — CLI commands → monitor API
    # ------------------------------------------------------------------

    def query(self, command: str) -> "QueryResult":
        """Execute a read-only CLI command via the REST API.

        Translates common CLI commands (get/show/diagnose) to their
        equivalent REST API monitor endpoints and returns structured JSON.

        Args:
            command: CLI command (e.g., "get system status")

        Returns:
            QueryResult with structured data
        """
        command = command.strip()
        match = find_api_endpoint(command)

        if not match:
            return QueryResult(
                success=False,
                command=command,
                data={},
                error=f"No API mapping for: {command}. Use api_get() directly or deploy_config() for config commands.",
                host=self.host,
            )

        endpoint, description = match
        try:
            resp = self.api_get(endpoint)
            return QueryResult(
                success=True,
                command=command,
                data=resp.get("results", resp),
                endpoint=endpoint,
                description=description,
                host=self.host,
            )
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code
            # 404 = endpoint not available on this firmware/model
            if status == 404:
                error = f"{description}: endpoint not available on this device ({endpoint})"
            else:
                error = f"HTTP {status}: {e.response.text[:200]}"
            return QueryResult(
                success=False, command=command, data={},
                error=error, host=self.host,
            )
        except requests.exceptions.ConnectionError:
            return QueryResult(
                success=False, command=command, data={},
                error=f"Connection failed to {self.host}:{self.port}",
                host=self.host,
            )
        except requests.exceptions.Timeout:
            return QueryResult(
                success=False, command=command, data={},
                error=f"Request timed out ({self.timeout}s)",
                host=self.host,
            )

    def query_many(self, commands: list[str]) -> list["QueryResult"]:
        """Execute multiple read-only commands, returning results for each."""
        return [self.query(cmd) for cmd in commands]

    # ------------------------------------------------------------------
    # CONFIG mode — deploy config scripts
    # ------------------------------------------------------------------

    def deploy_config(self, script: str, *, timeout: int | None = None) -> "ConfigResult":
        """Deploy a configuration script to the FortiGate.

        Uses POST /api/v2/monitor/system/config-script/upload with
        multipart file upload. The script executes immediately on upload.

        Args:
            script: Multi-line FortiOS config script (config/edit/set/end blocks)
            timeout: Override default timeout

        Returns:
            ConfigResult with CLI output and success/failure status
        """
        script = script.strip()
        is_valid, blocked = validate_config_script(script)
        if not is_valid:
            return ConfigResult(
                success=False,
                script=script,
                cli_output="",
                error=f"Blocked commands: {', '.join(blocked)}",
                host=self.host,
            )

        try:
            url = f"{self.base_url}/monitor/system/config-script/upload"
            files = {
                "filename": ("script.txt", io.BytesIO(script.encode("utf-8")), "text/plain"),
            }
            resp = self._session.post(url, files=files, timeout=timeout or self.timeout)

            body = resp.json()
            status = body.get("status", "")
            cli_output = body.get("cli_error", "")

            if resp.status_code == 200 and status == "success":
                return ConfigResult(
                    success=True,
                    script=script,
                    cli_output=cli_output,
                    host=self.host,
                )
            else:
                return ConfigResult(
                    success=False,
                    script=script,
                    cli_output=cli_output,
                    error=body.get("error", f"HTTP {resp.status_code}: {status}"),
                    host=self.host,
                )
        except requests.exceptions.ConnectionError:
            return ConfigResult(
                success=False, script=script, cli_output="",
                error=f"Connection failed to {self.host}:{self.port}",
                host=self.host,
            )
        except requests.exceptions.Timeout:
            return ConfigResult(
                success=False, script=script, cli_output="",
                error=f"Script upload timed out ({timeout or self.timeout}s)",
                host=self.host,
            )

    def get_config_history(self) -> list[Dict[str, Any]]:
        """Get execution history of config scripts."""
        data = self.api_get("/monitor/system/config-script")
        return data.get("results", {}).get("conf_scripts", {}).get("history", [])

    # ------------------------------------------------------------------
    # CMDB — read configuration (equivalent to "show" commands)
    # ------------------------------------------------------------------

    def get_cmdb(self, path: str) -> Dict[str, Any]:
        """Read CMDB configuration (equivalent to 'show' commands).

        Args:
            path: CMDB path, e.g., "system/interface", "firewall/policy",
                  "system/sdwan", "vpn.ipsec/phase1-interface"

        Returns:
            Dict with 'results' list of configuration objects
        """
        return self.api_get(f"/cmdb/{path}")

    # ------------------------------------------------------------------
    # Convenience methods — structured JSON queries
    # ------------------------------------------------------------------

    def get_system_status(self) -> "QueryResult":
        """System status (hostname, firmware, serial, uptime)."""
        return self.query("get system status")

    def get_performance(self) -> "QueryResult":
        """CPU and memory performance."""
        return self.query("get system performance status")

    def get_interfaces(self) -> "QueryResult":
        """All interfaces with stats."""
        return self.query("get system interface")

    def get_routing_table(self) -> "QueryResult":
        """IPv4 routing table."""
        return self.query("get router info routing-table all")

    def get_sdwan_health(self) -> "QueryResult":
        """SD-WAN health check SLA probes."""
        return self.query("diagnose sys sdwan health-check")

    def get_sdwan_members(self) -> "QueryResult":
        """SD-WAN member interface status."""
        return self.query("diagnose sys sdwan member")

    def get_ha_status(self) -> "QueryResult":
        """HA peer status."""
        return self.query("diagnose sys ha status")

    def get_vpn_tunnels(self) -> "QueryResult":
        """IPsec VPN tunnel status."""
        return self.query("get vpn ipsec tunnel summary")

    def get_bgp_neighbors(self) -> "QueryResult":
        """BGP neighbor summary."""
        return self.query("get router info bgp summary")


# ============================================================================
# RESULT MODELS
# ============================================================================

class QueryResult:
    """Result from a monitor API query."""

    def __init__(
        self,
        *,
        success: bool,
        command: str,
        data: Any,
        host: str,
        error: str = "",
        endpoint: str = "",
        description: str = "",
    ):
        self.success = success
        self.command = command
        self.data = data
        self.host = host
        self.error = error
        self.endpoint = endpoint
        self.description = description

    def __repr__(self) -> str:
        status = "OK" if self.success else f"FAIL: {self.error}"
        return f"<QueryResult host={self.host} cmd='{self.command}' status={status}>"

    def __bool__(self) -> bool:
        return self.success

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "success": self.success,
            "host": self.host,
            "command": self.command,
            "data": self.data,
        }
        if self.endpoint:
            d["endpoint"] = self.endpoint
        if self.error:
            d["error"] = self.error
        return d

    def print(self, indent: int = 2) -> None:
        """Pretty-print the result."""
        if self.success:
            print(f"[{self.host}] {self.description or self.command}")
            print(json.dumps(self.data, indent=indent))
        else:
            print(f"[{self.host}] ERROR: {self.error}")


class ConfigResult:
    """Result from a config script deployment."""

    def __init__(
        self,
        *,
        success: bool,
        script: str,
        cli_output: str,
        host: str,
        error: str = "",
    ):
        self.success = success
        self.script = script
        self.cli_output = cli_output
        self.host = host
        self.error = error

    def __repr__(self) -> str:
        status = "OK" if self.success else f"FAIL: {self.error}"
        return f"<ConfigResult host={self.host} status={status}>"

    def __bool__(self) -> bool:
        return self.success

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "success": self.success,
            "host": self.host,
            "script": self.script,
        }
        if self.cli_output:
            d["cli_output"] = self.cli_output
        if self.error:
            d["error"] = self.error
        return d

    def print(self) -> None:
        """Pretty-print the result."""
        if self.success:
            print(f"[{self.host}] Config deployed successfully")
            if self.cli_output:
                print(self.cli_output)
        else:
            print(f"[{self.host}] Config FAILED: {self.error}")
            if self.cli_output:
                print(f"CLI output:\n{self.cli_output}")


# ============================================================================
# MULTI-DEVICE RUNNER
# ============================================================================

class FleetCLI:
    """Run queries and deploy config across multiple FortiGates.

    Example:
        fleet = FleetCLI()
        fleet.add("192.168.1.1", "token1", name="HQ")
        fleet.add("192.168.2.1", "token2", name="Branch-1")

        results = fleet.query_all("get system status")
        for r in results:
            r.print()
    """

    def __init__(self, *, verify_ssl: bool = False, timeout: int = 30):
        self._devices: List[Dict[str, Any]] = []
        self.verify_ssl = verify_ssl
        self.timeout = timeout

    def add(
        self,
        host: str,
        api_token: str,
        *,
        name: str | None = None,
        port: int = 443,
    ) -> None:
        """Add a FortiGate device."""
        self._devices.append({
            "host": host,
            "api_token": api_token,
            "name": name or host,
            "port": port,
        })

    def load_from_file(self, path: str) -> int:
        """Load devices from a config file (CSV: ip, api_token, name).

        Lines starting with # are ignored.

        Returns:
            Number of devices loaded
        """
        count = 0
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 2:
                    host = parts[0]
                    token = parts[1]
                    name = parts[2] if len(parts) > 2 else host
                    self.add(host, token, name=name)
                    count += 1
        return count

    def query_all(self, command: str) -> List[QueryResult]:
        """Execute a query command on all devices."""
        results = []
        for dev in self._devices:
            with FortiGateCLI(
                dev["host"], dev["api_token"],
                verify_ssl=self.verify_ssl, timeout=self.timeout,
                port=dev["port"],
            ) as fg:
                results.append(fg.query(command))
        return results

    def deploy_config_all(self, script: str) -> List[ConfigResult]:
        """Deploy a config script to all devices."""
        results = []
        for dev in self._devices:
            with FortiGateCLI(
                dev["host"], dev["api_token"],
                verify_ssl=self.verify_ssl, timeout=self.timeout,
                port=dev["port"],
            ) as fg:
                results.append(fg.deploy_config(script))
        return results


# ============================================================================
# CLI ENTRYPOINT
# ============================================================================

def main():
    """Command-line interface for quick ad-hoc operations."""
    import argparse
    import os

    parser = argparse.ArgumentParser(
        description="FortiGate CLI Tool — Query devices and deploy config via REST API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Query device status (returns structured JSON)
  python fortigate_cli.py --host 192.168.1.1 --token $FG_TOKEN --query "get system status"

  # Query SD-WAN health
  python fortigate_cli.py --host 192.168.1.1 --token $FG_TOKEN --query "diagnose sys sdwan health-check"

  # Deploy config script
  python fortigate_cli.py --host 192.168.1.1 --token $FG_TOKEN --deploy config_script.txt

  # Direct API endpoint
  python fortigate_cli.py --host 192.168.1.1 --token $FG_TOKEN --api-get "/monitor/system/status"

  # Read CMDB config (equivalent to "show system interface")
  python fortigate_cli.py --host 192.168.1.1 --token $FG_TOKEN --cmdb "system/interface"

  # Multi-device from config file
  python fortigate_cli.py --config devices.csv --query "get system status"
        """,
    )

    parser.add_argument("--host", help="FortiGate IP/hostname")
    parser.add_argument("--token", help="API token (or set FORTIGATE_API_TOKEN env var)")
    parser.add_argument("--port", type=int, default=443, help="HTTPS port (default: 443)")
    parser.add_argument("--query", "-q", help="CLI command to query (mapped to monitor API)")
    parser.add_argument("--deploy", "-d", help="Path to config script file to deploy")
    parser.add_argument("--api-get", help="Direct GET to a monitor API endpoint")
    parser.add_argument("--cmdb", help="Read CMDB config path (e.g., system/interface)")
    parser.add_argument("--config", help="CSV config file for multi-device (ip,token,name)")
    parser.add_argument("--verify-ssl", action="store_true", help="Verify SSL certificates")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds (default: 30)")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--list-commands", action="store_true", help="List all supported CLI → API mappings")

    args = parser.parse_args()

    # List supported command mappings
    if args.list_commands:
        print("Supported CLI commands and their REST API equivalents:\n")
        print(f"  {'CLI Command':<45} {'API Endpoint':<50} {'Description'}")
        print(f"  {'-'*45} {'-'*50} {'-'*25}")
        for cmd, (ep, desc) in sorted(MONITOR_API_MAP.items()):
            print(f"  {cmd:<45} {ep:<50} {desc}")
        print(f"\nTotal: {len(MONITOR_API_MAP)} mapped commands")
        print("\nFor commands without a mapping, use --api-get or --cmdb.")
        return

    # Resolve token
    token = args.token or os.environ.get("FORTIGATE_API_TOKEN")

    # Multi-device mode
    if args.config:
        fleet = FleetCLI(verify_ssl=args.verify_ssl, timeout=args.timeout)
        count = fleet.load_from_file(args.config)
        print(f"Loaded {count} device(s) from {args.config}\n")

        if args.deploy:
            with open(args.deploy) as f:
                script = f.read()
            results = fleet.deploy_config_all(script)
            if args.json:
                print(json.dumps([r.to_dict() for r in results], indent=2))
            else:
                for r in results:
                    r.print()
                    print()
        elif args.query:
            results = fleet.query_all(args.query)
            if args.json:
                print(json.dumps([r.to_dict() for r in results], indent=2))
            else:
                for r in results:
                    r.print()
                    print()
        else:
            parser.error("--query or --deploy required")
        return

    # Single-device mode
    if not args.host:
        parser.error("--host required (or use --config for multi-device)")
    if not token:
        parser.error("--token required (or set FORTIGATE_API_TOKEN env var)")

    with FortiGateCLI(
        args.host, token,
        verify_ssl=args.verify_ssl,
        timeout=args.timeout,
        port=args.port,
    ) as fg:
        if args.deploy:
            with open(args.deploy) as f:
                script = f.read()
            result = fg.deploy_config(script)
            if args.json:
                print(json.dumps(result.to_dict(), indent=2))
            else:
                result.print()

        elif args.query:
            result = fg.query(args.query)
            if args.json:
                print(json.dumps(result.to_dict(), indent=2))
            else:
                result.print()

        elif args.api_get:
            data = fg.api_get(args.api_get)
            print(json.dumps(data, indent=2))

        elif args.cmdb:
            data = fg.get_cmdb(args.cmdb)
            print(json.dumps(data.get("results", data), indent=2))

        else:
            parser.error("--query, --deploy, --api-get, or --cmdb required")


if __name__ == "__main__":
    main()
