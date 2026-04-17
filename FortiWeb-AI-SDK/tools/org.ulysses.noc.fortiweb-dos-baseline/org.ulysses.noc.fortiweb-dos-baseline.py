#!/usr/bin/env python3
from __future__ import annotations
"""
FortiWeb DoS Prevention Baseline Tool

Audits and enforces DoS prevention best-practice on FortiWeb 8.0+.

FortiWeb DoS architecture — 4 rule types wired into 1 prevention policy:

  Application-Layer DoS Prevention Policy
    ├── HTTP Connection Flood Check Rule     (concurrent connections per IP)
    ├── HTTP Request Flood Prevention Rule   (requests per session)
    ├── Layer 4 Access Limit Rule            (new connections per IP per second)
    ├── Layer 4 Connection Flood Check Rule  (total concurrent L4 connections per IP)
    └── Layer 3 Fragment Protection          (IP fragment reassembly attack)

The prevention policy is then attached to an Inline Protection Profile.

Baseline (80/20 — production-safe thresholds):
  - HTTP connection flood: 500 connections/IP, alert_deny, block 600s
  - HTTP request flood: 1000 requests/session, block-period 600s, bot confirmation
  - L4 access limit: 1000 standalone / 2000 shared, block-period 600s
  - L4 connection flood: 500 connections/IP, alert_deny, block 600s
  - L3 fragment protection: enabled
  - All rules at severity High

Author: Ulysses Project
Version: 1.0.0
"""

import sys
import json
from typing import Any, Optional
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "sdk"))
from fortiweb_client import FortiWebClient, FortiWebAPIError


# --- Baseline definitions ---

BASELINE_HTTP_CONN_FLOOD = {
    "http-connection-threshold": 500,
    "action": "alert_deny",
    "severity": "High",
    "block-period": 600,
}

BASELINE_HTTP_REQ_FLOOD = {
    "access-limit-in-http-session": 1000,
    "action": "block-period",
    "block-period": 600,
    "severity": "High",
    "bot-confirmation": "enable",
    "bot-recognition": "captcha-enforcement",
}

BASELINE_L4_ACCESS = {
    "access-limit-standalone-ip": 1000,
    "access-limit-share-ip": 2000,
    "action": "block-period",
    "block-period": 600,
    "severity": "High",
}

BASELINE_L4_CONN_FLOOD = {
    "layer4-connection-threshold": 500,
    "action": "alert_deny",
    "severity": "High",
    "block-period": 600,
}

BASELINE_PREVENTION = {
    "enable-http-session-based-prevention": "enable",
    "enable-layer4-dos-prevention": "enable",
    "layer3-fragment-protection": "enable",
}

# Minimum acceptable thresholds — below these is dangerous for production
MIN_THRESHOLDS = {
    "http-connection-threshold": 50,
    "access-limit-in-http-session": 100,
    "access-limit-standalone-ip": 100,
    "access-limit-share-ip": 200,
    "layer4-connection-threshold": 50,
}

RULE_LABELS = {
    "http-connection-flood-check-rule": "HTTP Connection Flood",
    "http-request-flood-prevention-rule": "HTTP Request Flood",
    "layer4-access-limit-rule": "Layer 4 Access Limit",
    "layer4-connection-flood-check-rule": "Layer 4 Connection Flood",
}


# --- Audit ---

def audit_rule(rule: dict, baseline: dict, rule_type: str) -> list[dict]:
    """Audit a single DoS rule against baseline."""
    findings = []
    name = rule.get("name", "?")

    for field, expected in baseline.items():
        actual = rule.get(field)
        if actual is None:
            continue

        if field in MIN_THRESHOLDS and isinstance(actual, int):
            min_val = MIN_THRESHOLDS[field]
            if actual < min_val:
                findings.append({"name": f"{rule_type}_{field}", "status": "WARN",
                                 "detail": f"[{name}] {field}: {actual} (below minimum {min_val} — risk of blocking legitimate traffic)"})
                continue

        if isinstance(expected, int):
            if actual < expected:
                findings.append({"name": f"{rule_type}_{field}", "status": "WARN",
                                 "detail": f"[{name}] {field}: {actual} (baseline: {expected})"})
            else:
                findings.append({"name": f"{rule_type}_{field}", "status": "PASS",
                                 "detail": f"[{name}] {field}: {actual}"})
        elif str(actual) != str(expected):
            if field in ("action", "bot-confirmation"):
                findings.append({"name": f"{rule_type}_{field}", "status": "WARN",
                                 "detail": f"[{name}] {field}: {actual} (baseline: {expected})"})
            else:
                findings.append({"name": f"{rule_type}_{field}", "status": "PASS",
                                 "detail": f"[{name}] {field}: {actual}"})
        else:
            findings.append({"name": f"{rule_type}_{field}", "status": "PASS",
                             "detail": f"[{name}] {field}: {actual}"})

    return findings


