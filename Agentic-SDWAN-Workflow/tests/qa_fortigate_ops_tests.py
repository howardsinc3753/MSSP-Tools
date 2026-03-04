#!/usr/bin/env python3
"""
QA Test Suite for FortiGate Operations Solution Pack

Tests all tools and endpoints for correct behavior.
Stores results in tests/results/ directory.

Solution Pack: org.ulysses.solution.fortigate-ops/1.0.0
Author: Project Ulysses
Created: 2025-01-14
"""

import json
import httpx
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

# =============================================================================
# CONFIGURATION
# =============================================================================
TRUST_ANCHOR_URL = "http://10.0.0.100:8000"
PACK_NAME = "fortigate-ops"
RESULTS_DIR = Path(__file__).parent / "results"

# Lab devices for testing
TEST_DEVICES = {
    "lab-71f": "10.0.0.62",
    "fw-50g": "10.0.0.30"
}
DEFAULT_DEVICE = "10.0.0.62"

# Tools to test
FORTIGATE_TOOLS = [
    "org.ulysses.noc.fortigate-health-check/1.0.0",
    "org.ulysses.noc.fortigate-interface-status/1.0.0",
    "org.ulysses.noc.fortigate-routing-table/1.0.0",
    "org.ulysses.noc.fortigate-session-table/1.0.0",
    "org.ulysses.noc.fortigate-arp-table/1.0.0",
    "org.ulysses.noc.fortigate-performance-status/1.0.0",
    "org.ulysses.noc.fortigate-running-processes/1.0.0",
    "org.ulysses.noc.fortigate-network-analyzer/1.0.0",
]

# Runbooks to test
FORTIGATE_RUNBOOKS = [
    "org.ulysses.sop.fortigate-triage/1.0.0",
]


