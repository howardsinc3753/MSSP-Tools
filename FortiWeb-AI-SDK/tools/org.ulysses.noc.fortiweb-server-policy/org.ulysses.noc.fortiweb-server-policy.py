#!/usr/bin/env python3
from __future__ import annotations
"""
FortiWeb Server Policy Builder

Creates the full server policy stack — the keystone that makes FortiWeb
actually inspect traffic. Without a server policy, all the protection
profile settings are unused.

Dependency order:
  1. VIP (virtual IP)          — cmdb/system/vip
  2. Virtual Server            — cmdb/server-policy/vserver  (references VIP)
  3. Server Pool               — cmdb/server-policy/server-pool
  4. Pserver (backend member)  — sub-table of server-pool
  5. Server Policy             — cmdb/server-policy/policy
     ties together: vserver + server-pool + protection-profile + TLS

Known API limitations (sub-tables):
  - vip-list on vserver       — manual GUI step to link VIP
  - pserver-list on pool      — manual GUI step to add backend IPs

Author: Ulysses Project
Version: 1.0.0
"""

import sys
import json
from typing import Any, Optional
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "sdk"))
from fortiweb_client import FortiWebClient, FortiWebAPIError


def _ensure_profile_exists(client: FortiWebClient, profile_name: str) -> bool:
    """Verify the protection profile exists before we build a policy around it."""
    try:
        r = client.get("cmdb/waf/web-protection-profile.inline-protection",
                        extra_params={"mkey": profile_name})
        return bool(r.get("results", {}).get("name"))
    except FortiWebAPIError:
        return False


def _check_interface(client: FortiWebClient, iface: str) -> bool:
    try:
        r = client.get("system/network.interface")
        for i in r.get("results", []):
            if i.get("name") == iface:
                return True
    except FortiWebAPIError:
        pass
    return False