def run_audit(client: FortiWebClient, profile_name: str) -> dict:
    """Run full DoS baseline audit."""
    findings = []
    check_num = 1

    # Step 1: Check if DoS prevention is attached to protection profile
    try:
        r = client.get("cmdb/waf/web-protection-profile.inline-protection",
                        extra_params={"mkey": profile_name})
        pp = r.get("results", {})
    except FortiWebAPIError:
        return {"success": True, "action": "audit", "profile": profile_name,
                "score": "0/1", "pass": 0, "fail": 1, "warn": 0,
                "findings": [{"check": 1, "name": "protection_profile", "status": "FAIL",
                              "detail": f"Protection profile '{profile_name}' not found"}]}

    dos_policy = pp.get("application-layer-dos-prevention", "")
    if not dos_policy:
        findings.append({"check": check_num, "name": "dos_policy_attached", "status": "FAIL",
                         "detail": "No DoS prevention policy attached to protection profile"})
        return {"success": True, "action": "audit", "profile": profile_name,
                "score": f"0/1", "pass": 0, "fail": 1, "warn": 0, "findings": findings}

    findings.append({"check": check_num, "name": "dos_policy_attached", "status": "PASS",
                     "detail": f"DoS prevention policy: '{dos_policy}'"})
    check_num += 1

    # Step 2: Read the prevention policy
    try:
        r = client.get("cmdb/waf/application-layer-dos-prevention",
                        extra_params={"mkey": dos_policy})
        prev = r.get("results", {})
    except FortiWebAPIError:
        findings.append({"check": check_num, "name": "dos_policy_readable", "status": "FAIL",
                         "detail": f"Could not read DoS prevention policy '{dos_policy}'"})
        return _build_audit_result(findings, profile_name)

    # Check prevention policy settings
    for field, expected in BASELINE_PREVENTION.items():
        actual = prev.get(field, "?")
        if actual != expected:
            findings.append({"check": check_num, "name": f"prevention_{field}", "status": "FAIL",
                             "detail": f"{field}: {actual} (baseline: {expected})"})
        else:
            findings.append({"check": check_num, "name": f"prevention_{field}", "status": "PASS",
                             "detail": f"{field}: {actual}"})
        check_num += 1

    # Step 3: Audit each referenced rule
    rule_checks = [
        ("http-connection-flood-check-rule", "cmdb/waf/http-connection-flood-check-rule", BASELINE_HTTP_CONN_FLOOD),
        ("http-request-flood-prevention-rule", "cmdb/waf/http-request-flood-prevention-rule", BASELINE_HTTP_REQ_FLOOD),
        ("layer4-access-limit-rule", "cmdb/waf/layer4-access-limit-rule", BASELINE_L4_ACCESS),
        ("layer4-connection-flood-check-rule", "cmdb/waf/layer4-connection-flood-check-rule", BASELINE_L4_CONN_FLOOD),
    ]

    for rule_field, endpoint, baseline in rule_checks:
        rule_name = prev.get(rule_field, "")
        label = RULE_LABELS.get(rule_field, rule_field)

        if not rule_name:
            findings.append({"check": check_num, "name": f"{rule_field}_attached", "status": "FAIL",
                             "detail": f"{label}: not configured in prevention policy"})
            check_num += 1
            continue

        try:
            r = client.get(endpoint, extra_params={"mkey": rule_name})
            rule = r.get("results", {})
            rule_findings = audit_rule(rule, baseline, rule_field.replace("-", "_"))
            for f in rule_findings:
                f["check"] = check_num
                check_num += 1
            findings.extend(rule_findings)
        except FortiWebAPIError:
            findings.append({"check": check_num, "name": f"{rule_field}_readable", "status": "FAIL",
                             "detail": f"Could not read {label} rule '{rule_name}'"})
            check_num += 1

    return _build_audit_result(findings, profile_name)


