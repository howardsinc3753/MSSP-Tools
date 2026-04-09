"""
FortiBot NOC - VPN / IPsec Tunnel Tool
Lists IPsec VPN tunnels and their operational status.
"""
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def run(device: dict) -> dict:
    """List all IPsec VPN tunnels with configuration and status."""
    base = f"https://{device['ip']}:{device['port']}"
    headers = {"Authorization": f"Bearer {device['api_token']}"}

    try:
        # Phase 1 config
        cfg_resp = requests.get(
            f"{base}/api/v2/cmdb/vpn.ipsec/phase1-interface",
            headers=headers, verify=False, timeout=10,
        ).json()

        tunnels = []
        for t in cfg_resp.get("results", []):
            tunnels.append({
                "name": t.get("name", ""),
                "interface": t.get("interface", ""),
                "remote_gw": t.get("remote-gw", ""),
                "ike_version": t.get("ike-version", ""),
                "type": t.get("type", ""),
                "dpd": t.get("dpd", ""),
                "proposal": t.get("proposal", ""),
                "status": "unknown",
                "incoming_bytes": 0,
                "outgoing_bytes": 0,
            })

        # Operational status
        try:
            mon_resp = requests.get(
                f"{base}/api/v2/monitor/vpn/ipsec",
                headers=headers, verify=False, timeout=10,
            ).json()

            status_map = {}
            for s in mon_resp.get("results", []):
                name = s.get("name", "")
                if name:
                    status_map[name] = {
                        "status": "up" if s.get("proxyid") else "down",
                        "incoming_bytes": s.get("incoming_bytes", 0),
                        "outgoing_bytes": s.get("outgoing_bytes", 0),
                    }

            for t in tunnels:
                if t["name"] in status_map:
                    t.update(status_map[t["name"]])
        except Exception:
            pass  # status is optional enrichment

        up_count = sum(1 for t in tunnels if t["status"] == "up")
        return {
            "success": True,
            "tunnel_count": len(tunnels),
            "up": up_count,
            "down": len(tunnels) - up_count,
            "tunnels": tunnels,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
