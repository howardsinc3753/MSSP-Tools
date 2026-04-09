"""
FortiBot NOC - NPU / ASIC Offload Status Tool
Detects ASIC family from model and runs NPU session-stats via SSH.
"""
import re
import requests
import urllib3
from fortibot.tools.ssh_cli import run_ssh_command

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ASIC_FAMILIES = {
    "NP6": {
        "models": ["FG-600D", "FG-800D", "FG-1000D", "FG-1200D", "FG-1500D", "FG-3000D"],
        "cmd": "diagnose npu np6 session-stats",
    },
    "NP6XLite": {
        "models": ["FG-100F", "FG-101F", "FG-200F", "FG-201F"],
        "cmd": "diagnose npu np6xlite session-stats",
    },
    "NP7": {
        "models": ["FG-1800F", "FG-2600F", "FG-3700F", "FG-4200F", "FG-4400F",
                    "FG-600F", "FG-601F", "FG-400F", "FG-401F", "FG-3000F"],
        "cmd": "diagnose npu np7 session-stats",
    },
    "NP7Lite": {
        "models": ["FG-70G", "FG-71G", "FG-90G", "FG-91G", "FG-120G", "FG-121G"],
        "cmd": "diagnose npu np7lite session-stats",
    },
}


def _normalize_model(raw: str) -> str:
    s = raw.strip()
    s = re.sub(r"^FortiGate-", "FG-", s, flags=re.IGNORECASE)
    s = re.sub(r"^FGT-", "FG-", s, flags=re.IGNORECASE)
    return s


def _detect_family(model: str):
    norm = _normalize_model(model)
    for key, fam in ASIC_FAMILIES.items():
        for m in fam["models"]:
            if m in norm or norm in m:
                return key, fam
    if "vm" in norm.lower() or "virtual" in norm.lower():
        return "SW", None
    return "UNKNOWN", None


def run(device: dict) -> dict:
    """Detect NPU ASIC family and get offload stats via SSH."""
    base = f"https://{device['ip']}:{device['port']}"
    headers = {"Authorization": f"Bearer {device['api_token']}"}

    try:
        status = requests.get(
            f"{base}/api/v2/monitor/system/status",
            headers=headers, verify=False, timeout=10,
        ).json()
        results = status.get("results", {})
        raw_model = results.get("model", "") or results.get("model_name", "")
    except Exception as e:
        return {"success": False, "error": f"REST API error: {e}"}

    family_key, family = _detect_family(raw_model)

    result = {
        "success": True,
        "model": raw_model,
        "asic_family": family_key,
        "has_npu": family_key not in ("SW", "UNKNOWN"),
    }

    if family_key == "SW":
        result["verdict"] = f"{raw_model} uses software-path forwarding (no NPU)."
        return result

    if family_key == "UNKNOWN":
        result["verdict"] = f"Model '{raw_model}' is not in the ASIC lookup table."
        return result

    if not device.get("ssh_user"):
        result["verdict"] = f"{raw_model} has {family_key} NPU but SSH is not configured."
        return result

    ssh_result = run_ssh_command(device, family["cmd"])
    if not ssh_result.get("success"):
        result["ssh_error"] = ssh_result.get("error", "SSH failed")
        result["verdict"] = f"NPU command failed: {result['ssh_error']}"
        return result

    output = ssh_result["output"]
    result["raw_output"] = output

    # Parse session stats
    total_match = re.search(r"total\s+sessions?\s*[=:]\s*(\d+)", output, re.IGNORECASE)
    offload_match = re.search(r"offload(?:ed)?\s+sessions?\s*[=:]\s*(\d+)", output, re.IGNORECASE)

    total = int(total_match.group(1)) if total_match else 0
    offloaded = int(offload_match.group(1)) if offload_match else 0
    pct = (offloaded / total * 100) if total > 0 else 0

    result["total_sessions"] = total
    result["offloaded_sessions"] = offloaded
    result["offload_percent"] = round(pct, 2)

    if pct > 90:
        result["verdict"] = f"{family_key} offload excellent ({pct:.1f}%)."
    elif pct >= 70:
        result["verdict"] = f"{family_key} offload acceptable ({pct:.1f}%). Review policy config."
    elif pct >= 50:
        result["verdict"] = f"{family_key} offload elevated SW path ({pct:.1f}%). Check UTM policies."
    else:
        result["verdict"] = f"{family_key} offload critically low ({pct:.1f}%). Investigate immediately."

    return result
