#!/usr/bin/env python3
from __future__ import annotations
"""
FortiWeb SQLi Baseline Tool

Audits and enforces SQL Injection best-practice configuration on FortiWeb 8.0+.

Three actions:
  audit  — Read-only: check current config against baseline, report gaps
  apply  — Write: create best-practice signature + SBD + protection profile
  status — Quick read-only summary of current SQLi posture

Baseline definition (80/20 rule):
  Layer 1 — Signatures: SQLi/XSS/Generic at alert_deny, FPM enabled
  Layer 2 — SBD: All 6 SQL engines enabled at alert_deny
  Layer 3 — Protection Profile: Both sig + SBD attached

Author: Ulysses Project
Version: 1.0.0
"""

import sys
import os
import json
from typing import Any, Optional
from pathlib import Path

# Add SDK to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "sdk"))
from fortiweb_client import FortiWebClient, FortiWebAPIError, load_credentials


# --- Baseline definitions ---

# Signature classes that MUST be enabled at alert_deny for 80/20
BASELINE_SIG_CLASSES = {
    "010000000": {"name": "Cross Site Scripting", "action": "alert_deny", "fpm": "enable", "severity": "High"},
    "030000000": {"name": "SQL Injection",        "action": "alert_deny", "fpm": "enable", "severity": "High"},
    "050000000": {"name": "Generic Attacks",       "action": "alert_deny", "fpm": "enable", "severity": "High"},
    "090000000": {"name": "Known Exploits",        "action": "alert_deny", "fpm": "disable", "severity": "High"},
}

# Signature classes that should be enabled at alert (monitor, not block)
BASELINE_SIG_MONITOR = {
    "070000000": {"name": "Trojans",               "action": "alert", "severity": "Medium"},
    "080000000": {"name": "Information Disclosure", "action": "alert", "severity": "Low"},
}

# SBD SQL engines — all must be enabled at alert_deny
SBD_SQL_ENGINES = [
    "sql-stacked-queries",
    "sql-embeded-queries",
    "sql-condition-based",
    "sql-arithmetic-operation",
    "sql-line-comments",
    "sql-function-based",
]

# Wizard DB/server IDs for creating sig profiles
WIZARD_ALL_DBS = "101,102,103,104,105,106"
WIZARD_COMMON_SERVERS = "201,202,203,207"  # IIS, Apache, Tomcat, Nginx


# --- Audit checks ---

def audit_signatures(client: FortiWebClient, profile_name: str) -> list[dict]:
    """Check signature profile against baseline."""
    findings = []

    # Find which sig profile is attached to the protection profile
    try:
        r = client.get("cmdb/waf/web-protection-profile.inline-protection",
                        extra_params={"mkey": profile_name})
        sig_rule = r.get("results", {}).get("signature-rule", "")
    except FortiWebAPIError:
        return [{"check": 1, "name": "protection_profile_exists", "status": "FAIL",
                 "detail": f"Protection profile '{profile_name}' not found"}]

    if not sig_rule:
        findings.append({"check": 1, "name": "sig_profile_attached", "status": "FAIL",
                         "detail": "No signature profile attached to protection profile"})
        return findings

    findings.append({"check": 1, "name": "sig_profile_attached", "status": "PASS",
                     "detail": f"Signature profile: '{sig_rule}'"})

    # Get class-level detail from monitor API
    r = client.get("waf/signatures")
    sig_profile = None
    for p in r.get("results", []):
        if p["name"] == sig_rule:
            sig_profile = p
            break

    if not sig_profile:
        findings.append({"check": 2, "name": "sig_profile_readable", "status": "FAIL",
                         "detail": f"Could not read signature profile '{sig_rule}'"})
        return findings

    # Check each baseline class
    class_map = {}
    for mc in sig_profile.get("main_class_list", []):
        class_map[mc.get("main_class_id", "")] = mc

    check_num = 2
    for class_id, baseline in BASELINE_SIG_CLASSES.items():
        mc = class_map.get(class_id)
        if not mc:
            findings.append({"check": check_num, "name": f"sig_{baseline['name']}", "status": "FAIL",
                             "detail": f"{baseline['name']} class not found in profile"})
        elif mc.get("status") != "enable":
            findings.append({"check": check_num, "name": f"sig_{baseline['name']}", "status": "FAIL",
                             "detail": f"{baseline['name']}: DISABLED (should be enabled)"})
        elif mc.get("action") != baseline["action"]:
            findings.append({"check": check_num, "name": f"sig_{baseline['name']}", "status": "WARN",
                             "detail": f"{baseline['name']}: action={mc['action']} (baseline: {baseline['action']})"})
        elif baseline.get("fpm") == "enable" and mc.get("fpm-status") != "enable":
            findings.append({"check": check_num, "name": f"sig_{baseline['name']}", "status": "WARN",
                             "detail": f"{baseline['name']}: FPM disabled (baseline: enabled)"})
        else:
            findings.append({"check": check_num, "name": f"sig_{baseline['name']}", "status": "PASS",
                             "detail": f"{baseline['name']}: {mc['action']}, fpm={mc.get('fpm-status','?')}"})
        check_num += 1

    # Check disabled/alertonly/fpm counts
    disabled = sig_profile.get("signatureDisabledCount", 0)
    alert_only = sig_profile.get("alertOnlyCount", 0)
    fpm_disabled = sig_profile.get("fpmDisableCount", 0)

    if alert_only > 0:
        findings.append({"check": check_num, "name": "alert_only_count", "status": "WARN",
                         "detail": f"{alert_only} signatures set to alert-only (not blocking)"})
    else:
        findings.append({"check": check_num, "name": "alert_only_count", "status": "PASS",
                         "detail": "No signatures downgraded to alert-only"})
    check_num += 1

    if fpm_disabled > 0:
        findings.append({"check": check_num, "name": "fpm_disabled_count", "status": "WARN",
                         "detail": f"{fpm_disabled} signatures have FPM disabled"})
    else:
        findings.append({"check": check_num, "name": "fpm_disabled_count", "status": "PASS",
                         "detail": "FPM enabled for all applicable signatures"})
    check_num += 1

    # Check FortiGuard auto-update
    try:
        r = client.get("cmdb/waf/signature_update_policy")
        update_status = r.get("results", {}).get("status", "disable")
        if update_status == "enable":
            findings.append({"check": check_num, "name": "fortiguard_autoupdate", "status": "PASS",
                             "detail": "FortiGuard signature auto-update enabled"})
        else:
            findings.append({"check": check_num, "name": "fortiguard_autoupdate", "status": "FAIL",
                             "detail": "FortiGuard signature auto-update DISABLED"})
    except FortiWebAPIError:
        findings.append({"check": check_num, "name": "fortiguard_autoupdate", "status": "WARN",
                         "detail": "Could not read FortiGuard update policy"})

    return findings