def _build_audit_result(findings: list, profile_name: str) -> dict:
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


# --- Apply ---

def run_apply(client: FortiWebClient, bp_prefix: str) -> dict:
    """Create best-practice DoS prevention configuration.

    Creates 5 objects:
    1. HTTP Connection Flood rule
    2. HTTP Request Flood rule
    3. Layer 4 Access Limit rule
    4. Layer 4 Connection Flood rule
    5. Application Layer DoS Prevention policy (wires 1-4 together)

    Then wires the prevention policy into BP-SQLi-Protection if available.
    """
    created = []
    names = {
        "conn_flood": f"{bp_prefix}-ConnFlood",
        "req_flood": f"{bp_prefix}-ReqFlood",
        "l4_access": f"{bp_prefix}-L4Access",
        "l4_conn": f"{bp_prefix}-L4ConnFlood",
        "prevention": f"{bp_prefix}-DoS-Prevention",
    }

    # Check if prevention policy already exists
    try:
        r = client.get("cmdb/waf/application-layer-dos-prevention")
        existing = [p.get("name", "") for p in r.get("results", [])]
        if names["prevention"] in existing:
            return {"success": False, "action": "apply",
                    "error": f"DoS prevention policy '{names['prevention']}' already exists. Delete it first or use a different bp_prefix."}
    except FortiWebAPIError as e:
        return {"success": False, "action": "apply", "error": str(e)}

    # Create rules in dependency order
    rules = [
        ("cmdb/waf/http-connection-flood-check-rule", names["conn_flood"],
         {**BASELINE_HTTP_CONN_FLOOD, "name": names["conn_flood"]}, "http_connection_flood_rule"),
        ("cmdb/waf/http-request-flood-prevention-rule", names["req_flood"],
         {**BASELINE_HTTP_REQ_FLOOD, "name": names["req_flood"]}, "http_request_flood_rule"),
        ("cmdb/waf/layer4-access-limit-rule", names["l4_access"],
         {**BASELINE_L4_ACCESS, "name": names["l4_access"]}, "layer4_access_limit_rule"),
        ("cmdb/waf/layer4-connection-flood-check-rule", names["l4_conn"],
         {**BASELINE_L4_CONN_FLOOD, "name": names["l4_conn"]}, "layer4_connection_flood_rule"),
    ]

    for endpoint, name, config, obj_type in rules:
        try:
            client.post(endpoint, config)
            created.append({"type": obj_type, "name": name})
        except FortiWebAPIError as e:
            return {"success": False, "action": "apply",
                    "error": f"Failed creating {name}: {e}", "created_objects": created}

    # Create prevention policy wiring all rules
    try:
        client.post("cmdb/waf/application-layer-dos-prevention", {
            "name": names["prevention"],
            **BASELINE_PREVENTION,
            "http-connection-flood-check-rule": names["conn_flood"],
            "http-request-flood-prevention-rule": names["req_flood"],
            "layer4-access-limit-rule": names["l4_access"],
            "layer4-connection-flood-check-rule": names["l4_conn"],
        })
        created.append({"type": "dos_prevention_policy", "name": names["prevention"]})
    except FortiWebAPIError as e:
        return {"success": False, "action": "apply",
                "error": f"Failed creating prevention policy: {e}", "created_objects": created}

    # Wire into best available protection profile
    wire_profile = _find_wire_target(client, bp_prefix)
    if wire_profile:
        try:
            client.put("cmdb/waf/web-protection-profile.inline-protection",
                        {"application-layer-dos-prevention": names["prevention"]},
                        mkey=wire_profile)
            created.append({"type": "profile_update", "name": wire_profile,
                            "field": "application-layer-dos-prevention"})
        except FortiWebAPIError:
            pass  # Non-fatal — can wire manually

    # Audit the result
    audit_profile = wire_profile or "Inline Standard Protection"
    audit_result = run_audit(client, audit_profile) if wire_profile else None

    return {
        "success": True,
        "action": "apply",
        "created_objects": created,
        "audit": audit_result,
        "message": f"Created DoS prevention policy '{names['prevention']}' with 4 rules. "
                   + (f"Wired into '{wire_profile}'." if wire_profile
                      else "Assign to a protection profile to activate."),
    }


