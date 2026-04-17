#!/usr/bin/env python3
from __future__ import annotations
"""
FortiWeb IP Intelligence Baseline Tool

Blocks known-bad IPs using FortiGuard threat intel:
  Botnet, Anonymous Proxy, Phishing, Spam, Others, Tor

Architecture:
  Global flag (cmdb/waf/ip-intelligence-flag) — master on/off
  Category table (cmdb/waf/ip-intelligence) — per-category action
  Profile toggle (protection-profile.ip-intelligence) — per-profile enable

Baseline:
  Week 1: All categories at 'alert' (monitor only) — establish baseline
  Week 2+: Promote Botnet, Phishing, Spam to 'alert_deny'
           Leave Anonymous Proxy and Tor at 'alert' (VPN users are often legit)
"""

import sys
import json
import base64
import urllib.request
import urllib.error
import ssl
from typing import Any, Optional
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "sdk"))
from fortiweb_client import FortiWebClient, FortiWebAPIError, load_credentials


CATEGORIES = {
    "1": "Botnet",
    "2": "Anonymous Proxy",
    "3": "Phishing",
    "4": "Spam",
    "5": "Others",
    "6": "Tor",
}

# Block these categories (rarely legitimate)
BLOCK_CATEGORIES = {"1", "3", "4"}  # Botnet, Phishing, Spam

# Alert only (VPN users often legitimate)
MONITOR_CATEGORIES = {"2", "5", "6"}  # Anonymous Proxy, Others, Tor


def _put_singleton(client: FortiWebClient, endpoint: str, data: dict) -> None:
    """PUT on a singleton endpoint (no mkey)."""
    creds = load_credentials(client.host)
    token = base64.b64encode(json.dumps({
        "username": creds["username"],
        "password": creds["password"],
        "vdom": client.vdom,
    }).encode()).decode()

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    url = f"https://{client.host}/api/v2.0/{endpoint}"
    payload = json.dumps({"data": data}).encode()
    req = urllib.request.Request(url, method="PUT", data=payload)
    req.add_header("Authorization", token)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")

    with urllib.request.urlopen(req, timeout=client.timeout, context=ctx):
        pass


def run_audit(client: FortiWebClient, profile_name: str) -> dict:
    findings = []
    check = 1

    # Global flag
    r = client.get("cmdb/waf/ip-intelligence-flag")
    flag = r.get("results", {}).get("flag", "disable")
    if flag == "enable":
        findings.append({"check": check, "name": "global_flag", "status": "PASS",
                         "detail": "IP Intelligence global flag enabled"})
    else:
        findings.append({"check": check, "name": "global_flag", "status": "FAIL",
                         "detail": "IP Intelligence global flag DISABLED — no IP checks happen"})
    check += 1

    # Profile toggle
    try:
        r = client.get("cmdb/waf/web-protection-profile.inline-protection",
                        extra_params={"mkey": profile_name})
        pp = r.get("results", {})
        profile_ip = pp.get("ip-intelligence", "disable")
        if profile_ip == "enable":
            findings.append({"check": check, "name": "profile_toggle", "status": "PASS",
                             "detail": f"IP Intelligence enabled on profile '{profile_name}'"})
        else:
            findings.append({"check": check, "name": "profile_toggle", "status": "FAIL",
                             "detail": f"IP Intelligence disabled on profile '{profile_name}'"})
    except FortiWebAPIError:
        findings.append({"check": check, "name": "profile_toggle", "status": "FAIL",
                         "detail": f"Profile '{profile_name}' not found"})
    check += 1

    # Category actions
    r = client.get("cmdb/waf/ip-intelligence")
    for cat in r.get("results", []):
        cid = str(cat.get("id", ""))
        name = CATEGORIES.get(cid, f"unknown({cid})")
        status = cat.get("status", "disable")
        action = cat.get("action", "alert")

        if status != "enable":
            findings.append({"check": check, "name": f"category_{name}", "status": "FAIL",
                             "detail": f"{name}: category DISABLED"})
        elif cid in BLOCK_CATEGORIES:
            if action in ("alert_deny", "deny_no_log", "block-period"):
                findings.append({"check": check, "name": f"category_{name}", "status": "PASS",
                                 "detail": f"{name}: blocking ({action})"})
            else:
                findings.append({"check": check, "name": f"category_{name}", "status": "WARN",
                                 "detail": f"{name}: action={action} (recommend blocking — rarely legit)"})
        else:
            if action == "alert":
                findings.append({"check": check, "name": f"category_{name}", "status": "PASS",
                                 "detail": f"{name}: alert only (VPN/Tor — blocking could affect real users)"})
            else:
                findings.append({"check": check, "name": f"category_{name}", "status": "PASS",
                                 "detail": f"{name}: {action}"})
        check += 1

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


