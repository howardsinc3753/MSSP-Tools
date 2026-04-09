"""
FortiBot NOC - Top Bandwidth Analyzer Tool
Identifies top bandwidth consumers by source IP from traffic logs.
"""
from collections import defaultdict
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def run(device: dict, top_n: int = 10) -> dict:
    """Get top bandwidth consumers from forward traffic logs.

    Args:
        device: Device dict with ip, port, api_token.
        top_n: Number of top consumers to return.

    Returns:
        dict with top consumers by source IP.
    """
    base = f"https://{device['ip']}:{device['port']}"
    headers = {"Authorization": f"Bearer {device['api_token']}"}

    try:
        resp = requests.get(
            f"{base}/api/v2/log/disk/traffic/forward?rows=2000",
            headers=headers, verify=False, timeout=15,
        ).json()

        logs = resp.get("results", [])

        ip_stats = defaultdict(lambda: {
            "sent_bytes": 0, "recv_bytes": 0, "total_bytes": 0,
            "session_count": 0, "users": set(),
        })

        for log in logs:
            srcip = log.get("srcip", "unknown")
            sent = int(log.get("sentbyte", 0))
            recv = int(log.get("rcvdbyte", 0))
            user = log.get("user", "")
            s = ip_stats[srcip]
            s["sent_bytes"] += sent
            s["recv_bytes"] += recv
            s["total_bytes"] += sent + recv
            s["session_count"] += 1
            if user:
                s["users"].add(user)

        sorted_ips = sorted(ip_stats.items(), key=lambda x: x[1]["total_bytes"], reverse=True)

        consumers = []
        for rank, (ip, stats) in enumerate(sorted_ips[:top_n], 1):
            consumers.append({
                "rank": rank,
                "source_ip": ip,
                "users": list(stats["users"]) if stats["users"] else [],
                "total_bytes": stats["total_bytes"],
                "total_mb": round(stats["total_bytes"] / (1024 * 1024), 2),
                "sent_mb": round(stats["sent_bytes"] / (1024 * 1024), 2),
                "recv_mb": round(stats["recv_bytes"] / (1024 * 1024), 2),
                "session_count": stats["session_count"],
            })

        total_bw = sum(s["total_bytes"] for s in ip_stats.values())

        return {
            "success": True,
            "logs_analyzed": len(logs),
            "unique_sources": len(ip_stats),
            "total_bandwidth_mb": round(total_bw / (1024 * 1024), 2),
            "top_consumers": consumers,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
