"""
FortiBot NOC - Interface Status Tool
Retrieves interface status and NIC statistics from a FortiGate device.
"""
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def run(device: dict) -> dict:
    """Get all interface status including link, speed, errors, and traffic counters."""
    base = f"https://{device['ip']}:{device['port']}"
    headers = {"Authorization": f"Bearer {device['api_token']}"}

    try:
        resp = requests.get(
            f"{base}/api/v2/monitor/system/interface",
            headers=headers, verify=False, timeout=10,
        ).json()

        interfaces = []
        for iface_name, iface in resp.get("results", {}).items():
            duplex_val = iface.get("duplex", 0)
            duplex_str = "full" if duplex_val == 1 else ("half" if duplex_val == 0 else str(duplex_val))

            interfaces.append({
                "name": iface.get("name", iface_name),
                "ip": iface.get("ip", "0.0.0.0"),
                "mask": iface.get("mask", 0),
                "status": "up" if iface.get("link") else "down",
                "link": iface.get("link", False),
                "speed": int(iface.get("speed", 0)),
                "duplex": duplex_str,
                "mac": iface.get("mac", "00:00:00:00:00:00"),
                "rx_bytes": iface.get("rx_bytes", 0),
                "tx_bytes": iface.get("tx_bytes", 0),
                "rx_packets": iface.get("rx_packets", 0),
                "tx_packets": iface.get("tx_packets", 0),
                "rx_errors": iface.get("rx_errors", 0),
                "tx_errors": iface.get("tx_errors", 0),
            })

        up_count = sum(1 for i in interfaces if i["link"])
        error_count = sum(1 for i in interfaces if i["rx_errors"] > 0 or i["tx_errors"] > 0)

        return {
            "success": True,
            "interface_count": len(interfaces),
            "up": up_count,
            "down": len(interfaces) - up_count,
            "with_errors": error_count,
            "interfaces": interfaces,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