def run_apply(client: FortiWebClient, args: dict) -> dict:
    """Create full server policy stack."""
    created = []
    bp_prefix = args.get("bp_prefix", "BP")
    policy_name = args.get("policy_name", f"{bp_prefix}-WebApp-Policy")
    vip_address = args.get("vip_address")
    vip_interface = args.get("vip_interface", "port1")
    backend_ip = args.get("backend_ip")
    backend_port = args.get("backend_port", 80)
    https_enabled = args.get("https_enabled", False)
    cert_name = args.get("certificate_name")
    cipher_group = args.get("cipher_group")
    protection_profile = args.get("protection_profile", "BP-SQLi-Protection")

    # Validation
    if not vip_address:
        return {"success": False, "action": "apply",
                "error": "vip_address is required (FortiWeb listening IP)"}
    if not backend_ip:
        return {"success": False, "action": "apply",
                "error": "backend_ip is required (Rocky Linux app server IP)"}
    if https_enabled and not cert_name:
        return {"success": False, "action": "apply",
                "error": "certificate_name is required when https_enabled=true"}

    # Preflight checks
    if not _ensure_profile_exists(client, protection_profile):
        return {"success": False, "action": "apply",
                "error": f"Protection profile '{protection_profile}' does not exist. Run baseline tools first."}

    if not _check_interface(client, vip_interface):
        return {"success": False, "action": "apply",
                "error": f"Interface '{vip_interface}' not found on FortiWeb"}

    vip_name = f"{bp_prefix}-VIP"
    vserver_name = f"{bp_prefix}-VServer"
    pool_name = f"{bp_prefix}-Pool"

    # Check for existing objects
    existing = _check_existing(client, [
        ("cmdb/system/vip", vip_name),
        ("cmdb/server-policy/vserver", vserver_name),
        ("cmdb/server-policy/server-pool", pool_name),
        ("cmdb/server-policy/policy", policy_name),
    ])
    if existing:
        return {"success": False, "action": "apply",
                "error": f"Objects already exist: {existing}. Use different bp_prefix or delete first."}

    # Step 1: VIP
    try:
        client.post("cmdb/system/vip", {
            "name": vip_name,
            "vip": vip_address,
            "interface": vip_interface,
        })
        created.append({"type": "vip", "name": vip_name,
                        "vip": vip_address, "interface": vip_interface})
    except FortiWebAPIError as e:
        return {"success": False, "action": "apply",
                "error": f"Failed creating VIP: {e}", "created_objects": created}

    # Step 2: Virtual Server (VIP link needs GUI step)
    try:
        client.post("cmdb/server-policy/vserver", {
            "name": vserver_name,
            "vip-list": [{"id": 1, "vip": vip_name}],
        })
        created.append({"type": "vserver", "name": vserver_name,
                        "vip_linked_via_gui_needed": True})
    except FortiWebAPIError as e:
        return {"success": False, "action": "apply",
                "error": f"Failed creating Virtual Server: {e}", "created_objects": created}

    # Step 3: Server Pool
    try:
        pool_config = {
            "name": pool_name,
            "type": "reverse-proxy",
            "protocol": "HTTP",
            "server-balance": "disable",
            "lb-algo": "round-robin",
            "pserver-list": [{
                "id": 1,
                "server-type": "physical",
                "ip": backend_ip,
                "port": backend_port,
                "weight": 1,
                "status": "enable",
                "ssl": "disable",
                "http2": "disable",
            }],
        }
        client.post("cmdb/server-policy/server-pool", pool_config)
        created.append({"type": "server_pool", "name": pool_name,
                        "backend_ip": backend_ip, "backend_port": backend_port,
                        "pserver_linked_via_gui_needed": True})
    except FortiWebAPIError as e:
        return {"success": False, "action": "apply",
                "error": f"Failed creating Server Pool: {e}", "created_objects": created}

    # Step 4: Server Policy (the keystone)
    try:
        policy_config = {
            "name": policy_name,
            "deployment-mode": "server-pool",
            "protocol": "HTTP",
            "vserver": vserver_name,
            "server-pool": pool_name,
            "web-protection-profile": protection_profile,
            "monitor-mode": "disable",
            "ssl": "enable" if https_enabled else "disable",
        }

        if https_enabled:
            policy_config.update({
                "service": "",
                "https-service": "HTTPS",
                "certificate": cert_name,
                "http-to-https": "enable",
                "tls-v10": "disable",
                "tls-v11": "disable",
                "tls-v12": "enable",
                "tls-v13": "enable",
                "ssl-noreg": "enable",
            })
            if cipher_group:
                policy_config["use-ciphers-group"] = "enable"
                policy_config["ssl-ciphers-group"] = cipher_group
        else:
            policy_config["service"] = "HTTP"

        client.post("cmdb/server-policy/policy", policy_config)
        created.append({
            "type": "server_policy",
            "name": policy_name,
            "protocol": "HTTPS" if https_enabled else "HTTP",
            "protection_profile": protection_profile,
            "cipher_group": cipher_group if https_enabled else None,
        })
    except FortiWebAPIError as e:
        return {"success": False, "action": "apply",
                "error": f"Failed creating Server Policy: {e}", "created_objects": created}

    # Build reminder list for GUI steps
    gui_steps = [
        f"Link VIP '{vip_name}' to VServer '{vserver_name}' (Server Objects > Virtual Server > {vserver_name} > Add VIP)",
        f"Add backend '{backend_ip}:{backend_port}' to Pool '{pool_name}' (Server Objects > Server Pool > {pool_name} > Add Member)",
    ]

    return {
        "success": True,
        "action": "apply",
        "created_objects": created,
        "gui_steps_required": gui_steps,
        "message": f"Server policy '{policy_name}' created. "
                   f"Traffic to {vip_address}:{'443' if https_enabled else '80'} "
                   f"→ {backend_ip}:{backend_port} with '{protection_profile}' inspection. "
                   f"Complete the {len(gui_steps)} GUI steps to activate.",
    }


def _check_existing(client: FortiWebClient, checks: list) -> list:
    """Return list of object names that already exist."""
    existing = []
    for endpoint, mkey in checks:
        try:
            r = client.get(endpoint, extra_params={"mkey": mkey})
            if r.get("results", {}).get("name") == mkey:
                existing.append(mkey)
        except FortiWebAPIError:
            pass
    return existing


