"""
FortiBot NOC - Network Analyzer Tool
Retrieves traffic and event logs from FortiGate for network analysis.
"""
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

LOG_SOURCES = ["disk", "memory"]


def run(device: dict, mode: str = "traffic", rows: int = 50,
        filter_srcip: str = None, filter_dstip: str = None) -> dict:
    """Retrieve and analyze FortiGate logs.

    Args:
        device: Device dict with ip, port, api_token.
        mode: 'traffic' for forward traffic logs, 'event' for system events.
        rows: Number of log entries to retrieve (max 2000).
        filter_srcip: Filter by source IP.
        filter_dstip: Filter by destination IP.

    Returns:
        dict with log entries.
    """
    base = f"https://{device['ip']}:{device['port']}"
    headers = {"Authorization": f"Bearer {device['api_token']}"}
    rows = min(rows, 2000)

    if mode == "traffic":
        endpoint_path = "/api/v2/log/{source}/traffic/forward"
    elif mode == "event":
        endpoint_path = "/api/v2/log/{source}/event/system"
    else:
        return {"success": False, "error": f"Unknown mode: {mode}. Use 'traffic' or 'event'."}

    # Build filter string
    filters = []
    if filter_srcip:
        filters.append(f"srcip=={filter_srcip}")
    if filter_dstip:
        filters.append(f"dstip=={filter_dstip}")
    filter_str = ",".join(filters) if filters else None

    params = {"rows": rows}
    if filter_str:
        params["filter"] = filter_str

    # Try each log source in priority order
    for source in LOG_SOURCES:
        endpoint = endpoint_path.format(source=source)
        try:
            resp = requests.get(
                f"{base}{endpoint}",
                headers=headers, params=params, verify=False, timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            logs = data.get("results", [])
            if not logs:
                continue  # Try next source

            entries = []
            for log in logs:
                entry = {
                    "date": log.get("date", ""),
                    "time": log.get("time", ""),
                    "type": log.get("type", ""),
                    "subtype": log.get("subtype", ""),
                    "level": log.get("level", ""),
                }
                if mode == "traffic":
                    entry.update({
                        "srcip": log.get("srcip", ""),
                        "dstip": log.get("dstip", ""),
                        "srcport": log.get("srcport", 0),
                        "dstport": log.get("dstport", 0),
                        "service": log.get("service", ""),
                        "action": log.get("action", ""),
                        "sentbyte": int(log.get("sentbyte", 0)),
                        "rcvdbyte": int(log.get("rcvdbyte", 0)),
                        "policyid": log.get("policyid", 0),
                    })
                elif mode == "event":
                    entry.update({
                        "msg": log.get("msg", ""),
                        "action": log.get("action", ""),
                        "user": log.get("user", ""),
                        "logdesc": log.get("logdesc", ""),
                    })
                entries.append(entry)

            return {
                "success": True,
                "mode": mode,
                "source": source,
                "total_entries": data.get("total_lines", len(entries)),
                "returned_count": len(entries),
                "entries": entries,
            }
        except Exception:
            continue

    return {
        "success": False,
        "error": f"No {mode} logs available from any source (disk, memory).",
    }