def audit_sbd(client: FortiWebClient, profile_name: str) -> list[dict]:
    """Check SBD profile against baseline."""
    findings = []
    check_base = 20

    # Get SBD reference from protection profile
    r = client.get("cmdb/waf/web-protection-profile.inline-protection",
                    extra_params={"mkey": profile_name})
    sbd_rule = r.get("results", {}).get("syntax-based-attack-detection", "")

    if not sbd_rule:
        findings.append({"check": check_base, "name": "sbd_attached", "status": "FAIL",
                         "detail": "SBD profile NOT attached to protection profile — obfuscated SQLi will bypass signatures"})
        return findings

    findings.append({"check": check_base, "name": "sbd_attached", "status": "PASS",
                     "detail": f"SBD profile: '{sbd_rule}'"})

    # Read SBD config
    try:
        r = client.get("cmdb/waf/syntax-based-attack-detection",
                        extra_params={"mkey": sbd_rule})
        sbd = r.get("results", {})
    except FortiWebAPIError:
        findings.append({"check": check_base + 1, "name": "sbd_readable", "status": "FAIL",
                         "detail": f"Could not read SBD profile '{sbd_rule}'"})
        return findings

    # Check each SQL engine
    check_num = check_base + 1
    all_engines_ok = True
    for engine in SBD_SQL_ENGINES:
        status = sbd.get(f"{engine}-status", "disable")
        action = sbd.get(f"{engine}-action", "alert")
        engine_label = engine.replace("sql-", "").replace("-", " ").title()

        if status != "enable":
            findings.append({"check": check_num, "name": f"sbd_{engine}", "status": "FAIL",
                             "detail": f"SBD {engine_label}: DISABLED"})
            all_engines_ok = False
        elif action != "alert_deny":
            findings.append({"check": check_num, "name": f"sbd_{engine}", "status": "WARN",
                             "detail": f"SBD {engine_label}: action={action} (baseline: alert_deny)"})
            all_engines_ok = False
        check_num += 1

    if all_engines_ok:
        # Collapse to single PASS if all 6 are good
        findings = [f for f in findings if not f["name"].startswith("sbd_sql-")]
        findings.append({"check": check_base + 1, "name": "sbd_all_sql_engines", "status": "PASS",
                         "detail": "All 6 SQL SBD engines enabled at alert_deny"})
        check_num = check_base + 2

    # Check detection targets
    det_target = sbd.get("detection-target-sql", "")
    required_targets = ["ARGS_NAMES", "ARGS_VALUE", "REQUEST_COOKIES"]
    missing = [t for t in required_targets if t not in det_target]
    if missing:
        findings.append({"check": check_num, "name": "sbd_detection_targets", "status": "FAIL",
                         "detail": f"Missing SQL detection targets: {', '.join(missing)}"})
    else:
        findings.append({"check": check_num, "name": "sbd_detection_targets", "status": "PASS",
                         "detail": f"SQL detection targets: {det_target.strip()}"})
    check_num += 1

    # Check detection templates
    det_template = sbd.get("sql-detection-template", "")
    required_templates = ["SINGLE_QUOTE", "DOUBLE_QUOTE", "AS_IS"]
    missing = [t for t in required_templates if t not in det_template]
    if missing:
        findings.append({"check": check_num, "name": "sbd_detection_templates", "status": "WARN",
                         "detail": f"Missing SQL detection templates: {', '.join(missing)}"})
    else:
        findings.append({"check": check_num, "name": "sbd_detection_templates", "status": "PASS",
                         "detail": f"SQL detection templates: {det_template.strip()}"})

    return findings


