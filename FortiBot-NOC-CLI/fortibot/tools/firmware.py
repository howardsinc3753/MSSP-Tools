"""
FortiBot NOC - Firmware Check Tool
Checks current firmware and available upgrades via FortiGuard.
"""
import re
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _parse_version(v: str) -> tuple:
    clean = v.strip().lstrip("vV")
    m = re.match(r"(\d+)\.(\d+)\.(\d+)", clean)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    return (0, 0, 0)


def run(device: dict) -> dict:
    """Check current firmware and compare against available versions."""
    base = f"https://{device['ip']}:{device['port']}"
    headers = {"Authorization": f"Bearer {device['api_token']}"}

    try:
        status = requests.get(
            f"{base}/api/v2/monitor/system/status",
            headers=headers, verify=False, timeout=10,
        ).json()

        results = status.get("results", {})
        hostname = results.get("hostname", "unknown")
        raw_version = status.get("version", "unknown")
        build = status.get("build", 0)
        model = results.get("model_name", results.get("model", "unknown"))
        current = _parse_version(raw_version)
        train = f"{current[0]}.{current[1]}"

        result = {
            "success": True,
            "hostname": hostname,
            "model": model,
            "current_firmware": raw_version,
            "build": build,
            "train": train,
        }

        # Try FortiGuard firmware endpoint
        try:
            fw_resp = requests.get(
                f"{base}/api/v2/monitor/system/firmware",
                headers=headers, verify=False, timeout=10,
            ).json()

            available = []
            fw_results = fw_resp.get("results", {})
            if isinstance(fw_results, dict):
                for entry in fw_results.get("available", []):
                    ver_str = entry.get("version", "")
                    if ver_str:
                        available.append(ver_str)

            candidates = [v for v in available if _parse_version(v) > current]
            same_train = [v for v in candidates if v.lstrip("vV").startswith(train)]

            result["available_upgrades"] = candidates[:10]
            result["same_train_upgrades"] = same_train
            result["is_latest_in_train"] = len(same_train) == 0
            result["fortiguard_reachable"] = True

            if same_train:
                result["verdict"] = (
                    f"{hostname} running FortiOS {raw_version} (build {build}). "
                    f"{len(same_train)} patch(es) available in {train} train."
                )
            elif candidates:
                result["verdict"] = (
                    f"{hostname} running FortiOS {raw_version} (build {build}). "
                    f"Latest in {train} train. Newer trains available."
                )
            else:
                result["verdict"] = (
                    f"{hostname} running FortiOS {raw_version} (build {build}). "
                    "Firmware is current."
                )
        except Exception:
            result["fortiguard_reachable"] = False
            result["verdict"] = (
                f"{hostname} running FortiOS {raw_version} (build {build}). "
                "Could not reach FortiGuard to check for updates."
            )

        return result
    except Exception as e:
        return {"success": False, "error": str(e)}
