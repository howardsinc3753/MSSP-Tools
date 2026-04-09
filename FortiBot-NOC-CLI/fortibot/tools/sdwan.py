"""
FortiBot NOC - SD-WAN Status Tool
Retrieves SD-WAN member, health-check SLA, and service status via SSH.
"""
from fortibot.tools.ssh_cli import run_ssh_command


def run(device: dict) -> dict:
    """Get SD-WAN health check SLA status and member info."""
    if not device.get("ssh_user"):
        return {"success": False, "error": "SSH credentials required for SD-WAN diagnostics."}

    results = {}
    errors = []

    # Member status
    member_result = run_ssh_command(device, "diagnose sys sdwan member")
    if member_result.get("success"):
        results["member_status"] = member_result["output"]
    else:
        # Try older command
        member_result = run_ssh_command(device, "diagnose sys virtual-wan-link member")
        if member_result.get("success"):
            results["member_status"] = member_result["output"]
        else:
            errors.append("Could not retrieve SD-WAN member status.")

    # Health check SLA probes
    hc_result = run_ssh_command(device, "diagnose sys sdwan health-check")
    if hc_result.get("success"):
        results["health_check"] = hc_result["output"]
    else:
        hc_result = run_ssh_command(device, "diagnose sys virtual-wan-link health-check")
        if hc_result.get("success"):
            results["health_check"] = hc_result["output"]
        else:
            errors.append("Could not retrieve SD-WAN health check data.")

    # Service/rule status
    svc_result = run_ssh_command(device, "diagnose sys sdwan service")
    if svc_result.get("success"):
        results["service_status"] = svc_result["output"]

    if not results:
        return {
            "success": False,
            "error": "All SD-WAN diagnostic commands failed. "
                     "Ensure SSH credentials are correct and SD-WAN is configured.",
        }

    return {
        "success": True,
        "sdwan_data": results,
        "errors": errors if errors else None,
    }
