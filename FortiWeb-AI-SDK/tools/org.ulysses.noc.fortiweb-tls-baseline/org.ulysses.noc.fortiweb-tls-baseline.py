#!/usr/bin/env python3
from __future__ import annotations
"""
FortiWeb TLS Cipher Baseline Tool

Audits and enforces TLS/cipher best-practice on FortiWeb 8.0+.

Three actions:
  audit  — Check cipher groups + server policies for weak TLS config
  apply  — Create hardened cipher group (Mozilla-Intermediate equivalent)
  status — Quick TLS posture summary across all cipher groups

Baseline (Mozilla-Intermediate equivalent):
  - TLS 1.0/1.1 disabled
  - TLS 1.2 enabled with AES-GCM + CHACHA20 only (no CBC, no 3DES)
  - TLS 1.3 enabled (all suites are strong by design)
  - No RC4, NULL, EXPORT, 3DES, SEED ciphers
  - Insecure renegotiation disabled (ssl-noreg=enable on server policies)

Author: Ulysses Project
Version: 1.0.0
"""

import sys
import json
from typing import Any
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "sdk"))
from fortiweb_client import FortiWebClient, FortiWebAPIError


# --- Baseline definitions ---

# Weak ciphers that MUST NOT be present
WEAK_CIPHER_PATTERNS = {
    "DES-CBC3": "3DES (Sweet32 attack)",
    "RC4": "RC4 (known broken)",
    "NULL": "NULL cipher (no encryption)",
    "EXPORT": "EXPORT cipher (40/56-bit)",
    "SEED": "SEED (legacy Korean cipher)",
}

# CBC-mode ciphers — warn but don't fail (some legacy needs them)
CBC_WARN_PATTERNS = ["CBC"]
CBC_SAFE_PATTERNS = ["GCM", "CCM", "CHACHA", "POLY1305"]

# Baseline TLS versions
BASELINE_TLS = {
    "tls-v10": "disable",
    "tls-v11": "disable",
    "tls-v12": "enable",
    "tls-v13": "enable",
}

# Strong ciphers for our custom group (matches Mozilla-Intermediate)
BASELINE_TLS12_CIPHERS = [
    "ECDHE-ECDSA-AES256-GCM-SHA384",
    "ECDHE-RSA-AES256-GCM-SHA384",
    "DHE-RSA-AES256-GCM-SHA384",
    "ECDHE-ECDSA-CHACHA20-POLY1305",
    "ECDHE-RSA-CHACHA20-POLY1305",
    "DHE-RSA-CHACHA20-POLY1305",
    "ECDHE-ECDSA-AES128-GCM-SHA256",
    "ECDHE-RSA-AES128-GCM-SHA256",
    "DHE-RSA-AES128-GCM-SHA256",
]

BASELINE_TLS13_CIPHERS = [
    "TLS_AES_256_GCM_SHA384",
    "TLS_CHACHA20_POLY1305_SHA256",
    "TLS_AES_128_GCM_SHA256",
]


# --- Cipher analysis ---

def analyze_ciphers(cipher_string: str) -> dict:
    """Analyze a space-separated cipher string for weak entries."""
    ciphers = cipher_string.strip().split() if cipher_string else []
    weak = []
    cbc_warn = []

    for cipher in ciphers:
        for pattern, reason in WEAK_CIPHER_PATTERNS.items():
            if pattern in cipher:
                weak.append({"cipher": cipher, "reason": reason})
                break
        else:
            # Not in weak list — check for CBC
            is_cbc = any(p in cipher for p in CBC_WARN_PATTERNS)
            is_safe_mode = any(p in cipher for p in CBC_SAFE_PATTERNS)
            if is_cbc and not is_safe_mode:
                cbc_warn.append(cipher)

    return {
        "total": len(ciphers),
        "weak": weak,
        "cbc_warn": cbc_warn,
        "clean": len(ciphers) - len(weak) - len(cbc_warn),
    }


