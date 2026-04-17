#!/usr/bin/env python3
from __future__ import annotations
"""
FortiWeb Cookie Security Baseline Tool

Audits and enforces cookie security best-practice on FortiWeb 8.0+.

Three actions:
  audit  — Read-only: check current config against baseline, report gaps
  apply  — Write: create best-practice cookie security policy and wire into profile
  status — Quick read-only summary of current cookie security posture

Baseline definition (80/20 rule):
  - Cookie signing (tamper detection) enabled
  - Secure flag enforced (HTTPS-only cookies)
  - HttpOnly flag enforced (blocks JS access, mitigates XSS cookie theft)
  - SameSite=Lax (CSRF protection without breaking OAuth/SSO flows)
  - Suspicious cookies rejected
  - Session cookie (cookiesession1) for stickiness/affinity
  - Bot mitigation policy wired in (known bot classification)

Author: Ulysses Project
Version: 1.0.0
"""

import sys
import json
from typing import Any, Optional
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "sdk"))
from fortiweb_client import FortiWebClient, FortiWebAPIError, load_credentials


# --- Baseline definitions ---

BASELINE_COOKIE = {
    "security-mode": "signed",
    "secure-cookie": "enable",
    "http-only": "enable",
    "samesite": "enable",
    "samesite-value": "Lax",
    "action": "alert_deny",
    "block-period": 600,
    "severity": "High",
    "allow-suspicious-cookies": "Never",
}

BASELINE_COOKIE_LABELS = {
    "security-mode": "Cookie tamper detection (signing)",
    "secure-cookie": "Secure flag (HTTPS-only cookies)",
    "http-only": "HttpOnly flag (blocks JS access)",
    "samesite": "SameSite attribute enabled",
    "samesite-value": "SameSite value",
    "action": "Action on tampering",
    "block-period": "Block period (seconds)",
    "severity": "Log severity",
    "allow-suspicious-cookies": "Suspicious cookie handling",
}

# Session cookie baseline
BASELINE_SESSION = {
    "http-session-cookie": "enable",
}

# Bot mitigation — we check if any policy is wired, don't enforce a specific one
BOT_FIELD = "bot-mitigate-policy"


# --- Audit ---

def audit_cookie_policy(client: FortiWebClient, profile_name: str) -> list[dict]:
    """Check cookie security policy against baseline."""
    findings = []
    check_num = 1

    # Step 1: Read protection profile
    try:
        r = client.get("cmdb/waf/web-protection-profile.inline-protection",
                        extra_params={"mkey": profile_name})
        pp = r.get("results", {})
    except FortiWebAPIError:
        return [{"check": 1, "name": "protection_profile", "status": "FAIL",
                 "detail": f"Protection profile '{profile_name}' not found"}]

    cookie_policy = pp.get("cookie-security-policy", "")

    if not cookie_policy:
        findings.append({"check": check_num, "name": "cookie_policy_attached", "status": "FAIL",
                         "detail": "No cookie security policy attached to protection profile"})
        check_num += 1

        # Still check session cookie and bot mitigation
        findings.extend(_audit_session_and_bot(pp, check_num))
        return findings

    findings.append({"check": check_num, "name": "cookie_policy_attached", "status": "PASS",
                     "detail": f"Cookie security policy: '{cookie_policy}'"})
    check_num += 1

    # Step 2: Read the cookie security policy
    try:
        r = client.get("cmdb/waf/cookie-security",
                        extra_params={"mkey": cookie_policy})
        cs = r.get("results", {})
    except FortiWebAPIError:
        findings.append({"check": check_num, "name": "cookie_policy_readable", "status": "FAIL",
                         "detail": f"Could not read cookie policy '{cookie_policy}'"})
        return findings

    # Step 3: Check each baseline field
    for field, expected in BASELINE_COOKIE.items():
        actual = cs.get(field)
        label = BASELINE_COOKIE_LABELS.get(field, field)

        if actual is None:
            findings.append({"check": check_num, "name": f"cookie_{field}", "status": "WARN",
                             "detail": f"{label}: field not found in response"})
        elif str(actual) != str(expected):
            if field == "block-period" or field == "severity":
                # Non-critical deviations
                findings.append({"check": check_num, "name": f"cookie_{field}", "status": "WARN",
                                 "detail": f"{label}: {actual} (baseline: {expected})"})
            else:
                findings.append({"check": check_num, "name": f"cookie_{field}", "status": "FAIL",
                                 "detail": f"{label}: {actual} (baseline: {expected})"})
        else:
            findings.append({"check": check_num, "name": f"cookie_{field}", "status": "PASS",
                             "detail": f"{label}: {actual}"})
        check_num += 1

    # Step 4: Check exception list
    exceptions = cs.get("cookie-security-exception-list", [])
    if exceptions:
        findings.append({"check": check_num, "name": "cookie_exceptions", "status": "WARN",
                         "detail": f"{len(exceptions)} cookie exception(s) configured — review if still needed"})
    else:
        findings.append({"check": check_num, "name": "cookie_exceptions", "status": "PASS",
                         "detail": "No cookie exceptions configured"})
    check_num += 1

    # Step 5: Session cookie and bot
    findings.extend(_audit_session_and_bot(pp, check_num))

    return findings


