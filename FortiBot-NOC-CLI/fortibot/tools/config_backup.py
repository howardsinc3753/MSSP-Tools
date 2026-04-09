"""
FortiBot NOC - Configuration Backup Tool
Exports FortiGate configuration via REST API.
"""
import json
import ssl
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def run(device: dict, save_path: str = None) -> dict:
    """Download FortiGate configuration backup.

    Args:
        device: Device dict with ip, port, api_token.
        save_path: Directory to save the backup file. If None, returns content.

    Returns:
        dict with success, backup content or file path, and metadata.
    """
    base = f"https://{device['ip']}:{device['port']}"
    headers = {"Authorization": f"Bearer {device['api_token']}"}

    try:
        # Get device info for metadata
        status = requests.get(
            f"{base}/api/v2/monitor/system/status",
            headers=headers, verify=False, timeout=10,
        ).json()
        results = status.get("results", {})
        hostname = results.get("hostname", "unknown")
        serial = status.get("serial", "unknown")
        firmware = status.get("version", "unknown")

        # Download backup — try GET first (FortiOS 7.0-7.4), fall back to POST (7.6+)
        url = f"{base}/api/v2/monitor/system/config/backup?destination=file&scope=global"
        config_content = None

        try:
            resp = requests.get(url, headers=headers, verify=False, timeout=60)
            resp.raise_for_status()
            config_content = resp.text
        except (requests.exceptions.HTTPError, Exception):
            # GET failed — try POST (FortiOS 7.6+)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            post_url = f"{base}/api/v2/monitor/system/config/backup"
            body = json.dumps({
                "destination": "file",
                "scope": "global",
            }).encode("utf-8")

            req = urllib.request.Request(post_url, data=body, method="POST")
            req.add_header("Authorization", f"Bearer {device['api_token']}")
            req.add_header("Content-Type", "application/json")

            with urllib.request.urlopen(req, timeout=60, context=ctx) as post_resp:
                config_content = post_resp.read().decode("utf-8", errors="replace")

        result = {
            "success": True,
            "hostname": hostname,
            "serial": serial,
            "firmware": firmware,
            "backup_size_bytes": len(config_content.encode("utf-8")),
            "backup_timestamp": datetime.now().isoformat(),
        }

        if save_path:
            backup_dir = Path(save_path)
            backup_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_host = "".join(c if c.isalnum() or c in "-_" else "_" for c in hostname)
            filename = f"{safe_host}_{serial}_{ts}.conf"
            filepath = backup_dir / filename
            filepath.write_text(config_content, encoding="utf-8")
            result["saved_to"] = str(filepath)
        else:
            # Truncate for display if very large
            if len(config_content) > 50000:
                result["config_content"] = config_content[:50000] + "\n... [TRUNCATED]"
                result["truncated"] = True
            else:
                result["config_content"] = config_content

        return result

    except urllib.error.HTTPError as e:
        return {"success": False, "error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
