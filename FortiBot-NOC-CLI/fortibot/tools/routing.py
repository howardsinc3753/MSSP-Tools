"""
FortiBot NOC - Routing Table Tool
Retrieves the IPv4 routing table from a FortiGate device.
"""
import ipaddress
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def run(device: dict, filter_destination: str = None) -> dict:
    """Get the IPv4 routing table, optionally filtered by destination IP."""
    base = f"https://{device['ip']}:{device['port']}"
    headers = {"Authorization": f"Bearer {device['api_token']}"}

    try:
        resp = requests.get(
            f"{base}/api/v2/monitor/router/ipv4",
            headers=headers, verify=False, timeout=10,
        ).json()

        route_list = resp.get("results", [])

        routes = []
        for r in route_list:
            routes.append({
                "destination": f"{r.get('ip', '0.0.0.0')}/{r.get('mask', 0)}",
                "gateway": r.get("gateway", "0.0.0.0"),
                "interface": r.get("interface", ""),
                "type": r.get("type", "unknown"),
                "distance": r.get("distance", 0),
                "metric": r.get("metric", 0),
                "priority": r.get("priority", 0),
            })

        # Filter by destination IP if provided
        if filter_destination:
            filtered = []
            for r in routes:
                try:
                    ip = ipaddress.ip_address(filter_destination)
                    net = ipaddress.ip_network(r["destination"], strict=False)
                    if ip in net:
                        filtered.append(r)
                except ValueError:
                    if filter_destination in r["destination"]:
                        filtered.append(r)
            routes = filtered

        routes.sort(key=lambda r: r["destination"])

        return {
            "success": True,
            "total_routes": len(route_list),
            "returned_count": len(routes),
            "routes": routes,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