def _audit_session_and_bot(pp: dict, check_num: int) -> list[dict]:
    """Audit session cookie and bot mitigation fields on protection profile."""
    findings = []

    # Session cookie (FortiWeb's cookiesession1 for stickiness/affinity)
    session_cookie = pp.get("http-session-cookie", "disable")
    if session_cookie == "enable":
        timeout = pp.get("http-session-timeout", 365)
        findings.append({"check": check_num, "name": "session_cookie", "status": "PASS",
                         "detail": f"Session cookie (cookiesession1) enabled, timeout={timeout} days"})
    else:
        findings.append({"check": check_num, "name": "session_cookie", "status": "WARN",
                         "detail": "Session cookie (cookiesession1) disabled — no session-level tracking for cookie security or user tracking"})
    check_num += 1

    # Bot mitigation policy
    bot_policy = pp.get(BOT_FIELD, "")
    if bot_policy:
        findings.append({"check": check_num, "name": "bot_mitigate_policy", "status": "PASS",
                         "detail": f"Bot mitigation policy: '{bot_policy}'"})
    else:
        findings.append({"check": check_num, "name": "bot_mitigate_policy", "status": "WARN",
                         "detail": "No bot mitigation policy attached — bot-injected cookies won't be classified"})

    return findings


def run_audit(client: FortiWebClient, profile_name: str) -> dict:
    """Run full cookie security baseline audit."""
    findings = audit_cookie_policy(client, profile_name)

    passes = sum(1 for f in findings if f["status"] == "PASS")
    total = len(findings)
    fails = sum(1 for f in findings if f["status"] == "FAIL")

    return {
        "success": True,
        "action": "audit",
        "profile": profile_name,
        "score": f"{passes}/{total}",
        "pass": passes,
        "fail": fails,
        "warn": sum(1 for f in findings if f["status"] == "WARN"),
        "findings": findings,
    }


# --- Apply ---

def run_apply(client: FortiWebClient, bp_prefix: str, target_profile: str) -> dict:
    """Create best-practice cookie security configuration.

    Creates:
    1. Cookie security policy with baseline settings
    2. Wires it into the target protection profile (or BP-SQLi-Protection if exists)
    Also enables session cookie and wires bot mitigation if not already set.
    """
    created = []
    cookie_name = f"{bp_prefix}-Cookie-Security"

    # Check if already exists
    try:
        r = client.get("cmdb/waf/cookie-security")
        existing = [p.get("name", "") for p in r.get("results", [])]
        if cookie_name in existing:
            return {"success": False, "action": "apply",
                    "error": f"Cookie policy '{cookie_name}' already exists. Delete it first or use a different bp_prefix."}
    except FortiWebAPIError as e:
        return {"success": False, "action": "apply", "error": str(e)}

    # Step 1: Create cookie security policy
    try:
        r = client.post("cmdb/waf/cookie-security", {
            "name": cookie_name,
            **BASELINE_COOKIE,
        })
        created.append({
            "type": "cookie_security_policy",
            "name": cookie_name,
            "settings": BASELINE_COOKIE,
        })
    except FortiWebAPIError as e:
        return {"success": False, "action": "apply",
                "error": f"Failed creating cookie policy: {e}"}

    # Step 2: Find the best protection profile to wire into
    wire_profile = _find_wire_target(client, bp_prefix, target_profile)
    if not wire_profile:
        return {"success": True, "action": "apply",
                "created_objects": created,
                "message": f"Created '{cookie_name}' but no writable protection profile found. "
                           f"Assign it manually via: protection profile > cookie-security-policy = '{cookie_name}'"}

    # Step 3: Wire cookie policy + enable session cookie + wire bot mitigation
    try:
        update_fields = {"cookie-security-policy": cookie_name}

        # Enable session cookie if not already
        r = client.get("cmdb/waf/web-protection-profile.inline-protection",
                        extra_params={"mkey": wire_profile})
        pp = r.get("results", {})

        if pp.get("http-session-cookie") != "enable":
            update_fields["http-session-cookie"] = "enable"
            update_fields["http-session-timeout"] = 365

        # Wire bot mitigation if not already set
        if not pp.get(BOT_FIELD):
            update_fields[BOT_FIELD] = "Predefined - Bot Mitigation"

        client.put("cmdb/waf/web-protection-profile.inline-protection",
                    update_fields, mkey=wire_profile)

        created.append({
            "type": "profile_update",
            "name": wire_profile,
            "fields_set": list(update_fields.keys()),
        })
    except FortiWebAPIError as e:
        return {"success": True, "action": "apply",
                "created_objects": created,
                "message": f"Created '{cookie_name}' but failed to wire into '{wire_profile}': {e}. Wire it manually."}

    # Step 4: Audit the wired profile
    audit_result = run_audit(client, wire_profile)

    return {
        "success": True,
        "action": "apply",
        "created_objects": created,
        "audit": audit_result,
        "message": f"Created '{cookie_name}' and wired into '{wire_profile}' with session cookie enabled and bot mitigation attached.",
    }


