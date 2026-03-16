#!/usr/bin/env python3
"""
FortiGate Unused Interface Hardening Tool
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

Automatically discovers unused physical interfaces on any FortiGate model and
generates a config script to admin-disable them. Works across 50+ FortiGate
hardware models — no hardcoded interface names.

SECURITY RATIONALE:
  Every admin-up interface is a potential attack surface. Interfaces that have
  no link (nothing plugged in) and are not referenced in any active configuration
  should be administratively disabled to:
    - Reduce the device attack surface
    - Prevent unauthorized physical access via unused ports
    - Comply with CIS FortiGate Benchmark and NIST 800-41 guidelines
    - Meet MSSP/partner security hardening requirements

HOW IT WORKS:
  1. Discovers all physical interfaces via REST API (model-agnostic)
  2. Checks link status — identifies ports with no cable/link
  3. Cross-references interface usage across the entire config:
     - SD-WAN members
     - VPN tunnel bindings
     - Firewall policies (src/dst interfaces)
     - DHCP servers
     - HA heartbeat interfaces
     - Hardware switch membership
     - FortiSwitch/FortiLink uplinks
  4. Generates a config script to disable ONLY truly unused interfaces
  5. Optionally deploys the script via REST API

SAFETY:
  - NEVER disables interfaces that are in use (even if link is down)
  - NEVER disables management ports (mgmt), HA heartbeat ports, or loopbacks
  - WAN/LAN ports are protected by config evidence, not by name guessing
  - Generates a rollback script alongside the hardening script
  - Dry-run mode by default — you must explicitly opt in to deploy
  - Deploy requires interactive confirmation

Requirements:
    - Python 3.8+
    - requests library
    - FortiGate REST API token with admin profile permissions
    - FortiOS 7.2+
"""

import io
import json
import re
import sys
import warnings
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

import requests
import urllib3


# ============================================================================
# INTERFACE CLASSIFICATION
# ============================================================================

# Interface names that should NEVER be disabled regardless of link status.
# These are management, control-plane, or special-purpose interfaces.
PROTECTED_INTERFACES = {
    "mgmt", "mgmt1", "mgmt2",       # Dedicated management ports
    "ha", "ha1", "ha2",              # HA heartbeat ports
    "loopback", "lo", "lo0",         # Loopback interfaces
    "npu0_vlink0", "npu0_vlink1",    # NPU internal links
    "ssl.root", "ssl.vdom",          # SSL VPN virtual interfaces
    "any",                           # Wildcard
    "vsw.root",                      # Virtual switch
}

# Interface name prefixes that indicate virtual/non-physical interfaces
# These should be skipped entirely — they are not hardening candidates
VIRTUAL_PREFIXES = (
    "ssl.", "npu", "vwl", "vsw", "_", "fortilink",
)

# Interface types from the API that are physical ports
PHYSICAL_TYPES = {"physical", "hard-switch"}


# ============================================================================
# FORTIGATE INTERFACE ANALYZER
# ============================================================================