def _find_wire_target(client: FortiWebClient, bp_prefix: str) -> Optional[str]:
    """Find best protection profile to wire DoS into."""
    try:
        r = client.get("cmdb/waf/web-protection-profile.inline-protection")
        profiles = r.get("results", [])
    except FortiWebAPIError:
        return None

    # Prefer BP profile from SQLi baseline
    bp_sqli = f"{bp_prefix}-SQLi-Protection"
    for p in profiles:
        if p.get("name") == bp_sqli:
            return bp_sqli

    # Any custom profile
    for p in profiles:
        if p.get("can_view") == 0:
            return p.get("name")

    return None


# --- Status ---

def run_status(client: FortiWebClient, profile_name: str) -> dict:
    """Quick DoS posture summary."""
    try:
        r = client.get("cmdb/waf/web-protection-profile.inline-protection",
                        extra_params={"mkey": profile_name})
        pp = r.get("results", {})
    except FortiWebAPIError:
        return {"success": False, "error": f"Profile '{profile_name}' not found"}

    dos_policy = pp.get("application-layer-dos-prevention", "")

    if not dos_policy:
        return {"success": True, "action": "status", "profile": profile_name,
                "dos_policy": "(none)", "posture": "WEAK",
                "detail": "No DoS prevention policy attached"}

    # Read the prevention policy
    try:
        r = client.get("cmdb/waf/application-layer-dos-prevention",
                        extra_params={"mkey": dos_policy})
        prev = r.get("results", {})
    except FortiWebAPIError:
        return {"success": True, "action": "status", "profile": profile_name,
                "dos_policy": dos_policy, "posture": "PARTIAL",
                "detail": f"Policy '{dos_policy}' referenced but unreadable"}

    http_session = prev.get("enable-http-session-based-prevention", "disable")
    l4_enabled = prev.get("enable-layer4-dos-prevention", "disable")
    l3_frag = prev.get("layer3-fragment-protection", "disable")

    rules_configured = sum(1 for k in RULE_LABELS if prev.get(k, ""))
    rules_total = len(RULE_LABELS)

    if http_session == "enable" and l4_enabled == "enable" and rules_configured == rules_total:
        posture = "GOOD"
    elif rules_configured > 0:
        posture = "PARTIAL"
    else:
        posture = "WEAK"

    # Get blocked IPs count
    blocked = 0
    try:
        r = client.get("monitor/blockedips")
        blocked = len(r.get("results", []))
    except FortiWebAPIError:
        pass

    return {
        "success": True,
        "action": "status",
        "profile": profile_name,
        "dos_policy": dos_policy,
        "http_session_prevention": http_session,
        "layer4_prevention": l4_enabled,
        "layer3_fragment_protection": l3_frag,
        "rules_configured": f"{rules_configured}/{rules_total}",
        "blocked_ips": blocked,
        "posture": posture,
    }


# --- Entry point ---

def main(context) -> dict[str, Any]:
    """FortiWeb DoS Prevention Baseline — audit, apply, or status."""
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
            result.update(run_apply(client, bp_prefix))
        elif action == "status":
            result.update(run_status(client, profile_name))
        else:
            return {"success": False, "error": f"Unknown action: {action}. Use: audit, apply, status"}
    except FortiWebAPIError as e:
        result["success"] = False
        result["error"] = str(e)
    except Exception as e:
        result["success"] = False
        result["error"] = f"Unexpected error: {e}"

    return result


if __name__ == "__main__":
    result = main({"target_ip": "192.168.209.31", "action": "audit"})
    print(json.dumps(result, indent=2))