def audit_cipher_group(group: dict) -> list[dict]:
    """Audit a single cipher group against baseline."""
    findings = []
    name = group.get("name", "?")
    check_base = 0

    # TLS version checks
    for field, expected in BASELINE_TLS.items():
        actual = group.get(field, "?")
        label = field.replace("tls-v", "TLS 1.").replace("10", "0").replace("11", "1").replace("12", "2").replace("13", "3")
        if actual != expected:
            if expected == "disable" and actual == "enable":
                findings.append({"name": f"tls_{field}", "status": "FAIL",
                                 "detail": f"{label}: ENABLED (should be disabled — deprecated protocol)"})
            elif expected == "enable" and actual == "disable":
                findings.append({"name": f"tls_{field}", "status": "WARN",
                                 "detail": f"{label}: DISABLED (baseline recommends enabled)"})
        else:
            findings.append({"name": f"tls_{field}", "status": "PASS",
                             "detail": f"{label}: {actual}"})

    # Cipher analysis
    cipher_level = group.get("ssl-cipher", "?")
    custom_ciphers = group.get("ssl-custom-cipher", "")

    if cipher_level == "custom" and custom_ciphers:
        analysis = analyze_ciphers(custom_ciphers)

        if analysis["weak"]:
            for w in analysis["weak"]:
                findings.append({"name": f"weak_cipher", "status": "FAIL",
                                 "detail": f"Weak cipher: {w['cipher']} ({w['reason']})"})
        else:
            findings.append({"name": "no_weak_ciphers", "status": "PASS",
                             "detail": f"No weak ciphers (3DES/RC4/NULL/EXPORT) — {analysis['total']} ciphers total"})

        if analysis["cbc_warn"]:
            findings.append({"name": "cbc_ciphers", "status": "WARN",
                             "detail": f"{len(analysis['cbc_warn'])} CBC-mode ciphers present (Lucky13 risk): {', '.join(analysis['cbc_warn'][:3])}"})
    elif cipher_level in ("medium", "high"):
        findings.append({"name": "cipher_level", "status": "WARN",
                         "detail": f"Using preset '{cipher_level}' — review individual ciphers. 'custom' recommended for explicit control."})

    # TLS 1.3 ciphers (all are strong by design, just check they exist)
    tls13 = group.get("tls13-custom-cipher", "")
    if group.get("tls-v13") == "enable":
        if tls13:
            findings.append({"name": "tls13_ciphers", "status": "PASS",
                             "detail": f"TLS 1.3 ciphers: {tls13.strip()}"})
        else:
            findings.append({"name": "tls13_ciphers", "status": "WARN",
                             "detail": "TLS 1.3 enabled but no custom ciphers specified (using defaults)"})

    return findings


# --- Audit ---

def run_audit(client: FortiWebClient) -> dict:
    """Audit all cipher groups and server policies."""
    all_findings = []
    check_num = 1

    # Audit predefined cipher groups
    r = client.get("cmdb/server-policy/ssl-ciphers.predefined")
    for group in r.get("results", []):
        name = group.get("name", "?")
        group_findings = audit_cipher_group(group)
        for f in group_findings:
            f["check"] = check_num
            f["group"] = name
            f["detail"] = f"[{name}] {f['detail']}"
            check_num += 1
        all_findings.extend(group_findings)

    # Audit custom cipher groups
    r = client.get("cmdb/server-policy/ssl-ciphers.custom")
    for group in r.get("results", []):
        name = group.get("name", "?")
        group_findings = audit_cipher_group(group)
        for f in group_findings:
            f["check"] = check_num
            f["group"] = name
            f["detail"] = f"[{name}] {f['detail']}"
            check_num += 1
        all_findings.extend(group_findings)

    # Audit server policies (TLS settings can be inline on policy)
    r = client.get("cmdb/server-policy/policy")
    policies = r.get("results", [])
    if policies:
        for policy in policies:
            pname = policy.get("name", "?")
            ssl = policy.get("ssl", "disable")
            if ssl != "enable":
                all_findings.append({"check": check_num, "name": "policy_ssl", "group": pname,
                                     "status": "PASS", "detail": f"[Policy: {pname}] SSL disabled (HTTP only)"})
                check_num += 1
                continue

            # Check renegotiation
            noreg = policy.get("ssl-noreg", "disable")
            if noreg == "enable":
                all_findings.append({"check": check_num, "name": "policy_noreg", "group": pname,
                                     "status": "PASS", "detail": f"[Policy: {pname}] Insecure renegotiation disabled"})
            else:
                all_findings.append({"check": check_num, "name": "policy_noreg", "group": pname,
                                     "status": "FAIL", "detail": f"[Policy: {pname}] Insecure renegotiation ENABLED (SSL-DoS risk)"})
            check_num += 1

            # Check if using cipher group or inline
            use_group = policy.get("use-ciphers-group", "disable")
            if use_group == "enable":
                group_name = policy.get("ssl-ciphers-group", "")
                all_findings.append({"check": check_num, "name": "policy_cipher_group", "group": pname,
                                     "status": "PASS" if group_name else "WARN",
                                     "detail": f"[Policy: {pname}] Using cipher group: '{group_name}'"})
            else:
                # Inline TLS settings — audit them
                policy_findings = audit_cipher_group(policy)
                for f in policy_findings:
                    f["check"] = check_num
                    f["group"] = f"Policy: {pname}"
                    f["detail"] = f"[Policy: {pname}] {f['detail']}"
                    check_num += 1
                all_findings.extend(policy_findings)
            check_num += 1
    else:
        all_findings.append({"check": check_num, "name": "no_policies", "group": "n/a",
                             "status": "PASS",
                             "detail": "No server policies configured — TLS will be checked when policies are created"})

    passes = sum(1 for f in all_findings if f["status"] == "PASS")
    total = len(all_findings)

    return {
        "success": True,
        "action": "audit",
        "score": f"{passes}/{total}",
        "pass": passes,
        "fail": sum(1 for f in all_findings if f["status"] == "FAIL"),
        "warn": sum(1 for f in all_findings if f["status"] == "WARN"),
        "findings": all_findings,
    }


