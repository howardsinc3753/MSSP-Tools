#!/usr/bin/env python3
from __future__ import annotations
"""
FortiWeb JSON Protection Baseline Tool

Validates JSON request bodies. Essential for REST API protection.

Architecture:
  JSON rule (cmdb/waf/json-validation.rule) — per-URL limits + action
  JSON policy (cmdb/waf/json-validation.policy) — container + signatures flag
  Protection profile (json-validation-policy field) — activation point

Baseline:
  - Match all paths (^/.*) initially, tune per-endpoint later
  - Max body: 10 MB (tune per app)
  - Max depth: 32 levels
  - Max keys: 1000
  - Attack signatures ON — runs WAF signatures inside JSON values
  - Action: alert_deny
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
    "request-type": "regular",
    "request-file": "^/.*",
    "action": "alert_deny",
    "severity": "High",
    "block-period": 600,
    "json-limits": "enable",
    "key-size": 1024,
    "key-number": 1000,
    "value-size": 10240,
    "value-number": 10000,
    "value-number-in-array": 10000,
    "object-depth": 32,
}


def run_audit(client: FortiWebClient, profile_name: str) -> dict:
    findings = []
    check = 1

    # Check profile has JSON policy attached
    try:
        r = client.get("cmdb/waf/web-protection-profile.inline-protection",
                        extra_params={"mkey": profile_name})
        pp = r.get("results", {})
    except FortiWebAPIError:
        return {"success": True, "action": "audit",
                "score": "0/1", "pass": 0, "fail": 1, "warn": 0,
                "findings": [{"check": 1, "name": "profile", "status": "FAIL",
                              "detail": f"Profile '{profile_name}' not found"}]}

    json_policy = pp.get("json-validation-policy", "")
    if not json_policy:
        findings.append({"check": check, "name": "policy_attached", "status": "FAIL",
                         "detail": "No JSON validation policy attached to profile"})
        return _build_result(findings, profile_name)

    findings.append({"check": check, "name": "policy_attached", "status": "PASS",
                     "detail": f"JSON policy: '{json_policy}'"})
    check += 1

    # Check policy config
    try:
        r = client.get("cmdb/waf/json-validation.policy",
                        extra_params={"mkey": json_policy})
        policy = r.get("results", {})
    except FortiWebAPIError:
        findings.append({"check": check, "name": "policy_readable", "status": "FAIL",
                         "detail": f"Could not read policy '{json_policy}'"})
        return _build_result(findings, profile_name)

    sigs = policy.get("enable-attack-signatures", "disable")
    if sigs == "enable":
        findings.append({"check": check, "name": "attack_signatures", "status": "PASS",
                         "detail": "Attack signatures run on JSON content"})
    else:
        findings.append({"check": check, "name": "attack_signatures", "status": "FAIL",
                         "detail": "Attack signatures DISABLED — SQLi/XSS in JSON bypass WAF"})
    check += 1

    # Check rule count
    rules_attached = policy.get("input-rule-list", [])
    sz = policy.get("sz_input-rule-list", 0)
    if rules_attached or sz > 0:
        findings.append({"check": check, "name": "rules_attached", "status": "PASS",
                         "detail": f"{sz or len(rules_attached)} rules attached to policy"})
    else:
        findings.append({"check": check, "name": "rules_attached", "status": "WARN",
                         "detail": "No rules attached — policy exists but doesn't match any URLs (may need GUI config)"})

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
              max_body_kb: int, max_depth: int, max_keys: int) -> dict:
    """Create JSON protection baseline.

    Creates:
    1. Rule with baseline limits (matches all paths)
    2. Policy with attack signatures enabled
    3. Wires policy into protection profile
    """
    created = []
    rule_name = f"{bp_prefix}-JSON-Rule"
    policy_name = f"{bp_prefix}-JSON-Protection"

    # Check existence
    r = client.get("cmdb/waf/json-validation.rule")
    existing_rules = [p.get("name", "") for p in r.get("results", [])]
    r = client.get("cmdb/waf/json-validation.policy")
    existing_policies = [p.get("name", "") for p in r.get("results", [])]

    if rule_name in existing_rules:
        return {"success": False, "action": "apply",
                "error": f"Rule '{rule_name}' already exists. Delete or use different bp_prefix."}
    if policy_name in existing_policies:
        return {"success": False, "action": "apply",
                "error": f"Policy '{policy_name}' already exists. Delete or use different bp_prefix."}

    # Step 1: Create rule
    try:
        rule_config = {**BASELINE_RULE_FIELDS, "name": rule_name,
                       "json-data-size": max_body_kb,
                       "object-depth": max_depth,
                       "key-number": max_keys}
        client.post("cmdb/waf/json-validation.rule", rule_config)
        created.append({"type": "json_rule", "name": rule_name,
                        "max_body_kb": max_body_kb, "max_depth": max_depth})
    except FortiWebAPIError as e:
        return {"success": False, "action": "apply",
                "error": f"Failed creating rule: {e}"}

    # Step 2: Create policy
    try:
        client.post("cmdb/waf/json-validation.policy", {
            "name": policy_name,
            "enable-attack-signatures": "enable",
        })
        created.append({"type": "json_policy", "name": policy_name,
                        "attack_signatures": "enable"})
    except FortiWebAPIError as e:
        return {"success": False, "action": "apply",
                "error": f"Failed creating policy: {e}", "created_objects": created}

    # Step 3: Wire into profile
    wire_profile = _find_wire_target(client, bp_prefix, profile_name)
    if wire_profile:
        try:
            client.put("cmdb/waf/web-protection-profile.inline-protection",
                        {"json-validation-policy": policy_name}, mkey=wire_profile)
            created.append({"type": "profile_update", "name": wire_profile,
                            "field": "json-validation-policy"})
        except FortiWebAPIError:
            pass

    audit_result = run_audit(client, wire_profile) if wire_profile else None

    return {
        "success": True,
        "action": "apply",
        "created_objects": created,
        "audit": audit_result,
        "message": f"Created '{policy_name}' with rule '{rule_name}' "
                   + (f"and wired into '{wire_profile}'." if wire_profile
                      else "— assign to protection profile manually.")
                   + " NOTE: Rule must be attached to policy via GUI "
                   "(Advanced Protection > JSON Protection > [policy] > Add Rule).",
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

    json_policy = pp.get("json-validation-policy", "")
    policy_detail = {}
    if json_policy:
        try:
            r = client.get("cmdb/waf/json-validation.policy",
                            extra_params={"mkey": json_policy})
            p = r.get("results", {})
            policy_detail = {
                "attack_signatures": p.get("enable-attack-signatures", "?"),
                "rule_count": p.get("sz_input-rule-list", 0),
            }
        except FortiWebAPIError:
            pass

    if json_policy and policy_detail.get("attack_signatures") == "enable":
        posture = "GOOD"
    elif json_policy:
        posture = "PARTIAL"
    else:
        posture = "WEAK"

    return {
        "success": True,
        "action": "status",
        "profile": profile_name,
        "json_policy": json_policy or "(none)",
        "policy_detail": policy_detail,
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
    max_body_kb = args.get("max_body_kb", 10240)
    max_depth = args.get("max_depth", 32)
    max_keys = args.get("max_keys", 1000)
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
                                     max_body_kb, max_depth, max_keys))
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