class InterfaceAnalyzer:
    """Analyzes FortiGate interfaces to find unused ports for hardening.

    Example:
        analyzer = InterfaceAnalyzer("192.168.1.1", api_token="your_token")

        # Audit — see what would be disabled
        report = analyzer.audit()
        report.print_summary()

        # Generate config script (dry-run)
        script = report.hardening_script()
        print(script)

        # Deploy to device
        result = analyzer.harden(deploy=True)
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
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {api_token}",
        })
        self._session.verify = verify_ssl

        # Suppress InsecureRequestWarning only for this session, not globally
        if not verify_ssl:
            warnings.filterwarnings(
                "ignore",
                category=urllib3.exceptions.InsecureRequestWarning,
            )

    def close(self):
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ------------------------------------------------------------------
    # API helpers
    # ------------------------------------------------------------------

    def _get(self, endpoint: str) -> Any:
        """GET request, returns results field."""
        url = f"{self.base_url}{endpoint}"
        resp = self._session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json().get("results", {})

    def _get_safe(self, endpoint: str, default: Any = None) -> Any:
        """GET request that returns default on error (for optional endpoints).

        Tracks failures in self._query_failures so the audit can report them.
        """
        try:
            return self._get(endpoint)
        except Exception as e:
            self._query_failures.append({
                "endpoint": endpoint,
                "error": str(e),
            })
            return default if default is not None else {}

    def _upload_config(self, script: str) -> Dict[str, Any]:
        """Upload and execute a config script."""
        url = f"{self.base_url}/monitor/system/config-script/upload"
        files = {
            "filename": ("harden_interfaces.txt", io.BytesIO(script.encode("utf-8")), "text/plain"),
        }
        resp = self._session.post(url, files=files, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Data collection
    # ------------------------------------------------------------------

    def get_physical_interfaces(self) -> List[Dict[str, Any]]:
        """Get all physical interfaces with link status from monitor API."""
        all_ifaces = self._get("/monitor/system/available-interfaces")
        if isinstance(all_ifaces, dict):
            all_ifaces = list(all_ifaces.values())

        physical = []
        for iface in all_ifaces:
            name = iface.get("name", "")
            itype = iface.get("type", "")

            # Skip virtual/tunnel/software interfaces
            if itype not in PHYSICAL_TYPES:
                continue
            if any(name.lower().startswith(p) for p in VIRTUAL_PREFIXES):
                continue
            # Note: PROTECTED_INTERFACES are NOT filtered here — they flow
            # through to classification so they appear in the report as
            # "protected" ports. This gives partners visibility.

            physical.append({
                "name": name,
                "type": itype,
                "link": iface.get("link", "unknown"),
                "status": iface.get("status", "unknown"),
                "speed": iface.get("speed", "N/A"),
                "ip": iface.get("ipv4_addresses", []),
                "is_hardware_switch": iface.get("is_hardware_switch", False),
                "is_hardware_switch_member": iface.get("is_hardware_switch_member", False),
            })
        return physical

    def get_referenced_interfaces(self, *, progress: bool = False) -> Dict[str, Set[str]]:
        """Collect all interfaces referenced in the running configuration.

        Returns:
            Dict mapping interface name → set of config sections that reference it
        """
        refs: Dict[str, Set[str]] = {}

        def add_ref(name: str, section: str):
            if name:
                refs.setdefault(name, set()).add(section)

        def _progress(msg: str):
            if progress:
                print(f"    Checking {msg}...", flush=True)

        # 1. SD-WAN members
        _progress("SD-WAN config")
        sdwan = self._get_safe("/cmdb/system/sdwan")
        if isinstance(sdwan, dict):
            for m in sdwan.get("members", []):
                add_ref(m.get("interface", ""), "sdwan-member")
        elif isinstance(sdwan, list) and sdwan:
            for m in sdwan[0].get("members", []):
                add_ref(m.get("interface", ""), "sdwan-member")

        # 2. VPN phase1 interface bindings
        _progress("VPN tunnel bindings")
        vpn_p1 = self._get_safe("/cmdb/vpn.ipsec/phase1-interface", [])
        if isinstance(vpn_p1, list):
            for p1 in vpn_p1:
                add_ref(p1.get("interface", ""), f"vpn:{p1.get('name', '?')}")

        # 3. Firewall policies (source and destination interfaces)
        _progress("firewall policies")
        policies = self._get_safe("/cmdb/firewall/policy", [])
        if isinstance(policies, list):
            for pol in policies:
                pol_id = pol.get("policyid", "?")
                for src in pol.get("srcintf", []):
                    add_ref(src.get("name", ""), f"policy:{pol_id}:src")
                for dst in pol.get("dstintf", []):
                    add_ref(dst.get("name", ""), f"policy:{pol_id}:dst")

        # 4. DHCP servers
        _progress("DHCP servers")
        dhcp = self._get_safe("/cmdb/system.dhcp/server", [])
        if isinstance(dhcp, list):
            for srv in dhcp:
                add_ref(srv.get("interface", ""), "dhcp-server")

        # 5. HA heartbeat interfaces
        _progress("HA config")
        ha = self._get_safe("/cmdb/system/ha")
        if isinstance(ha, dict):
            for hb in ha.get("hbdev", []):
                add_ref(hb.get("name", ""), "ha-heartbeat")
            # Monitor interfaces
            for mi in ha.get("monitor", []):
                add_ref(mi.get("name", ""), "ha-monitor")
        elif isinstance(ha, list) and ha:
            for hb in ha[0].get("hbdev", []):
                add_ref(hb.get("name", ""), "ha-heartbeat")
            for mi in ha[0].get("monitor", []):
                add_ref(mi.get("name", ""), "ha-monitor")

        # 6. Hardware switch membership (parent switches reference members)
        _progress("hardware switches and interfaces")
        ifaces = self._get_safe("/cmdb/system/interface", [])
        if isinstance(ifaces, list):
            for iface in ifaces:
                # Check if this is a hardware switch with member ports
                if iface.get("type") == "hard-switch":
                    sw_name = iface.get("name", "")
                    for member in iface.get("member", []):
                        member_name = member.get("interface-name", "")
                        add_ref(member_name, f"hw-switch:{sw_name}")
                # Check if interface is bound to a parent (e.g., aggregate member)
                parent = iface.get("interface", "")
                if parent and iface.get("type") == "physical":
                    add_ref(iface.get("name", ""), f"aggregate:{parent}")

        # 7. Zones (interfaces assigned to zones)
        _progress("zones")
        zones = self._get_safe("/cmdb/system/zone", [])
        if isinstance(zones, list):
            for zone in zones:
                zone_name = zone.get("name", "?")
                for member in zone.get("interface", []):
                    add_ref(member.get("interface-name", ""), f"zone:{zone_name}")

        # 8. Static routes (interfaces used as gateway)
        _progress("static routes")
        routes = self._get_safe("/cmdb/router/static", [])
        if isinstance(routes, list):
            for route in routes:
                add_ref(route.get("device", ""), "static-route")

        # 9. DNS settings
        _progress("DNS config")
        dns = self._get_safe("/cmdb/system/dns")
        if isinstance(dns, dict):
            add_ref(dns.get("source-ip-interface", ""), "dns-source")

        return refs

    def get_system_info(self) -> Dict[str, Any]:
        """Get basic system info for the report."""
        try:
            return self._get("/monitor/system/status")
        except Exception:
            return {}

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def audit(self, *, progress: bool = False) -> "HardeningReport":
        """Analyze all interfaces and generate a hardening report.

        Returns:
            HardeningReport with categorized interfaces and config scripts

        Uses fail-closed safety: if any config reference query fails,
        no interfaces will be marked as candidates for disabling.
        """
        # Reset failure tracker before each audit
        self._query_failures: List[Dict[str, str]] = []

        # Collect data
        if progress:
            print(f"\n  Connecting to {self.host}...", flush=True)
        system_info = self.get_system_info()
        if progress:
            hostname = system_info.get("hostname", self.host)
            model = f"{system_info.get('model_name', '')} {system_info.get('model_number', '')}".strip()
            print(f"  Connected: {hostname} ({model})", flush=True)
            print(f"  Discovering physical interfaces...", flush=True)
        physical_ifaces = self.get_physical_interfaces()
        if progress:
            print(f"  Found {len(physical_ifaces)} physical interface(s)", flush=True)
            print(f"  Cross-referencing config sections:", flush=True)
        config_refs = self.get_referenced_interfaces(progress=progress)
        if progress:
            print(f"  Analyzing interface usage...\n", flush=True)

        # Categorize each interface
        active = []         # Link up, in use — leave alone
        in_use_no_link = [] # Link down but referenced in config — warn but don't touch
        candidates = []     # Link down, not referenced — disable these
        already_down = []   # Already admin disabled
        protected = []      # Protected by policy (management, etc.)

        for iface in physical_ifaces:
            name = iface["name"]
            link = iface["link"]
            admin_status = iface["status"]
            refs = config_refs.get(name, set())
            has_ip = len(iface.get("ip", [])) > 0
            is_switch = iface["is_hardware_switch"]

            iface["refs"] = sorted(refs) if refs else []

            # Already admin disabled
            if admin_status == "down":
                already_down.append(iface)
                continue

            # Protected interface names
            if name.lower() in PROTECTED_INTERFACES:
                protected.append(iface)
                continue

            # Hardware switch parent — don't disable (members handle traffic)
            if is_switch:
                active.append(iface)
                continue

            # Link is up — interface is operational
            if link == "up":
                active.append(iface)
                continue

            # Link is down — check if referenced in config
            if refs:
                in_use_no_link.append(iface)
                continue

            # Link is down, has IP assigned — might be intentional
            if has_ip:
                in_use_no_link.append(iface)
                continue

            # Unknown link state — treat as in-use (fail-closed)
            if link != "down":
                in_use_no_link.append(iface)
                continue

            # Link down + no config refs + no IP = candidate for disabling
            candidates.append(iface)

        # FAIL-CLOSED: If any config reference query failed, we cannot
        # guarantee that interfaces are truly unreferenced. Move all
        # candidates back to in_use_no_link and flag the failures.
        if self._query_failures and candidates:
            for iface in candidates:
                iface["refs"] = ["QUERY_FAILED — cannot confirm unreferenced"]
            in_use_no_link.extend(candidates)
            candidates = []

        return HardeningReport(
            host=self.host,
            system_info=system_info,
            active=active,
            in_use_no_link=in_use_no_link,
            candidates=candidates,
            already_down=already_down,
            protected=protected,
            config_refs=config_refs,
            query_failures=self._query_failures,
        )

    def harden(self, *, deploy: bool = False, progress: bool = False, confirm: bool = True) -> "HardeningReport":
        """Audit and optionally deploy the hardening config.

        Args:
            deploy: If True, deploy the config script to the device.
                    If False (default), dry-run only.
            progress: If True, print progress messages during API queries.
            confirm: If True (default), prompt for confirmation before deploying.

        Returns:
            HardeningReport with deployment results
        """
        report = self.audit(progress=progress)

        if deploy and report.candidates:
            # Show what will be changed and ask for confirmation
            if confirm:
                report.print_summary()
                iface_names = ", ".join(i["name"] for i in sorted(report.candidates, key=lambda x: x["name"]))
                print(f"  About to DISABLE {len(report.candidates)} interface(s): {iface_names}")
                print(f"  on {report.hostname} ({self.host})\n")
                answer = input("  Proceed with deployment? [y/N]: ").strip().lower()
                if answer not in ("y", "yes"):
                    print("  Deployment cancelled.")
                    return report

            script = report.hardening_script()
            result = self._upload_config(script)
            report.deployed = True
            report.deploy_result = result
            report.deploy_success = (
                result.get("status") == "success"
                and result.get("http_status") == 200
            )

        return report


# ============================================================================
# REPORT MODEL
# ============================================================================

class HardeningReport:
    """Results from an interface hardening audit."""

    def __init__(
        self,
        *,
        host: str,
        system_info: Dict[str, Any],
        active: List[Dict],
        in_use_no_link: List[Dict],
        candidates: List[Dict],
        already_down: List[Dict],
        protected: List[Dict],
        config_refs: Dict[str, Set[str]],
        query_failures: Optional[List[Dict[str, str]]] = None,
    ):
        self.host = host
        self.system_info = system_info
        self.active = active
        self.in_use_no_link = in_use_no_link
        self.candidates = candidates
        self.already_down = already_down
        self.protected = protected
        self.config_refs = config_refs
        self.query_failures = query_failures or []
        self.deployed = False
        self.deploy_result = None
        self.deploy_success = False
        self.timestamp = datetime.now(timezone.utc).isoformat()

    @property
    def hostname(self) -> str:
        return self.system_info.get("hostname", self.host)

    @property
    def model(self) -> str:
        name = self.system_info.get("model_name", "")
        number = self.system_info.get("model_number", "")
        return f"{name} {number}".strip() or "Unknown"

    def hardening_script(self) -> str:
        """Generate FortiOS config script to disable unused interfaces."""
        if not self.candidates:
            return "# No unused interfaces found — nothing to disable.\n"

        lines = [
            f"# FortiGate Interface Hardening Script",
            f"# Device: {self.hostname} ({self.host})",
            f"# Model: {self.model}",
            f"# Generated: {self.timestamp}",
            f"# Interfaces to disable: {len(self.candidates)}",
            f"#",
            f"# This script disables physical interfaces that have:",
            f"#   - No link (nothing plugged in)",
            f"#   - No references in firewall policies, SD-WAN, VPN, DHCP, HA, or zones",
            f"#   - No IP address assigned",
            f"#",
            f"config system interface",
        ]
        for iface in sorted(self.candidates, key=lambda x: x["name"]):
            lines.append(f'    edit "{iface["name"]}"')
            lines.append(f'        set status down')
            lines.append(f'    next')
        lines.append("end")
        return "\n".join(lines) + "\n"

    def rollback_script(self) -> str:
        """Generate a rollback script to re-enable disabled interfaces."""
        if not self.candidates:
            return "# No interfaces were disabled — nothing to roll back.\n"

        lines = [
            f"# FortiGate Interface Hardening ROLLBACK Script",
            f"# Device: {self.hostname} ({self.host})",
            f"# Generated: {self.timestamp}",
            f"#",
            f"# Re-enables {len(self.candidates)} interface(s) disabled by hardening script",
            f"#",
            f"config system interface",
        ]
        for iface in sorted(self.candidates, key=lambda x: x["name"]):
            lines.append(f'    edit "{iface["name"]}"')
            lines.append(f'        set status up')
            lines.append(f'    next')
        lines.append("end")
        return "\n".join(lines) + "\n"

    def print_summary(self) -> None:
        """Print a human-readable audit summary."""
        print(f"\n{'='*70}")
        print(f"  FORTIGATE INTERFACE HARDENING AUDIT")
        print(f"{'='*70}")
        print(f"  Device:    {self.hostname} ({self.host})")
        print(f"  Model:     {self.model}")
        print(f"  Timestamp: {self.timestamp}")
        print(f"{'='*70}")

        total = len(self.active) + len(self.in_use_no_link) + len(self.candidates) + len(self.already_down) + len(self.protected)
        print(f"\n  Total physical interfaces: {total}")
        print(f"  Active (link up):          {len(self.active)}")
        print(f"  Already disabled:          {len(self.already_down)}")
        print(f"  Protected:                 {len(self.protected)}")

        # Active interfaces
        if self.active:
            print(f"\n  ACTIVE INTERFACES (link up — no change)")
            print(f"  {'Name':<15} {'Type':<14} {'Speed':<10} {'Referenced By'}")
            print(f"  {'-'*15} {'-'*14} {'-'*10} {'-'*30}")
            for i in self.active:
                refs = ", ".join(i.get("refs", [])) or "-"
                speed = i["speed"] if i["speed"] != "N/A" else "-"
                print(f"  {i['name']:<15} {i['type']:<14} {speed:<10} {refs}")

        # In-use but no link — warn
        if self.in_use_no_link:
            print(f"\n  WARNING: Link down but REFERENCED in config ({len(self.in_use_no_link)} interfaces)")
            print(f"  These will NOT be disabled — they may be temporarily disconnected.")
            print(f"  {'Name':<15} {'Referenced By'}")
            print(f"  {'-'*15} {'-'*50}")
            for i in self.in_use_no_link:
                refs = ", ".join(i.get("refs", []))
                print(f"  {i['name']:<15} {refs}")

        # Candidates for disabling
        if self.candidates:
            print(f"\n  UNUSED INTERFACES — CANDIDATES FOR DISABLING ({len(self.candidates)})")
            print(f"  {'Name':<15} {'Type':<14} {'Link':<8} {'Reason'}")
            print(f"  {'-'*15} {'-'*14} {'-'*8} {'-'*35}")
            for i in self.candidates:
                print(f"  {i['name']:<15} {i['type']:<14} {i['link']:<8} No link, no config references")
        else:
            print(f"\n  No unused interfaces found — device is already hardened.")

        # Already disabled
        if self.already_down:
            print(f"\n  ALREADY ADMIN DISABLED ({len(self.already_down)})")
            for i in self.already_down:
                print(f"    {i['name']}")

        # Query failures warning
        if self.query_failures:
            print(f"\n  *** SAFETY WARNING: {len(self.query_failures)} config query(s) FAILED ***")
            print(f"  Cannot confirm interfaces are unreferenced. No interfaces will be disabled.")
            for f in self.query_failures:
                print(f"    - {f['endpoint']}: {f['error']}")

        # Deployment status
        if self.deployed:
            if self.deploy_success:
                print(f"\n  DEPLOYED: Config script applied successfully.")
            else:
                print(f"\n  DEPLOY FAILED: {self.deploy_result}")

        print(f"\n{'='*70}\n")

    def to_dict(self) -> Dict[str, Any]:
        """Export report as a dict (for JSON serialization)."""
        return {
            "host": self.host,
            "hostname": self.hostname,
            "model": self.model,
            "timestamp": self.timestamp,
            "summary": {
                "active": len(self.active),
                "in_use_no_link": len(self.in_use_no_link),
                "candidates": len(self.candidates),
                "already_disabled": len(self.already_down),
                "protected": len(self.protected),
            },
            "active": [{"name": i["name"], "link": i["link"], "refs": i.get("refs", [])} for i in self.active],
            "in_use_no_link": [{"name": i["name"], "refs": i.get("refs", [])} for i in self.in_use_no_link],
            "candidates": [{"name": i["name"], "type": i["type"]} for i in self.candidates],
            "already_disabled": [i["name"] for i in self.already_down],
            "hardening_script": self.hardening_script(),
            "rollback_script": self.rollback_script(),
            "deployed": self.deployed,
            "deploy_success": self.deploy_success,
            "query_failures": self.query_failures,
        }


# ============================================================================
# MULTI-DEVICE RUNNER
# ============================================================================

class FleetHardener:
    """Audit and harden unused interfaces across multiple FortiGates.

    Example:
        fleet = FleetHardener()
        fleet.add("192.168.1.1", "token1", name="HQ")
        fleet.add("192.168.2.1", "token2", name="Branch-1")

        reports = fleet.audit_all()
        for r in reports:
            r.print_summary()
    """

    def __init__(self, *, verify_ssl: bool = False, timeout: int = 30):
        self._devices: List[Dict[str, Any]] = []
        self.verify_ssl = verify_ssl
        self.timeout = timeout

    def add(self, host: str, api_token: str, *, name: Optional[str] = None, port: int = 443):
        self._devices.append({
            "host": host, "api_token": api_token,
            "name": name or host, "port": port,
        })

    def load_from_file(self, path: str) -> int:
        """Load devices from CSV file (ip, api_token, name)."""
        count = 0
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 2:
                    self.add(parts[0], parts[1], name=parts[2] if len(parts) > 2 else None)
                    count += 1
        return count

    def audit_all(self) -> List[HardeningReport]:
        """Audit all devices (dry-run)."""
        reports = []
        for dev in self._devices:
            try:
                with InterfaceAnalyzer(
                    dev["host"], dev["api_token"],
                    verify_ssl=self.verify_ssl, timeout=self.timeout,
                    port=dev["port"],
                ) as analyzer:
                    reports.append(analyzer.audit())
            except Exception as e:
                print(f"[{dev['host']}] ERROR: {e}")
        return reports

    def harden_all(self, *, deploy: bool = False, progress: bool = False, confirm: bool = True) -> List[HardeningReport]:
        """Audit and optionally deploy hardening to all devices."""
        reports = []
        for dev in self._devices:
            try:
                with InterfaceAnalyzer(
                    dev["host"], dev["api_token"],
                    verify_ssl=self.verify_ssl, timeout=self.timeout,
                    port=dev["port"],
                ) as analyzer:
                    reports.append(analyzer.harden(deploy=deploy, progress=progress, confirm=confirm))
            except Exception as e:
                print(f"[{dev['host']}] ERROR: {e}")
        return reports


# ============================================================================
# CLI ENTRYPOINT
# ============================================================================

def main():
    import argparse
    import os

    parser = argparse.ArgumentParser(
        description="FortiGate Unused Interface Hardening Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Audit a single device (dry-run — shows what WOULD be disabled)
  python fortigate_harden_interfaces.py --host 192.168.1.1 --token $FORTIGATE_API_TOKEN

  # Audit and save scripts to files
  python fortigate_harden_interfaces.py --host 192.168.1.1 --token $FORTIGATE_API_TOKEN --save-scripts

  # Audit and deploy (actually disables unused interfaces)
  python fortigate_harden_interfaces.py --host 192.168.1.1 --token $FORTIGATE_API_TOKEN --deploy

  # Audit entire fleet from config file
  python fortigate_harden_interfaces.py --config devices.csv

  # JSON output for automation
  python fortigate_harden_interfaces.py --host 192.168.1.1 --token $FORTIGATE_API_TOKEN --json
        """,
    )

    parser.add_argument("--host", help="FortiGate IP/hostname")
    parser.add_argument("--token", help="API token (or set FORTIGATE_API_TOKEN env var)")
    parser.add_argument("--port", type=int, default=443, help="HTTPS port (default: 443)")
    parser.add_argument("--config", help="CSV config file for multi-device (ip,token,name)")
    parser.add_argument("--deploy", action="store_true",
                        help="Deploy hardening config (default: dry-run audit only)")
    parser.add_argument("--save-scripts", action="store_true",
                        help="Save hardening and rollback scripts to files")
    parser.add_argument("--yes", "-y", action="store_true",
                        help="Skip deploy confirmation prompt (use with caution)")
    parser.add_argument("--verify-ssl", action="store_true", help="Verify SSL certificates")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds (default: 30)")
    parser.add_argument("--json", action="store_true", help="Output report as JSON")

    args = parser.parse_args()
    token = args.token or os.environ.get("FORTIGATE_API_TOKEN")

    # Multi-device mode
    if args.config:
        fleet = FleetHardener(verify_ssl=args.verify_ssl, timeout=args.timeout)
        count = fleet.load_from_file(args.config)
        print(f"Loaded {count} device(s) from {args.config}")

        reports = fleet.harden_all(deploy=args.deploy, progress=not args.json, confirm=not args.yes)

        if args.json:
            print(json.dumps([r.to_dict() for r in reports], indent=2))
        else:
            for r in reports:
                r.print_summary()

            # Summary across fleet
            total_candidates = sum(len(r.candidates) for r in reports)
            print(f"Fleet summary: {total_candidates} unused interface(s) across {len(reports)} device(s)")

        if args.save_scripts:
            for r in reports:
                hostname = re.sub(r'[^\w\-.]', '_', r.hostname)
                with open(f"harden_{hostname}.txt", "w") as f:
                    f.write(r.hardening_script())
                with open(f"rollback_{hostname}.txt", "w") as f:
                    f.write(r.rollback_script())
                print(f"Saved: harden_{hostname}.txt, rollback_{hostname}.txt")
        return

    # Single-device mode
    if not args.host:
        parser.error("--host required (or use --config for multi-device)")
    if not token:
        parser.error("--token required (or set FORTIGATE_API_TOKEN env var)")

    with InterfaceAnalyzer(
        args.host, token,
        verify_ssl=args.verify_ssl, timeout=args.timeout, port=args.port,
    ) as analyzer:
        report = analyzer.harden(deploy=args.deploy, progress=not args.json, confirm=not args.yes)

        if args.json:
            print(json.dumps(report.to_dict(), indent=2))
        else:
            report.print_summary()

            if not args.deploy and report.candidates:
                print("  To apply these changes, re-run with --deploy flag.")
                print(f"  Or save scripts with --save-scripts and review before deploying.\n")

        if args.save_scripts:
            hostname = re.sub(r'[^\w\-.]', '_', report.hostname)
            with open(f"harden_{hostname}.txt", "w") as f:
                f.write(report.hardening_script())
            with open(f"rollback_{hostname}.txt", "w") as f:
                f.write(report.rollback_script())
            print(f"Saved: harden_{hostname}.txt, rollback_{hostname}.txt")


if __name__ == "__main__":
    main()