def _find_wire_target(client: FortiWebClient, bp_prefix: str, target_profile: str) -> Optional[str]:
    """Find the best protection profile to wire into.

    Priority:
    1. BP-prefixed profile from SQLi baseline (e.g., BP-SQLi-Protection)
    2. Explicitly provided target_profile if it's custom (editable)
    3. None if only predefined profiles exist
    """
    try:
        r = client.get("cmdb/waf/web-protection-profile.inline-protection")
        profiles = r.get("results", [])
    except FortiWebAPIError:
        return None

    # Look for our BP profile first
    bp_sqli = f"{bp_prefix}-SQLi-Protection"
    for p in profiles:
        if p.get("name") == bp_sqli:
            return bp_sqli

    # Try the target profile — but only if it's custom (can_view=0 means custom)
    for p in profiles:
        if p.get("name") == target_profile and p.get("can_view") == 0:
            return target_profile

    # Look for any custom profile
    for p in profiles:
        if p.get("can_view") == 0:
            return p.get("name")

    return None


# --- Status ---

def run_status(client: FortiWebClient, profile_name: str) -> dict:
    """Quick cookie security posture summary."""
    try:
        r = client.get("cmdb/waf/web-protection-profile.inline-protection",
                        extra_params={"mkey": profile_name})
        pp = r.get("results", {})
    except FortiWebAPIError:
        return {"success": False, "error": f"Profile '{profile_name}' not found"}

    cookie_policy = pp.get("cookie-security-policy", "")
    session_cookie = pp.get("http-session-cookie", "disable")
    bot_policy = pp.get(BOT_FIELD, "")

    cookie_detail = {}
    if cookie_policy:
        try:
            r = client.get("cmdb/waf/cookie-security",
                            extra_params={"mkey": cookie_policy})
            cs = r.get("results", {})
            cookie_detail = {
                "security_mode": cs.get("security-mode", "?"),
                "secure_flag": cs.get("secure-cookie", "?"),
                "httponly_flag": cs.get("http-only", "?"),
                "samesite": f"{cs.get('samesite', '?')} ({cs.get('samesite-value', '?')})",
                "action": cs.get("action", "?"),
                "suspicious_cookies": cs.get("allow-suspicious-cookies", "?"),
            }
        except FortiWebAPIError:
            cookie_detail = {"error": "Could not read policy"}

    # Determine posture
    if not cookie_policy:
        posture = "WEAK"
    elif cookie_detail.get("security_mode") in ("signed", "encrypted") and \
         cookie_detail.get("secure_flag") == "enable" and \
         cookie_detail.get("httponly_flag") == "enable":
        posture = "GOOD"
    else:
        posture = "PARTIAL"

    return {
        "success": True,
        "action": "status",
        "profile": profile_name,
        "cookie_policy": cookie_policy or "(none)",
        "cookie_settings": cookie_detail if cookie_detail else "(not configured)",
        "session_cookie": session_cookie,
        "bot_mitigate_policy": bot_policy or "(none)",
        "posture": posture,
    }


# --- Entry point ---

def main(context) -> dict[str, Any]:
    """FortiWeb Cookie Security Baseline — audit, apply, or status."""
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
            result.update(run_apply(client, bp_prefix, profile_name))
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