def audit_attack_log(client: FortiWebClient) -> list[dict]:
    """Check attack log for recent SQLi activity."""
    findings = []
    try:
        r = client.get("log/logaccess.attack")
        total = r.get("total", 0)
        findings.append({"check": 30, "name": "attack_log", "status": "PASS",
                         "detail": f"Attack log accessible — {total} total entries"})
    except FortiWebAPIError:
        findings.append({"check": 30, "name": "attack_log", "status": "WARN",
                         "detail": "Could not read attack log"})
    return findings


def run_audit(client: FortiWebClient, profile_name: str) -> dict:
    """Run full SQLi baseline audit."""
    all_findings = []
    all_findings.extend(audit_signatures(client, profile_name))
    all_findings.extend(audit_sbd(client, profile_name))
    all_findings.extend(audit_attack_log(client))

    passes = sum(1 for f in all_findings if f["status"] == "PASS")
    total = len(all_findings)
    fails = sum(1 for f in all_findings if f["status"] == "FAIL")

    return {
        "success": True,
        "action": "audit",
        "profile": profile_name,
        "score": f"{passes}/{total}",
        "pass": passes,
        "fail": fails,
        "warn": sum(1 for f in all_findings if f["status"] == "WARN"),
        "findings": all_findings,
    }


# --- Apply ---

def run_apply(client: FortiWebClient, bp_prefix: str) -> dict:
    """Create best-practice SQLi configuration.

    Creates:
    1. Signature profile via wizard (with all DBs + common web servers)
    2. Protection profile with sig + SBD wired together
    """
    created = []
    sig_name = f"{bp_prefix}-SQLi-Signatures"
    profile_name = f"{bp_prefix}-SQLi-Protection"

    # Step 1: Create signature profile via wizard
    try:
        # Check if it already exists
        r = client.get("waf/signatures")
        existing = [p["name"] for p in r.get("results", [])]
        if sig_name in existing:
            return {"success": False, "action": "apply",
                    "error": f"Signature profile '{sig_name}' already exists. Delete it first or use a different bp_prefix."}

        # Wizard POST — creates profile with class hierarchy configured
        # Note: wizard returns errcode 1 but actually succeeds
        import urllib.request
        import urllib.error
        import urllib.parse
        import ssl
        import base64

        creds = load_credentials(client.host)
        auth_token = base64.b64encode(json.dumps({
            "username": creds["username"],
            "password": creds["password"],
            "vdom": client.vdom,
        }).encode()).decode()

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        url = f"https://{client.host}/api/v2.0/waf/signature.wizard"
        payload = json.dumps({
            "signature_name": sig_name,
            "database": WIZARD_ALL_DBS,
            "web_server": WIZARD_COMMON_SERVERS,
            "web_app": "",
            "script_lang": "",
        }).encode()

        req = urllib.request.Request(url, method="POST", data=payload)
        req.add_header("Accept", "application/json")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", auth_token)

        try:
            with urllib.request.urlopen(req, timeout=client.timeout, context=ctx) as resp:
                resp.read()
        except urllib.error.HTTPError:
            pass  # Wizard returns 500/errcode 1 but actually creates the profile

        # Verify it was created
        r = client.get("waf/signatures")
        sig_created = False
        for p in r.get("results", []):
            if p["name"] == sig_name:
                sig_created = True
                sqli_class = None
                for mc in p.get("main_class_list", []):
                    if mc.get("main_class_id") == "030000000":
                        sqli_class = mc
                        break
                created.append({
                    "type": "signature_profile",
                    "name": sig_name,
                    "sqli_status": sqli_class.get("status", "?") if sqli_class else "NOT FOUND",
                    "sqli_action": sqli_class.get("action", "?") if sqli_class else "NOT FOUND",
                    "sqli_fpm": sqli_class.get("fpm-status", "?") if sqli_class else "NOT FOUND",
                    "enabled_classes": p.get("mainClassEnabledCount", 0),
                })
                break

        if not sig_created:
            return {"success": False, "action": "apply",
                    "error": f"Failed to create signature profile '{sig_name}' via wizard"}

    except Exception as e:
        return {"success": False, "action": "apply",
                "error": f"Failed creating signature profile: {e}"}

    # Step 2: Create protection profile with sig + SBD wired
    try:
        existing_profiles = client.get("cmdb/waf/web-protection-profile.inline-protection")
        existing_names = [p.get("name", "") for p in existing_profiles.get("results", [])]
        if profile_name in existing_names:
            return {"success": False, "action": "apply",
                    "error": f"Protection profile '{profile_name}' already exists. Delete it first or use a different bp_prefix.",
                    "created_objects": created}

        r = client.post("cmdb/waf/web-protection-profile.inline-protection", {
            "name": profile_name,
            "signature-rule": sig_name,
            "syntax-based-attack-detection": "Standard Protection",
            "comment": f"Best Practice SQLi baseline — created by FortiWeb SDK",
        })
        created.append({
            "type": "protection_profile",
            "name": profile_name,
            "signature_rule": sig_name,
            "sbd_rule": "Standard Protection",
        })
    except FortiWebAPIError as e:
        return {"success": False, "action": "apply",
                "error": f"Failed creating protection profile: {e}",
                "created_objects": created}

    # Step 3: Run audit on the newly created profile to verify
    audit_result = run_audit(client, profile_name)

    return {
        "success": True,
        "action": "apply",
        "created_objects": created,
        "audit": audit_result,
        "message": f"Created '{profile_name}' with signature profile '{sig_name}' + SBD 'Standard Protection'. "
                   f"Assign this protection profile to your server policy to activate.",
    }


