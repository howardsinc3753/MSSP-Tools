"""
FortiBot NOC - FortiGuard License & Update Status Tool
Checks subscription licenses and signature update freshness.
"""
import requests
import urllib3
from datetime import datetime, timezone

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SERVICES = {
    "antivirus": "AntiVirus",
    "ips": "Intrusion Prevention (IPS)",
    "webfilter": "Web Filter",
    "appctrl": "Application Control",
    "industrial_db": "Industrial Security",
    "dns_filter": "DNS Filter",
    "antispam": "Anti-Spam",
    "forticare": "FortiCare Support",
    "security_rating": "Security Rating",
    "botnet_domain": "Botnet Domain",
    "botnet_ip": "Botnet IP",
}


def _parse_ts(ts):
    if isinstance(ts, (int, float)) and ts > 0:
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            return None
    return None


def run(device: dict) -> dict:
    """Check FortiGuard subscription and signature status."""
    base = f"https://{device['ip']}:{device['port']}"
    headers = {"Authorization": f"Bearer {device['api_token']}"}

    try:
        resp = requests.get(
            f"{base}/api/v2/monitor/license/status",
            headers=headers, verify=False, timeout=10,
        ).json()

        results = resp.get("results", {})
        now = datetime.now(timezone.utc)
        services = []
        flags = []

        for key, display in SERVICES.items():
            svc_data = results.get(key)
            if svc_data is None:
                continue

            licensed = bool(svc_data.get("status", 0)) or bool(svc_data.get("licensed", False))
            expiry_dt = _parse_ts(svc_data.get("expires") or svc_data.get("expiry_date"))
            days_left = (expiry_dt - now).days if expiry_dt else None

            status = "ok"
            if days_left is not None and days_left < 0:
                status = "expired"
            elif not licensed:
                status = "expired"
            elif days_left is not None and days_left <= 30:
                status = "warning"

            services.append({
                "name": display,
                "licensed": licensed,
                "days_until_expiry": days_left,
                "status": status,
            })

            if status == "expired":
                flags.append(f"{display}: EXPIRED")
            elif status == "warning":
                flags.append(f"{display}: expiring in {days_left} days")

        ok_count = sum(1 for s in services if s["status"] == "ok")
        warn_count = sum(1 for s in services if s["status"] == "warning")
        exp_count = sum(1 for s in services if s["status"] == "expired")

        if exp_count:
            verdict = f"{exp_count} service(s) EXPIRED. {ok_count}/{len(services)} OK."
        elif warn_count:
            verdict = f"{warn_count} service(s) expiring soon. {ok_count}/{len(services)} OK."
        else:
            verdict = "All FortiGuard services current and licensed."

        return {
            "success": True,
            "services": services,
            "ok": ok_count,
            "warning": warn_count,
            "expired": exp_count,
            "flags": flags,
            "verdict": verdict,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