def run_audit(client: FortiWebClient) -> dict:
    """Audit existing server policies."""
    findings = []
    check = 1

    try:
        r = client.get("cmdb/server-policy/policy")
        policies = r.get("results", [])
    except FortiWebAPIError as e:
        return {"success": False, "error": str(e)}

    if not policies:
        findings.append({"check": check, "name": "no_policies", "status": "FAIL",
                         "detail": "No server policies configured — FortiWeb is not inspecting any traffic"})
        return _build_audit_result(findings)

    findings.append({"check": check, "name": "policies_exist", "status": "PASS",
                     "detail": f"{len(policies)} server policy/policies configured"})
    check += 1

    for p in policies:
        pname = p.get("name", "?")
        profile = p.get("web-protection-profile", "")
        ssl = p.get("ssl", "disable")
        use_group = p.get("use-ciphers-group", "disable")
        cipher_group = p.get("ssl-ciphers-group", "")
        noreg = p.get("ssl-noreg", "disable")
        tls10 = p.get("tls-v10", "disable")
        tls11 = p.get("tls-v11", "disable")
        monitor = p.get("monitor-mode", "disable")

        if not profile:
            findings.append({"check": check, "name": f"policy_{pname}_profile", "status": "FAIL",
                             "detail": f"[{pname}] No protection profile attached"})
        else:
            findings.append({"check": check, "name": f"policy_{pname}_profile", "status": "PASS",
                             "detail": f"[{pname}] Protection profile: '{profile}'"})
        check += 1

        if monitor == "enable":
            findings.append({"check": check, "name": f"policy_{pname}_monitor", "status": "WARN",
                             "detail": f"[{pname}] Monitor mode ENABLED — traffic is only logged, not blocked"})
            check += 1

        if ssl == "enable":
            if use_group == "enable" and cipher_group:
                findings.append({"check": check, "name": f"policy_{pname}_cipher_group", "status": "PASS",
                                 "detail": f"[{pname}] Using cipher group: '{cipher_group}'"})
            else:
                findings.append({"check": check, "name": f"policy_{pname}_cipher_group", "status": "WARN",
                                 "detail": f"[{pname}] SSL enabled but no cipher group — using inline settings"})
            check += 1

            if tls10 == "enable" or tls11 == "enable":
                findings.append({"check": check, "name": f"policy_{pname}_tls_legacy", "status": "FAIL",
                                 "detail": f"[{pname}] Legacy TLS enabled (1.0={tls10}, 1.1={tls11})"})
                check += 1

            if noreg != "enable":
                findings.append({"check": check, "name": f"policy_{pname}_noreg", "status": "WARN",
                                 "detail": f"[{pname}] SSL renegotiation allowed (SSL-DoS risk)"})
                check += 1

    return _build_audit_result(findings)


def _build_audit_result(findings: list) -> dict:
    passes = sum(1 for f in findings if f["status"] == "PASS")
    return {
        "success": True,
        "action": "audit",
        "score": f"{passes}/{len(findings)}",
        "pass": passes,
        "fail": sum(1 for f in findings if f["status"] == "FAIL"),
        "warn": sum(1 for f in findings if f["status"] == "WARN"),
        "findings": findings,
    }


def run_status(client: FortiWebClient) -> dict:
    try:
        r = client.get("cmdb/server-policy/policy")
        policies = r.get("results", [])
    except FortiWebAPIError as e:
        return {"success": False, "error": str(e)}

    summary = []
    for p in policies:
        summary.append({
            "name": p.get("name"),
            "protocol": p.get("protocol"),
            "ssl": p.get("ssl"),
            "vserver": p.get("vserver"),
            "server_pool": p.get("server-pool"),
            "protection_profile": p.get("web-protection-profile") or "(none)",
            "cipher_group": p.get("ssl-ciphers-group") or "(inline)",
            "monitor_mode": p.get("monitor-mode"),
        })

    return {
        "success": True,
        "action": "status",
        "policy_count": len(policies),
        "policies": summary,
        "posture": "DEPLOYED" if policies else "NOT_DEPLOYED",
    }


def run_delete(client: FortiWebClient, args: dict) -> dict:
    """Delete a server policy and its dependencies in reverse order."""
    bp_prefix = args.get("bp_prefix", "BP")
    policy_name = args.get("policy_name", f"{bp_prefix}-WebApp-Policy")
    vip_name = f"{bp_prefix}-VIP"
    vserver_name = f"{bp_prefix}-VServer"
    pool_name = f"{bp_prefix}-Pool"

    deleted = []
    errors = []

    for label, endpoint, mkey in [
        ("server_policy", "cmdb/server-policy/policy", policy_name),
        ("server_pool", "cmdb/server-policy/server-pool", pool_name),
        ("vserver", "cmdb/server-policy/vserver", vserver_name),
        ("vip", "cmdb/system/vip", vip_name),
    ]:
        try:
            client.delete(endpoint, mkey=mkey)
            deleted.append({"type": label, "name": mkey})
        except FortiWebAPIError as e:
            errors.append({"type": label, "name": mkey, "error": str(e)})

    return {
        "success": len(errors) == 0,
        "action": "delete",
        "deleted_objects": deleted,
        "errors": errors,
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
            result.update(run_apply(client, args))
        elif action == "status":
            result.update(run_status(client))
        elif action == "delete":
            result.update(run_delete(client, args))
        else:
            return {"success": False,
                    "error": f"Unknown action: {action}. Use: audit, apply, status, delete"}
    except FortiWebAPIError as e:
        result["success"] = False
        result["error"] = str(e)
    except Exception as e:
        result["success"] = False
        result["error"] = f"Unexpected error: {e}"

    return result


if __name__ == "__main__":
    result = main({"target_ip": "192.168.209.31", "action": "status"})
    print(json.dumps(result, indent=2))