# --- Status ---

def run_status(client: FortiWebClient, profile_name: str) -> dict:
    """Quick SQLi posture summary."""
    try:
        r = client.get("cmdb/waf/web-protection-profile.inline-protection",
                        extra_params={"mkey": profile_name})
        pp = r.get("results", {})
    except FortiWebAPIError:
        return {"success": False, "error": f"Profile '{profile_name}' not found"}

    sig_rule = pp.get("signature-rule", "")
    sbd_rule = pp.get("syntax-based-attack-detection", "")

    # Get sig class details
    sqli_status = "UNKNOWN"
    sqli_action = "UNKNOWN"
    sqli_fpm = "UNKNOWN"
    enabled_classes = 0

    if sig_rule:
        r = client.get("waf/signatures")
        for p in r.get("results", []):
            if p["name"] == sig_rule:
                enabled_classes = p.get("mainClassEnabledCount", 0)
                for mc in p.get("main_class_list", []):
                    if mc.get("main_class_id") == "030000000":
                        sqli_status = mc.get("status", "?")
                        sqli_action = mc.get("action", "?")
                        sqli_fpm = mc.get("fpm-status", "?")
                        break
                break

    # Get SBD engine count
    sbd_engines_ok = 0
    if sbd_rule:
        try:
            r = client.get("cmdb/waf/syntax-based-attack-detection",
                            extra_params={"mkey": sbd_rule})
            sbd_config = r.get("results", {})
            for eng in SBD_SQL_ENGINES:
                if (sbd_config.get(f"{eng}-status") == "enable" and
                        sbd_config.get(f"{eng}-action") == "alert_deny"):
                    sbd_engines_ok += 1
        except FortiWebAPIError:
            pass

    # FortiGuard
    try:
        r = client.get("cmdb/waf/signature_update_policy")
        fg_update = r.get("results", {}).get("status", "unknown")
    except FortiWebAPIError:
        fg_update = "unknown"

    return {
        "success": True,
        "action": "status",
        "profile": profile_name,
        "signature_profile": sig_rule or "(none)",
        "sbd_profile": sbd_rule or "(none)",
        "sqli_signatures": {
            "status": sqli_status,
            "action": sqli_action,
            "fpm": sqli_fpm,
        },
        "sbd_sql_engines": f"{sbd_engines_ok}/{len(SBD_SQL_ENGINES)} at alert_deny",
        "sig_classes_enabled": enabled_classes,
        "fortiguard_autoupdate": fg_update,
        "posture": "GOOD" if (sqli_action == "alert_deny" and sbd_engines_ok == 6 and sbd_rule) else
                   "PARTIAL" if sqli_action == "alert_deny" else "WEAK",
    }


# --- Entry point ---

def main(context) -> dict[str, Any]:
    """FortiWeb SQLi Baseline — audit, apply, or status."""
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
