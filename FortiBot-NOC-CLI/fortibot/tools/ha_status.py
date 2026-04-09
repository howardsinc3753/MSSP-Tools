"""
FortiBot NOC - HA (High Availability) Status Tool
Checks HA cluster status including mode, sync state, and peer info.
"""
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HA_MODE_MAP = {
    "standalone": "standalone",
    "a-p": "active-passive",
    "a-a": "active-active",
    "active-passive": "active-passive",
    "active-active": "active-active",
}


def _format_uptime(seconds: int) -> str:
    if seconds <= 0:
        return "0s"
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    return "".join(parts) or f"{seconds}s"


def run(device: dict) -> dict:
    """Get HA cluster status: mode, sync state, nodes, heartbeats."""
    base = f"https://{device['ip']}:{device['port']}"
    headers = {"Authorization": f"Bearer {device['api_token']}"}

    try:
        status = requests.get(
            f"{base}/api/v2/monitor/system/status",
            headers=headers, verify=False, timeout=10,
        ).json()

        results = status.get("results", {})
        ha_mode_raw = results.get("ha_mode") or status.get("ha_mode") or "standalone"
        ha_mode = HA_MODE_MAP.get(str(ha_mode_raw).lower().strip(), str(ha_mode_raw))
        hostname = results.get("hostname", "unknown")

        if ha_mode == "standalone":
            return {
                "success": True,
                "mode": "standalone",
                "hostname": hostname,
                "nodes": [],
                "verdict": "Device is in standalone mode -- no HA configured.",
            }

        # Get HA peer info
        nodes = []
        flags = []
        try:
            peer_resp = requests.get(
                f"{base}/api/v2/monitor/system/ha-peer",
                headers=headers, verify=False, timeout=10,
            ).json()

            for peer in peer_resp.get("results", []):
                node = {
                    "hostname": peer.get("hostname", "unknown"),
                    "serial_number": peer.get("serial_no", "unknown"),
                    "role": peer.get("role", "unknown"),
                    "priority": peer.get("priority", 0),
                    "uptime": _format_uptime(peer.get("uptime", 0)),
                }
                nodes.append(node)
        except Exception:
            flags.append("Could not retrieve HA peer information.")

        # Sync state from checksums
        sync_state = "unknown"
        try:
            cs_resp = requests.get(
                f"{base}/api/v2/monitor/system/ha-checksums",
                headers=headers, verify=False, timeout=10,
            ).json()
            checksums = cs_resp.get("results", [])
            if len(checksums) >= 2:
                cs0 = checksums[0].get("checksum", checksums[0])
                cs1 = checksums[1].get("checksum", checksums[1])
                if isinstance(cs0, dict) and isinstance(cs1, dict):
                    oos = [k for k in set(cs0) | set(cs1)
                           if k not in ("serial_no", "hostname", "is_manage_master")
                           and cs0.get(k) != cs1.get(k)]
                    sync_state = "out-of-sync" if oos else "in-sync"
                    if oos:
                        flags.append(f"Out of sync tables: {', '.join(oos)}")
        except Exception:
            pass

        if len(nodes) < 2 and ha_mode != "standalone":
            flags.append("Single-node HA cluster -- no peer detected.")

        node_summary = ", ".join(f"{n['hostname']} ({n['role']})" for n in nodes) or "none detected"
        verdict = (
            f"HA {ha_mode} cluster: {node_summary}. Sync: {sync_state}."
            + (f" Issues: {'; '.join(flags)}" if flags else " No issues detected.")
        )

        return {
            "success": True,
            "mode": ha_mode,
            "hostname": hostname,
            "sync_state": sync_state,
            "nodes": nodes,
            "flags": flags,
            "verdict": verdict,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