# --- Apply ---

def run_apply(client: FortiWebClient, bp_prefix: str) -> dict:
    """Create hardened cipher group."""
    group_name = f"{bp_prefix}-TLS-Hardened"

    # Check if exists
    r = client.get("cmdb/server-policy/ssl-ciphers.custom")
    existing = [g.get("name", "") for g in r.get("results", [])]
    if group_name in existing:
        return {"success": False, "action": "apply",
                "error": f"Cipher group '{group_name}' already exists. Delete it first or use a different bp_prefix."}

    # Create
    try:
        r = client.post("cmdb/server-policy/ssl-ciphers.custom", {
            "name": group_name,
            "tls-v10": "disable",
            "tls-v11": "disable",
            "tls-v12": "enable",
            "tls-v13": "enable",
            "ssl-cipher": "custom",
            "ssl-custom-cipher": " ".join(BASELINE_TLS12_CIPHERS),
            "tls13-custom-cipher": " ".join(BASELINE_TLS13_CIPHERS),
        })
    except FortiWebAPIError as e:
        return {"success": False, "action": "apply", "error": f"Failed creating cipher group: {e}"}

    # Verify
    try:
        r = client.get("cmdb/server-policy/ssl-ciphers.custom", extra_params={"mkey": group_name})
        res = r.get("results", {})
        tls12_count = len(res.get("ssl-custom-cipher", "").strip().split())
        tls13_count = len(res.get("tls13-custom-cipher", "").strip().split())
    except FortiWebAPIError:
        tls12_count = "?"
        tls13_count = "?"

    return {
        "success": True,
        "action": "apply",
        "created_objects": [{
            "type": "cipher_group",
            "name": group_name,
            "tls_versions": "1.2 + 1.3 (1.0/1.1 disabled)",
            "tls12_ciphers": tls12_count,
            "tls13_ciphers": tls13_count,
            "standard": "Mozilla-Intermediate equivalent",
        }],
        "message": f"Created cipher group '{group_name}'. To use it, set use-ciphers-group=enable "
                   f"and ssl-ciphers-group='{group_name}' on your server policy.",
    }


# --- Status ---

def run_status(client: FortiWebClient) -> dict:
    """Quick TLS posture summary."""
    groups = []

    # Predefined
    r = client.get("cmdb/server-policy/ssl-ciphers.predefined")
    for g in r.get("results", []):
        analysis = analyze_ciphers(g.get("ssl-custom-cipher", ""))
        groups.append({
            "name": g.get("name"),
            "type": "predefined",
            "tls10": g.get("tls-v10"),
            "tls11": g.get("tls-v11"),
            "tls12": g.get("tls-v12"),
            "tls13": g.get("tls-v13"),
            "weak_ciphers": len(analysis["weak"]),
            "cbc_ciphers": len(analysis["cbc_warn"]),
            "total_ciphers": analysis["total"],
        })

    # Custom
    r = client.get("cmdb/server-policy/ssl-ciphers.custom")
    for g in r.get("results", []):
        analysis = analyze_ciphers(g.get("ssl-custom-cipher", ""))
        groups.append({
            "name": g.get("name"),
            "type": "custom",
            "tls10": g.get("tls-v10"),
            "tls11": g.get("tls-v11"),
            "tls12": g.get("tls-v12"),
            "tls13": g.get("tls-v13"),
            "weak_ciphers": len(analysis["weak"]),
            "cbc_ciphers": len(analysis["cbc_warn"]),
            "total_ciphers": analysis["total"],
        })

    # Server policies
    r = client.get("cmdb/server-policy/policy")
    policies = r.get("results", [])
    ssl_policies = [p for p in policies if p.get("ssl") == "enable"]

    any_weak = any(g["weak_ciphers"] > 0 for g in groups)
    any_legacy_tls = any(g["tls10"] == "enable" or g["tls11"] == "enable" for g in groups)

    if any_weak or any_legacy_tls:
        posture = "WEAK"
    elif any(g["cbc_ciphers"] > 0 for g in groups):
        posture = "PARTIAL"
    else:
        posture = "GOOD"

    return {
        "success": True,
        "action": "status",
        "cipher_groups": groups,
        "server_policies_with_ssl": len(ssl_policies),
        "server_policies_total": len(policies),
        "posture": posture,
    }


# --- Entry point ---

def main(context) -> dict[str, Any]:
    """FortiWeb TLS Cipher Baseline — audit, apply, or status."""
    if hasattr(context, "parameters"):
        args = context.parameters
        creds = getattr(context, "credentials", None)
    else:
        args = context
        creds = None

    target_ip = args.get("target_ip")
    action = args.get("action", "status")
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
            result.update(run_audit(client))
        elif action == "apply":
            result.update(run_apply(client, bp_prefix))
        elif action == "status":
            result.update(run_status(client))
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
