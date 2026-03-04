#!/usr/bin/env python3
"""
SD-WAN Workflow Pre-Execution Hook

This hook validates that the agent has completed the required prerequisites
before executing SD-WAN workflow tools.

Hook is triggered via Claude Code hooks system before tool execution.
Returns exit code 0 to allow execution, non-zero to block.

Usage:
  python validate_prerequisites.py --tool-id <canonical_id> --session-file <path>

The session file should contain the agent's process log output.
"""

import argparse
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Tools that require prerequisite validation
SDWAN_WORKFLOW_TOOLS = [
    "org.ulysses.sdwan.kvm-fortios-provision",
    "org.ulysses.provisioning.fortigate-sdwan-spoke-template",
    "org.ulysses.noc.fortigate-health-check",
    "org.ulysses.noc.fortigate-cli-execute",
    "org.ulysses.noc.fortigate-ssh",
    "org.ulysses.noc.fortigate-config-push",
    "org.ulysses.sdwan.fortigate-sdwan-member",
]

# Required files that must be read
REQUIRED_FILES = [
    "Skills.md",
    "BASELINE_TEMPLATE.yaml",
    "BLOCK_0_BLUEPRINT_WIZARD.yaml",
]

# Expected preflight values
EXPECTED_PREFLIGHT = {
    "loopback_name": "Spoke-Lo",
    "tunnel_names": ["HUB1-VPN1", "HUB1-VPN2"],
    "sdwan_zone": "SDWAN_OVERLAY",
    "health_check": "HUB_Health",
    "ike_tcp_port": 11443,
    "transport": "udp",
    "min_kvm_provision_version": "1.0.11",
    "min_spoke_template_version": "1.3.0",
}


def parse_process_log(session_content: str) -> dict:
    """Extract process log from session content."""
    # Look for process_log YAML block in the session
    import re

    # Find process_log section
    match = re.search(r'process_log:\s*\n((?:  .*\n)+)', session_content)
    if not match:
        return {}

    # Simple YAML-like parsing (avoid external dependencies)
    log_text = match.group(0)
    result = {
        "files_read": [],
        "mcp_checks": [],
        "preflight_confirmed": {},
        "ready_to_proceed": False
    }

    # Check for files_read section
    if "skills_md:" in log_text:
        result["files_read"].append("Skills.md")
    if "baseline_template:" in log_text:
        result["files_read"].append("BASELINE_TEMPLATE.yaml")
    if "block_0:" in log_text:
        result["files_read"].append("BLOCK_0_BLUEPRINT_WIZARD.yaml")

    # Check for preflight values
    for key in EXPECTED_PREFLIGHT.keys():
        if f"{key}:" in log_text:
            result["preflight_confirmed"][key] = True

    # Check ready_to_proceed
    if "ready_to_proceed: true" in log_text.lower():
        result["ready_to_proceed"] = True

    return result


def validate_prerequisites(tool_id: str, session_file: str = None) -> tuple[bool, str]:
    """
    Validate that prerequisites are met before tool execution.

    Returns:
        (allowed: bool, message: str)
    """
    # Check if this tool requires validation
    tool_base = tool_id.split("/")[0] if "/" in tool_id else tool_id

    requires_validation = any(
        tool_base.startswith(t) or t in tool_base
        for t in SDWAN_WORKFLOW_TOOLS
    )

    if not requires_validation:
        return True, f"Tool {tool_id} does not require SD-WAN workflow validation"

    # If session file provided, check for process log
    if session_file and os.path.exists(session_file):
        with open(session_file, 'r') as f:
            session_content = f.read()

        process_log = parse_process_log(session_content)

        # Validate files were read
        missing_files = [f for f in REQUIRED_FILES if f not in process_log.get("files_read", [])]
        if missing_files:
            return False, f"BLOCKED: Missing required file reads: {missing_files}. Read Skills.md first."

        # Validate preflight was confirmed
        if not process_log.get("preflight_confirmed"):
            return False, "BLOCKED: Preflight checklist not confirmed. Complete process_log first."

        # Validate ready_to_proceed
        if not process_log.get("ready_to_proceed"):
            return False, "BLOCKED: ready_to_proceed not set to true. Complete all prerequisites."

        return True, f"Prerequisites validated for {tool_id}"

    # No session file - check environment variable fallback
    prereqs_confirmed = os.environ.get("SDWAN_PREREQS_CONFIRMED", "false")
    if prereqs_confirmed.lower() == "true":
        return True, f"Prerequisites confirmed via environment variable for {tool_id}"

    # Default: Block execution and require prerequisites
    return False, f"""
BLOCKED: SD-WAN Workflow Prerequisites Not Met

Before executing {tool_id}, you MUST complete these steps:

1. Read Skills.md (the workflow guide)
2. Read BASELINE_TEMPLATE.yaml (naming constants)
3. Read BLOCK_0_BLUEPRINT_WIZARD.yaml (parameters)
4. Call list_certified_tools() to verify versions
5. Call list_accessible_devices() to verify credentials
6. Output your process_log confirming all prerequisites

See: solution_packs/fortigate-ops/workflows/add-sdwan-site/Skills.md

Set SDWAN_PREREQS_CONFIRMED=true in your environment if using manual override.
"""


def main():
    parser = argparse.ArgumentParser(description="SD-WAN Workflow Pre-Execution Hook")
    parser.add_argument("--tool-id", required=True, help="Tool canonical ID")
    parser.add_argument("--session-file", help="Path to session transcript file")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of text")

    args = parser.parse_args()

    allowed, message = validate_prerequisites(args.tool_id, args.session_file)

    if args.json:
        print(json.dumps({
            "allowed": allowed,
            "message": message,
            "tool_id": args.tool_id,
            "timestamp": datetime.now().isoformat()
        }))
    else:
        print(message)

    sys.exit(0 if allowed else 1)


if __name__ == "__main__":
    main()