def run_apply(client: FortiWebClient, profile_name: str, mode: str) -> dict:
    """Apply IP Intelligence baseline.

    mode='monitor' → all categories at 'alert'
    mode='block'   → block categories at 'alert_deny', monitor at 'alert'
    """
    updated = []

    # Enable global flag
    _put_singleton(client, "cmdb/waf/ip-intelligence-flag", {"flag": "enable"})
    updated.append({"type": "global_flag", "value": "enable"})

    # Enable on protection profile
    try:
        client.put("cmdb/waf/web-protection-profile.inline-protection",
                    {"ip-intelligence": "enable"}, mkey=profile_name)
        updated.append({"type": "profile_toggle", "profile": profile_name, "value": "enable"})
    except FortiWebAPIError as e:
        return {"success": False, "action": f"apply-{mode}", "error": f"Failed enabling on profile: {e}"}

    # Set category actions
    for cid, name in CATEGORIES.items():
        if mode == "block" and cid in BLOCK_CATEGORIES:
            action = "alert_deny"
        else:
            action = "alert"

        try:
            client.put("cmdb/waf/ip-intelligence", {
                "status": "enable",
                "action": action,
                "severity": "High",
                "block-period": 600,
            }, mkey=cid)
            updated.append({"type": "category", "id": cid, "name": name, "action": action})
        except FortiWebAPIError as e:
            return {"success": False, "action": f"apply-{mode}",
                    "error": f"Failed updating {name}: {e}", "updated": updated}

    audit_result = run_audit(client, profile_name)

    return {
        "success": True,
        "action": f"apply-{mode}",
        "updated_objects": updated,
        "audit": audit_result,
        "message": f"IP Intelligence applied in {mode} mode. "
                   + ("Monitor logs for 2 weeks before promoting to block." if mode == "monitor"
                      else "Botnet, Phishing, Spam blocking enabled. Anonymous Proxy and Tor still at alert."),
    }


def run_status(client: FortiWebClient, profile_name: str) -> dict:
    r = client.get("cmdb/waf/ip-intelligence-flag")
    flag = r.get("results", {}).get("flag", "disable")

    try:
        r = client.get("cmdb/waf/web-protection-profile.inline-protection",
                        extra_params={"mkey": profile_name})
        profile_ip = r.get("results", {}).get("ip-intelligence", "disable")
    except FortiWebAPIError:
        profile_ip = "profile not found"

    categories = []
    r = client.get("cmdb/waf/ip-intelligence")
    for cat in r.get("results", []):
        cid = str(cat.get("id", ""))
        categories.append({
            "id": cid,
            "name": CATEGORIES.get(cid, "unknown"),
            "status": cat.get("status", "?"),
            "action": cat.get("action", "?"),
        })

    blocking_count = sum(1 for c in categories if c["action"] in ("alert_deny", "deny_no_log", "block-period"))
    alerting_count = sum(1 for c in categories if c["action"] == "alert")

    if flag == "enable" and profile_ip == "enable" and blocking_count >= 3:
        posture = "GOOD"
    elif flag == "enable" and profile_ip == "enable":
        posture = "PARTIAL (monitor mode)"
    else:
        posture = "WEAK"

    return {
        "success": True,
        "action": "status",
        "profile": profile_name,
        "global_flag": flag,
        "profile_toggle": profile_ip,
        "categories": categories,
        "blocking_count": blocking_count,
        "alerting_count": alerting_count,
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
        elif action == "apply-monitor":
            result.update(run_apply(client, profile_name, "monitor"))
        elif action == "apply-block":
            result.update(run_apply(client, profile_name, "block"))
        elif action == "status":
            result.update(run_status(client, profile_name))
        else:
            return {"success": False,
                    "error": f"Unknown action: {action}. Use: audit, apply-monitor, apply-block, status"}
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
