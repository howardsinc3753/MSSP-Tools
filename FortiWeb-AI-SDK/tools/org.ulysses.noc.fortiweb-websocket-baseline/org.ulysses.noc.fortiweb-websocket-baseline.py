#!/usr/bin/env python3
from __future__ import annotations
"""
FortiWeb WebSocket Security Baseline Tool

Protects WebSocket connections (Socket.IO, native WS). Without this FortiWeb
may mishandle WebSocket upgrades and break real-time features.

Architecture:
  WS rule (cmdb/waf/websocket-security.rule) — per-URL config
  WS policy (cmdb/waf/websocket-security.policy) — container
  Protection profile (websocket-security-policy field) — activation

Baseline:
  - Don't block WebSocket traffic (block-websocket-traffic: disable)
  - Run attack signatures inside WS frames (enable-attack-signatures: enable)
  - Max frame: 64 KB, max message: 16 MB
  - Allow both plain text and binary frames (Socket.IO uses both)
  - Action on violation: alert_deny
"""

import sys
import json
from typing import Any
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "sdk"))
from fortiweb_client import FortiWebClient, FortiWebAPIError


BASELINE_RULE_FIELDS = {
    "host-status": "disable",
    "host": "",
    "url-type": "regular",
    "block-websocket-traffic": "disable",
    "action": "alert_deny",
    "block-extensions": "disable",
    "enable-attack-signatures": "enable",
    "allow-plain-text": "enable",
    "allow-binary-text": "enable",
}


def run_audit(client: FortiWebClient, profile_name: str) -> dict:
    findings = []
    check = 1

    try:
        r = client.get("cmdb/waf/web-protection-profile.inline-protection",
                        extra_params={"mkey": profile_name})
        pp = r.get("results", {})
    except FortiWebAPIError:
        return {"success": True, "action": "audit",
                "score": "0/1", "pass": 0, "fail": 1, "warn": 0,
                "findings": [{"check": 1, "name": "profile", "status": "FAIL",
                              "detail": f"Profile '{profile_name}' not found"}]}

    ws_policy = pp.get("websocket-security-policy", "")
    if not ws_policy:
        findings.append({"check": check, "name": "policy_attached", "status": "WARN",
                         "detail": "No WebSocket policy attached (OK if app doesn't use WebSockets)"})
        return _build_result(findings, profile_name)

    findings.append({"check": check, "name": "policy_attached", "status": "PASS",
                     "detail": f"WebSocket policy: '{ws_policy}'"})
    check += 1

    # Check rules exist (sub-table on policy)
    try:
        r = client.get("cmdb/waf/websocket-security.policy",
                        extra_params={"mkey": ws_policy})
        policy = r.get("results", {})
        rule_count = policy.get("sz_rule-list", 0)
        if rule_count > 0:
            findings.append({"check": check, "name": "rules_attached", "status": "PASS",
                             "detail": f"{rule_count} rules attached to policy"})
        else:
            findings.append({"check": check, "name": "rules_attached", "status": "WARN",
                             "detail": "No rules attached — may need GUI config"})
    except FortiWebAPIError:
        findings.append({"check": check, "name": "policy_readable", "status": "FAIL",
                         "detail": f"Could not read policy '{ws_policy}'"})

    return _build_result(findings, profile_name)


def _build_result(findings: list, profile_name: str) -> dict:
    passes = sum(1 for f in findings if f["status"] == "PASS")
    return {
        "success": True,
        "action": "audit",
        "profile": profile_name,
        "score": f"{passes}/{len(findings)}",
        "pass": passes,
        "fail": sum(1 for f in findings if f["status"] == "FAIL"),
        "warn": sum(1 for f in findings if f["status"] == "WARN"),
        "findings": findings,
    }


