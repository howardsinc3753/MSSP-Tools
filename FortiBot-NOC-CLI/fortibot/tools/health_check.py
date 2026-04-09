"""
FortiBot NOC - Health Check Tool
Retrieves CPU, memory, disk, session count, and uptime from a FortiGate.
"""
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def run(device: dict) -> dict:
    """Get FortiGate health status: CPU, memory, disk, sessions, uptime."""
    base = f"https://{device['ip']}:{device['port']}"
    headers = {"Authorization": f"Bearer {device['api_token']}"}

    try:
        status_resp = requests.get(
            f"{base}/api/v2/monitor/system/status",
            headers=headers, verify=False, timeout=10,
        )
        status_resp.raise_for_status()
        status = status_resp.json()

        resources_resp = requests.get(
            f"{base}/api/v2/monitor/system/resource/usage",
            headers=headers, verify=False, timeout=10,
        )
        resources_resp.raise_for_status()
        resources = resources_resp.json()

        results = status.get("results", {})
        res = resources.get("results", {})

        def _current(data):
            """Extract the current value from a resource metric."""
            if isinstance(data, list) and data:
                return data[0].get("current", 0)
            if isinstance(data, dict):
                return data.get("current", 0)
            return 0

        return {
            "success": True,
            "hostname": results.get("hostname", "Unknown"),
            "serial": status.get("serial", "Unknown"),
            "model": results.get("model_name", results.get("model", "Unknown")),
            "firmware": status.get("version", "Unknown"),
            "build": status.get("build", 0),
            "cpu_percent": _current(res.get("cpu", [])),
            "memory_percent": _current(res.get("mem", [])),
            "disk_percent": _current(res.get("disk", [])),
            "session_count": _current(res.get("session", [])),
            "uptime": results.get("uptime", 0),
        }
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": f"Cannot connect to {device['ip']}:{device['port']}"}
    except requests.exceptions.HTTPError as e:
        return {"success": False, "error": f"HTTP error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