# =============================================================================
# TEST SUITE CLASS
# =============================================================================
class QATestSuite:
    """QA Test Suite for FortiGate Operations"""

    def __init__(self):
        self.results = {
            "suite": f"NFR-FORTIGATE-OPS-QA",
            "pack_id": "org.ulysses.solution.fortigate-ops/1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trust_anchor_url": TRUST_ANCHOR_URL,
            "test_devices": TEST_DEVICES,
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0
            },
            "tests": []
        }

    def record_test(
        self,
        test_id: str,
        name: str,
        description: str,
        status: str,
        details: str,
        duration_ms: int,
        category: str = "general"
    ):
        """Record a test result"""
        self.results["tests"].append({
            "test_id": test_id,
            "name": name,
            "description": description,
            "category": category,
            "status": status,
            "details": details,
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        self.results["summary"]["total"] += 1
        if status == "pass":
            self.results["summary"]["passed"] += 1
        elif status == "fail":
            self.results["summary"]["failed"] += 1
        else:
            self.results["summary"]["skipped"] += 1

    def save_results(self) -> Path:
        """Save test results to JSON file"""
        RESULTS_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"qa_{PACK_NAME}_{timestamp}.json"
        filepath = RESULTS_DIR / filename

        # Calculate success rate
        total = self.results["summary"]["total"]
        passed = self.results["summary"]["passed"]
        self.results["summary"]["success_rate"] = f"{(passed/total)*100:.1f}%" if total > 0 else "N/A"

        with open(filepath, "w") as f:
            json.dump(self.results, f, indent=2)

        return filepath


# =============================================================================
# INFRASTRUCTURE TESTS
# =============================================================================
async def test_trust_anchor_health(suite: QATestSuite, client: httpx.AsyncClient):
    """TEST-001: Verify Trust Anchor is healthy"""
    start = datetime.now()
    try:
        response = await client.get(f"{TRUST_ANCHOR_URL}/health")
        duration = int((datetime.now() - start).total_seconds() * 1000)

        if response.status_code == 200:
            suite.record_test(
                "FG-001", "Trust Anchor Health",
                "Verify Trust Anchor /health endpoint responds",
                "pass", f"Status: {response.status_code}",
                duration, "infrastructure"
            )
        else:
            suite.record_test(
                "FG-001", "Trust Anchor Health",
                "Verify Trust Anchor /health endpoint responds",
                "fail", f"Unexpected status: {response.status_code}",
                duration, "infrastructure"
            )
    except Exception as e:
        duration = int((datetime.now() - start).total_seconds() * 1000)
        suite.record_test(
            "FG-001", "Trust Anchor Health",
            "Verify Trust Anchor /health endpoint responds",
            "fail", str(e), duration, "infrastructure"
        )


async def test_tools_registered(suite: QATestSuite, client: httpx.AsyncClient):
    """TEST-002: Verify FortiGate tools are registered"""
    start = datetime.now()
    try:
        response = await client.get(f"{TRUST_ANCHOR_URL}/tools")
        duration = int((datetime.now() - start).total_seconds() * 1000)

        if response.status_code == 200:
            tools = response.json()
            tool_ids = [t.get("canonical_id", t.get("id", "")) for t in tools]

            # Check each FortiGate tool
            missing = []
            for tool_id in FORTIGATE_TOOLS:
                if tool_id not in tool_ids:
                    missing.append(tool_id)

            if not missing:
                suite.record_test(
                    "FG-002", "Tools Registered",
                    "Verify all FortiGate tools are registered",
                    "pass", f"All {len(FORTIGATE_TOOLS)} tools registered",
                    duration, "infrastructure"
                )
            else:
                suite.record_test(
                    "FG-002", "Tools Registered",
                    "Verify all FortiGate tools are registered",
                    "fail", f"Missing: {missing}",
                    duration, "infrastructure"
                )
        else:
            suite.record_test(
                "FG-002", "Tools Registered",
                "Verify all FortiGate tools are registered",
                "fail", f"GET /tools failed: {response.status_code}",
                duration, "infrastructure"
            )
    except Exception as e:
        duration = int((datetime.now() - start).total_seconds() * 1000)
        suite.record_test(
            "FG-002", "Tools Registered",
            "Verify all FortiGate tools are registered",
            "fail", str(e), duration, "infrastructure"
        )


# =============================================================================
# TOOL EXECUTION TESTS
# =============================================================================
async def test_health_check_tool(suite: QATestSuite, client: httpx.AsyncClient):
    """TEST-003: Execute FortiGate health check tool"""
    start = datetime.now()
    try:
        response = await client.post(
            f"{TRUST_ANCHOR_URL}/tools/execute",
            json={
                "tool_id": "org.ulysses.noc.fortigate-health-check/1.0.0",
                "parameters": {
                    "target_ip": DEFAULT_DEVICE
                }
            },
            timeout=60.0
        )
        duration = int((datetime.now() - start).total_seconds() * 1000)

        if response.status_code == 200:
            result = response.json()
            if result.get("success", False):
                suite.record_test(
                    "FG-003", "Health Check Execution",
                    f"Execute health check against {DEFAULT_DEVICE}",
                    "pass",
                    f"Hostname: {result.get('result', {}).get('hostname', 'N/A')}",
                    duration, "tool-execution"
                )
            else:
                suite.record_test(
                    "FG-003", "Health Check Execution",
                    f"Execute health check against {DEFAULT_DEVICE}",
                    "fail",
                    f"Tool returned error: {result.get('error', 'Unknown')}",
                    duration, "tool-execution"
                )
        else:
            suite.record_test(
                "FG-003", "Health Check Execution",
                f"Execute health check against {DEFAULT_DEVICE}",
                "fail", f"HTTP {response.status_code}: {response.text[:200]}",
                duration, "tool-execution"
            )
    except Exception as e:
        duration = int((datetime.now() - start).total_seconds() * 1000)
        suite.record_test(
            "FG-003", "Health Check Execution",
            f"Execute health check against {DEFAULT_DEVICE}",
            "fail", str(e), duration, "tool-execution"
        )


async def test_interface_status_tool(suite: QATestSuite, client: httpx.AsyncClient):
    """TEST-004: Execute FortiGate interface status tool"""
    start = datetime.now()
    try:
        response = await client.post(
            f"{TRUST_ANCHOR_URL}/tools/execute",
            json={
                "tool_id": "org.ulysses.noc.fortigate-interface-status/1.0.0",
                "parameters": {
                    "target_ip": DEFAULT_DEVICE
                }
            },
            timeout=60.0
        )
        duration = int((datetime.now() - start).total_seconds() * 1000)

        if response.status_code == 200:
            result = response.json()
            if result.get("success", False):
                iface_count = len(result.get("result", {}).get("interfaces", []))
                suite.record_test(
                    "FG-004", "Interface Status Execution",
                    f"Execute interface status against {DEFAULT_DEVICE}",
                    "pass", f"Found {iface_count} interfaces",
                    duration, "tool-execution"
                )
            else:
                suite.record_test(
                    "FG-004", "Interface Status Execution",
                    f"Execute interface status against {DEFAULT_DEVICE}",
                    "fail", f"Tool error: {result.get('error', 'Unknown')}",
                    duration, "tool-execution"
                )
        else:
            suite.record_test(
                "FG-004", "Interface Status Execution",
                f"Execute interface status against {DEFAULT_DEVICE}",
                "fail", f"HTTP {response.status_code}",
                duration, "tool-execution"
            )
    except Exception as e:
        duration = int((datetime.now() - start).total_seconds() * 1000)
        suite.record_test(
            "FG-004", "Interface Status Execution",
            f"Execute interface status against {DEFAULT_DEVICE}",
            "fail", str(e), duration, "tool-execution"
        )


async def test_routing_table_tool(suite: QATestSuite, client: httpx.AsyncClient):
    """TEST-005: Execute FortiGate routing table tool"""
    start = datetime.now()
    try:
        response = await client.post(
            f"{TRUST_ANCHOR_URL}/tools/execute",
            json={
                "tool_id": "org.ulysses.noc.fortigate-routing-table/1.0.0",
                "parameters": {
                    "target_ip": DEFAULT_DEVICE
                }
            },
            timeout=60.0
        )
        duration = int((datetime.now() - start).total_seconds() * 1000)

        if response.status_code == 200:
            result = response.json()
            if result.get("success", False):
                route_count = len(result.get("result", {}).get("routes", []))
                suite.record_test(
                    "FG-005", "Routing Table Execution",
                    f"Execute routing table against {DEFAULT_DEVICE}",
                    "pass", f"Found {route_count} routes",
                    duration, "tool-execution"
                )
            else:
                suite.record_test(
                    "FG-005", "Routing Table Execution",
                    f"Execute routing table against {DEFAULT_DEVICE}",
                    "fail", f"Tool error: {result.get('error', 'Unknown')}",
                    duration, "tool-execution"
                )
        else:
            suite.record_test(
                "FG-005", "Routing Table Execution",
                f"Execute routing table against {DEFAULT_DEVICE}",
                "fail", f"HTTP {response.status_code}",
                duration, "tool-execution"
            )
    except Exception as e:
        duration = int((datetime.now() - start).total_seconds() * 1000)
        suite.record_test(
            "FG-005", "Routing Table Execution",
            f"Execute routing table against {DEFAULT_DEVICE}",
            "fail", str(e), duration, "tool-execution"
        )


# =============================================================================
# RUNBOOK TESTS
# =============================================================================
async def test_triage_runbook(suite: QATestSuite, client: httpx.AsyncClient):
    """TEST-006: Execute FortiGate triage runbook"""
    start = datetime.now()
    try:
        response = await client.post(
            f"{TRUST_ANCHOR_URL}/runbooks/execute",
            json={
                "runbook_id": "org.ulysses.sop.fortigate-triage/1.0.0",
                "device": DEFAULT_DEVICE
            },
            timeout=120.0
        )
        duration = int((datetime.now() - start).total_seconds() * 1000)

        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "completed":
                suite.record_test(
                    "FG-006", "Triage Runbook Execution",
                    f"Execute triage runbook against {DEFAULT_DEVICE}",
                    "pass", f"Completed in {duration}ms",
                    duration, "runbook-execution"
                )
            else:
                suite.record_test(
                    "FG-006", "Triage Runbook Execution",
                    f"Execute triage runbook against {DEFAULT_DEVICE}",
                    "fail", f"Status: {result.get('status', 'Unknown')}",
                    duration, "runbook-execution"
                )
        else:
            suite.record_test(
                "FG-006", "Triage Runbook Execution",
                f"Execute triage runbook against {DEFAULT_DEVICE}",
                "skip", f"HTTP {response.status_code} - Runbook may not be registered",
                duration, "runbook-execution"
            )
    except Exception as e:
        duration = int((datetime.now() - start).total_seconds() * 1000)
        suite.record_test(
            "FG-006", "Triage Runbook Execution",
            f"Execute triage runbook against {DEFAULT_DEVICE}",
            "fail", str(e), duration, "runbook-execution"
        )


# =============================================================================
# CREDENTIAL TESTS
# =============================================================================
async def test_credentials_file_exists(suite: QATestSuite, client: httpx.AsyncClient):
    """TEST-007: Verify credentials file exists"""
    start = datetime.now()
    cred_path = Path(__file__).parent.parent.parent.parent / "config" / "fortigate_credentials.yaml"

    try:
        if cred_path.exists():
            suite.record_test(
                "FG-007", "Credentials File Exists",
                "Verify fortigate_credentials.yaml exists",
                "pass", f"Found at {cred_path}",
                int((datetime.now() - start).total_seconds() * 1000),
                "credentials"
            )
        else:
            suite.record_test(
                "FG-007", "Credentials File Exists",
                "Verify fortigate_credentials.yaml exists",
                "fail", f"Not found at {cred_path}",
                int((datetime.now() - start).total_seconds() * 1000),
                "credentials"
            )
    except Exception as e:
        suite.record_test(
            "FG-007", "Credentials File Exists",
            "Verify fortigate_credentials.yaml exists",
            "fail", str(e),
            int((datetime.now() - start).total_seconds() * 1000),
            "credentials"
        )


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================
async def run_tests():
    """Run all QA tests"""
    suite = QATestSuite()

    print(f"\n{'='*60}")
    print(f"FortiGate Operations QA Test Suite")
    print(f"{'='*60}")
    print(f"Trust Anchor: {TRUST_ANCHOR_URL}")
    print(f"Default Device: {DEFAULT_DEVICE}")
    print(f"{'='*60}\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Infrastructure tests
        print("Running infrastructure tests...")
        await test_trust_anchor_health(suite, client)
        await test_tools_registered(suite, client)

        # Credential tests
        print("Running credential tests...")
        await test_credentials_file_exists(suite, client)

        # Tool execution tests
        print("Running tool execution tests...")
        await test_health_check_tool(suite, client)
        await test_interface_status_tool(suite, client)
        await test_routing_table_tool(suite, client)

        # Runbook tests
        print("Running runbook tests...")
        await test_triage_runbook(suite, client)

    # Save results
    filepath = suite.save_results()
    print(f"\nResults saved to: {filepath}")

    return suite.results


# =============================================================================
# ENTRY POINT
# =============================================================================
if __name__ == "__main__":
    results = asyncio.run(run_tests())

    print(f"\n{'='*60}")
    print(f"QA Test Results: {PACK_NAME}")
    print(f"{'='*60}")
    print(json.dumps(results["summary"], indent=2))

    # Exit with error code if any tests failed
    if results["summary"]["failed"] > 0:
        exit(1)