def run_apply(client: FortiWebClient, bp_prefix: str, profile_name: str,
              ws_path: str, max_frame_size: int, max_message_size: int) -> dict:
    created = []
    rule_name = f"{bp_prefix}-WebSocket-Rule"
    policy_name = f"{bp_prefix}-WebSocket-Protection"

    # Check existence
    r = client.get("cmdb/waf/websocket-security.rule")
    existing_rules = [p.get("name", "") for p in r.get("results", [])]
    r = client.get("cmdb/waf/websocket-security.policy")
    existing_policies = [p.get("name", "") for p in r.get("results", [])]

    if rule_name in existing_rules:
        return {"success": False, "action": "apply",
                "error": f"Rule '{rule_name}' already exists."}
    if policy_name in existing_policies:
        return {"success": False, "action": "apply",
                "error": f"Policy '{policy_name}' already exists."}

    # Create rule
    try:
        rule_config = {**BASELINE_RULE_FIELDS, "name": rule_name,
                       "url": ws_path,
                       "max-frame-size": max_frame_size,
                       "max-message-size": max_message_size}
        client.post("cmdb/waf/websocket-security.rule", rule_config)
        created.append({"type": "websocket_rule", "name": rule_name,
                        "url": ws_path, "max_frame_size": max_frame_size})
    except FortiWebAPIError as e:
        return {"success": False, "action": "apply",
                "error": f"Failed creating rule: {e}"}

    # Create policy
    try:
        client.post("cmdb/waf/websocket-security.policy", {"name": policy_name})
        created.append({"type": "websocket_policy", "name": policy_name})
    except FortiWebAPIError as e:
        return {"success": False, "action": "apply",
                "error": f"Failed creating policy: {e}", "created_objects": created}

    # Wire into profile
    wire_profile = _find_wire_target(client, bp_prefix, profile_name)
    if wire_profile:
        try:
            client.put("cmdb/waf/web-protection-profile.inline-protection",
                        {"websocket-security-policy": policy_name}, mkey=wire_profile)
            created.append({"type": "profile_update", "name": wire_profile,
                            "field": "websocket-security-policy"})
        except FortiWebAPIError:
            pass

    audit_result = run_audit(client, wire_profile) if wire_profile else None

    return {
        "success": True,
        "action": "apply",
        "created_objects": created,
        "audit": audit_result,
        "message": f"Created '{policy_name}' with rule '{rule_name}' matching '{ws_path}' "
                   + (f"and wired into '{wire_profile}'." if wire_profile else "")
                   + " NOTE: Rule must be attached to policy via GUI "
                   "(API Protection > WebSocket Security > [policy] > Add Rule).",
    }


def _find_wire_target(client: FortiWebClient, bp_prefix: str, profile_name: str):
    try:
        r = client.get("cmdb/waf/web-protection-profile.inline-protection")
        profiles = r.get("results", [])
    except FortiWebAPIError:
        return None

    bp_sqli = f"{bp_prefix}-SQLi-Protection"
    for p in profiles:
        if p.get("name") == bp_sqli:
            return bp_sqli
    for p in profiles:
        if p.get("name") == profile_name and p.get("can_view") == 0:
            return profile_name
    for p in profiles:
        if p.get("can_view") == 0:
            return p.get("name")
    return None


def run_status(client: FortiWebClient, profile_name: str) -> dict:
    try:
        r = client.get("cmdb/waf/web-protection-profile.inline-protection",
                        extra_params={"mkey": profile_name})
        pp = r.get("results", {})
    except FortiWebAPIError:
        return {"success": False, "error": f"Profile '{profile_name}' not found"}

    ws_policy = pp.get("websocket-security-policy", "")

    if ws_policy:
        posture = "GOOD"
        try:
            r = client.get("cmdb/waf/websocket-security.policy",
                            extra_params={"mkey": ws_policy})
            rule_count = r.get("results", {}).get("sz_rule-list", 0)
        except FortiWebAPIError:
            rule_count = 0
    else:
        posture = "NOT_CONFIGURED"
        rule_count = 0

    return {
        "success": True,
        "action": "status",
        "profile": profile_name,
        "websocket_policy": ws_policy or "(none)",
        "rule_count": rule_count,
        "posture": posture,
    }


def main(context) -> dict[str, Any]:
    if hasattr(context, "parameters"):
        args = context.parameters
        creds = getattr(context, "credentials", None)
    else:
        args = context
        creds = None

    target_ip = args.get("target_ip")
    action = args.get("action", "status")
    profile_name = args.get("profile_name", "Inline Standard Protection")
    bp_prefix = args.get("bp_prefix", "BP")
    ws_path = args.get("ws_path", "^/.*")
    max_frame_size = args.get("max_frame_size", 65536)
    max_message_size = args.get("max_message_size", 16777216)
    timeout = args.get("timeout", 30)
    verify_ssl = args.get("verify_ssl", False)

    if not target_ip:
        return {"success": False, "error": "target_ip is required"}

    try:
        client = FortiWebClient.from_credentials(
            target_ip, context_creds=creds,
            verify_ssl=verify_ssl, timeout=timeout
        )
    except ValueError as e:
        return {"success": False, "error": str(e)}

    result = {"target_ip": target_ip}

    try:
        if action == "audit":
            result.update(run_audit(client, profile_name))
        elif action == "apply":
            result.update(run_apply(client, bp_prefix, profile_name,
                                     ws_path, max_frame_size, max_message_size))
        elif action == "status":
            result.update(run_status(client, profile_name))
        else:
            return {"success": False,
                    "error": f"Unknown action: {action}. Use: audit, apply, status"}
    except FortiWebAPIError as e:
        result["success"] = False
        result["error"] = str(e)
    except Exception as e:
        result["success"] = False
        result["error"] = f"Unexpected error: {e}"

    return result


if __name__ == "__main__":
    result = main({"target_ip": "192.168.209.31", "action": "audit",
                   "profile_name": "BP-SQLi-Protection"})
    print(json.dumps(result, indent=2))
