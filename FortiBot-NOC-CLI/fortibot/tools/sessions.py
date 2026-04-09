"""
FortiBot NOC - Session Table Tool
Retrieves active firewall sessions for troubleshooting.
"""
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROTO_MAP = {1: "ICMP", 6: "TCP", 17: "UDP", 47: "GRE", 50: "ESP", 89: "OSPF"}


def run(device: dict, count: int = 20, filter_srcip: str = None,
        filter_dstip: str = None, filter_dport: str = None) -> dict:
    """Get active firewall sessions with optional filters."""
    base = f"https://{device['ip']}:{device['port']}"
    headers = {"Authorization": f"Bearer {device['api_token']}"}
    params = {"count": min(count, 1000), "start": 0}

    filters = []
    if filter_srcip:
        filters.append(f"src=={filter_srcip}")
    if filter_dstip:
        filters.append(f"dst=={filter_dstip}")
    if filter_dport:
        filters.append(f"dport=={filter_dport}")
    if filters:
        params["filter"] = ",".join(filters)

    try:
        # Try 7.6+ endpoint first
        try:
            resp = requests.get(
                f"{base}/api/v2/monitor/firewall/sessions",
                headers=headers, params=params, verify=False, timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.HTTPError:
            resp = requests.get(
                f"{base}/api/v2/monitor/firewall/session",
                headers=headers, params=params, verify=False, timeout=10,
            ).json()
            data = resp

        results_obj = data.get("results", {})
        if isinstance(results_obj, dict):
            session_list = results_obj.get("details", [])
        else:
            session_list = results_obj if isinstance(results_obj, list) else []

        sessions = []
        for s in session_list:
            proto_str = s.get("proto", "")
            if isinstance(proto_str, str):
                proto_name = proto_str.upper()
            else:
                proto_name = PROTO_MAP.get(proto_str, f"proto-{proto_str}")

            sessions.append({
                "src_ip": s.get("saddr", ""),
                "src_port": s.get("sport", 0),
                "dst_ip": s.get("daddr", ""),
                "dst_port": s.get("dport", 0),
                "proto": proto_name,
                "policy_id": s.get("policyid", 0),
                "bytes_in": s.get("rcvdbyte", 0),
                "bytes_out": s.get("sentbyte", 0),
                "duration": s.get("duration", 0),
                "src_intf": s.get("srcintf", ""),
                "dst_intf": s.get("dstintf", ""),
            })

        sessions.sort(key=lambda x: x["bytes_in"] + x["bytes_out"], reverse=True)

        return {
            "success": True,
            "total_sessions": data.get("total", len(sessions)),
            "returned_count": len(sessions),
            "sessions": sessions,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
