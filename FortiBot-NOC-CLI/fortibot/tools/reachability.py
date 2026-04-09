"""
FortiBot NOC - Reachability / Trace Diagnostic Tool
Runs ping, traceroute, routing lookup, and interface checks to diagnose
connectivity between two IP addresses through the FortiGate.
"""
from fortibot.tools import routing, interface_status
from fortibot.tools.ssh_cli import run_ssh_command


def run(device: dict, source_ip: str, dest_ip: str) -> dict:
    """Diagnose reachability between two IP addresses via the FortiGate.

    Runs:
    1. Routing table lookup for destination
    2. Interface status check
    3. Ping from FortiGate to destination
    4. Traceroute from FortiGate to destination

    Args:
        device: Device dict.
        source_ip: Source IP address.
        dest_ip: Destination IP address.

    Returns:
        dict with results from each diagnostic step.
    """
    results = {
        "success": True,
        "source_ip": source_ip,
        "dest_ip": dest_ip,
        "steps": {},
    }

    # Step 1: Route lookup for destination
    route_result = routing.run(device, filter_destination=dest_ip)
    if route_result.get("success"):
        matching_routes = route_result.get("routes", [])
        results["steps"]["route_lookup"] = {
            "success": True,
            "matching_routes": len(matching_routes),
            "routes": matching_routes[:5],  # Top 5 most specific
        }
        if not matching_routes:
            results["steps"]["route_lookup"]["finding"] = (
                f"No route found for {dest_ip}. Traffic will be dropped."
            )
    else:
        results["steps"]["route_lookup"] = {
            "success": False,
            "error": route_result.get("error", "Route lookup failed"),
        }

    # Step 2: Route lookup for source (return path)
    src_route = routing.run(device, filter_destination=source_ip)
    if src_route.get("success"):
        results["steps"]["return_route_lookup"] = {
            "success": True,
            "matching_routes": len(src_route.get("routes", [])),
            "routes": src_route.get("routes", [])[:3],
        }

    # Step 3: Interface status
    iface_result = interface_status.run(device)
    if iface_result.get("success"):
        results["steps"]["interfaces"] = {
            "success": True,
            "total": iface_result.get("interface_count", 0),
            "up": iface_result.get("up", 0),
            "down": iface_result.get("down", 0),
            "with_errors": iface_result.get("with_errors", 0),
        }
        # Check if the egress interface is up
        if route_result.get("success") and route_result.get("routes"):
            egress_iface = route_result["routes"][0].get("interface", "")
            for iface in iface_result.get("interfaces", []):
                if iface["name"] == egress_iface:
                    results["steps"]["egress_interface"] = {
                        "name": egress_iface,
                        "status": iface["status"],
                        "link": iface["link"],
                        "speed": iface["speed"],
                        "rx_errors": iface["rx_errors"],
                        "tx_errors": iface["tx_errors"],
                    }
                    break

    # Step 4: Ping from FortiGate (requires SSH)
    if device.get("ssh_user"):
        ping_result = run_ssh_command(device, f"execute ping {dest_ip}", timeout=30)
        if ping_result.get("success"):
            results["steps"]["ping"] = {
                "success": True,
                "output": ping_result["output"],
            }
            # Parse for packet loss
            output = ping_result["output"]
            if "0% packet loss" in output:
                results["steps"]["ping"]["finding"] = "Ping successful -- 0% packet loss."
            elif "100% packet loss" in output:
                results["steps"]["ping"]["finding"] = "Ping FAILED -- 100% packet loss."
            elif "packet loss" in output:
                results["steps"]["ping"]["finding"] = "Partial packet loss detected."
        else:
            results["steps"]["ping"] = {
                "success": False,
                "error": ping_result.get("error", "Ping failed"),
            }

        # Step 5: Traceroute from FortiGate
        trace_result = run_ssh_command(device, f"execute traceroute {dest_ip}", timeout=30)
        if trace_result.get("success"):
            results["steps"]["traceroute"] = {
                "success": True,
                "output": trace_result["output"],
            }
        else:
            results["steps"]["traceroute"] = {
                "success": False,
                "error": trace_result.get("error", "Traceroute failed"),
            }
    else:
        results["steps"]["ping"] = {
            "success": False,
            "error": "SSH not configured -- cannot run ping/traceroute.",
        }

    return results
