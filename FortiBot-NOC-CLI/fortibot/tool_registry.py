"""
FortiBot NOC - Tool Registry
Maps tool names to functions and Claude tool definitions for agentic AI.
"""
from fortibot.tools import (
    health_check,
    interface_status,
    routing,
    vpn,
    ha_status,
    sdwan,
    npu_status,
    firmware,
    fortiguard,
    sessions,
    config_backup,
    ssh_cli,
    bandwidth,
    network_analyzer,
    reachability,
)


# Each entry: name, description, function, input_schema, requires_ssh
TOOLS = [
    {
        "name": "health_check",
        "description": (
            "Get FortiGate device health: CPU, memory, disk usage, session count, "
            "uptime, hostname, serial, model, and firmware version. Use this for "
            "general health monitoring or morning checks."
        ),
        "function": health_check.run,
        "requires_ssh": False,
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "interface_status",
        "description": (
            "Get all network interface status including link state, speed, duplex, "
            "MAC address, IP address, traffic counters (bytes/packets), and error "
            "counts. Use this to investigate interface problems, link flaps, or errors."
        ),
        "function": interface_status.run,
        "requires_ssh": False,
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "routing_table",
        "description": (
            "Get the IPv4 routing table. Can optionally filter by a destination IP "
            "to find which routes would match that destination. Use this to verify "
            "routing paths, check for missing routes, or diagnose reachability."
        ),
        "function": routing.run,
        "requires_ssh": False,
        "input_schema": {
            "type": "object",
            "properties": {
                "filter_destination": {
                    "type": "string",
                    "description": "Optional IP to filter routes that match this destination.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "vpn_tunnels",
        "description": (
            "List all IPsec VPN tunnels with their configuration and operational status "
            "(up/down). Shows remote gateway, IKE version, interface binding, DPD settings, "
            "and traffic counters. Use this to check VPN health or troubleshoot tunnels."
        ),
        "function": vpn.run,
        "requires_ssh": False,
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "ha_status",
        "description": (
            "Check HA (High Availability) cluster status including mode "
            "(active-passive/active-active), sync state, peer nodes, heartbeat "
            "interfaces, and recent failovers. Use this when investigating "
            "failover events or HA sync issues."
        ),
        "function": ha_status.run,
        "requires_ssh": False,
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "sdwan_status",
        "description": (
            "Get SD-WAN health check SLA probe results, member interface status, "
            "and service rule status via SSH CLI commands. Use this to troubleshoot "
            "SD-WAN path selection, SLA violations, or link quality issues."
        ),
        "function": sdwan.run,
        "requires_ssh": True,
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "npu_offload",
        "description": (
            "Detect the NPU ASIC family (NP6/NP7/NP7Lite) and get hardware offload "
            "session statistics. Shows what percentage of traffic is offloaded to NPU "
            "vs software path. Use this for performance troubleshooting on hardware models."
        ),
        "function": npu_status.run,
        "requires_ssh": True,
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "firmware_check",
        "description": (
            "Check current firmware version and compare against available upgrades "
            "from FortiGuard. Shows if the device is current, how many patches behind, "
            "and lists available upgrade candidates."
        ),
        "function": firmware.run,
        "requires_ssh": False,
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "fortiguard_status",
        "description": (
            "Check FortiGuard subscription license status and signature update freshness "
            "for all services (AV, IPS, Web Filter, App Control, etc). Shows expiry dates "
            "and flags expired or soon-to-expire subscriptions."
        ),
        "function": fortiguard.run,
        "requires_ssh": False,
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "session_table",
        "description": (
            "Get active firewall sessions. Can filter by source IP, destination IP, "
            "or destination port. Shows protocol, policy ID, byte counters, and "
            "interface info. Use to check if traffic is being processed or to find "
            "specific flows."
        ),
        "function": sessions.run,
        "requires_ssh": False,
        "input_schema": {
            "type": "object",
            "properties": {
                "count": {
                    "type": "integer",
                    "description": "Number of sessions to return (default 20, max 1000).",
                },
                "filter_srcip": {
                    "type": "string",
                    "description": "Filter by source IP address.",
                },
                "filter_dstip": {
                    "type": "string",
                    "description": "Filter by destination IP address.",
                },
                "filter_dport": {
                    "type": "string",
                    "description": "Filter by destination port.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "config_backup",
        "description": (
            "Download a full configuration backup from the FortiGate. Returns the "
            "config content or saves to a file. Use for backup/archival or config review."
        ),
        "function": config_backup.run,
        "requires_ssh": False,
        "input_schema": {
            "type": "object",
            "properties": {
                "save_path": {
                    "type": "string",
                    "description": "Directory to save the backup file. If omitted, content is returned.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "ssh_command",
        "description": (
            "Execute an arbitrary CLI command on the FortiGate via SSH. Supports all "
            "read-only commands including 'get', 'show', 'diagnose', and 'execute ping', "
            "'execute traceroute'. Destructive commands are blocked for safety."
        ),
        "function": ssh_cli.run_ssh_command,
        "requires_ssh": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "FortiGate CLI command to execute.",
                },
            },
            "required": ["command"],
        },
    },
    {
        "name": "top_bandwidth",
        "description": (
            "Identify top bandwidth consumers from forward traffic logs. Shows top N "
            "source IPs ranked by total bytes with session counts and user info."
        ),
        "function": bandwidth.run,
        "requires_ssh": False,
        "input_schema": {
            "type": "object",
            "properties": {
                "top_n": {
                    "type": "integer",
                    "description": "Number of top consumers to return (default 10).",
                },
            },
            "required": [],
        },
    },
    {
        "name": "network_logs",
        "description": (
            "Retrieve traffic or event logs from the FortiGate. Supports filtering by "
            "source/destination IP. Mode can be 'traffic' for forward traffic or 'event' "
            "for system events. Use to investigate security events or traffic patterns."
        ),
        "function": network_analyzer.run,
        "requires_ssh": False,
        "input_schema": {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "description": "Log type: 'traffic' or 'event'.",
                    "enum": ["traffic", "event"],
                },
                "rows": {
                    "type": "integer",
                    "description": "Number of log entries (default 50, max 2000).",
                },
                "filter_srcip": {
                    "type": "string",
                    "description": "Filter by source IP.",
                },
                "filter_dstip": {
                    "type": "string",
                    "description": "Filter by destination IP.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "reachability_test",
        "description": (
            "Diagnose connectivity between a source IP and destination IP through the "
            "FortiGate. Runs route lookup, interface check, ping, and traceroute. "
            "Use this when someone reports 'IP X cannot reach IP Y'."
        ),
        "function": reachability.run,
        "requires_ssh": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "source_ip": {
                    "type": "string",
                    "description": "Source IP address (the host that cannot connect).",
                },
                "dest_ip": {
                    "type": "string",
                    "description": "Destination IP address (the target host).",
                },
            },
            "required": ["source_ip", "dest_ip"],
        },
    },
]


def get_tool_by_name(name: str) -> dict:
    """Return the tool entry matching the given name, or None."""
    for tool in TOOLS:
        if tool["name"] == name:
            return tool
    return None


def get_claude_tools() -> list:
    """Return tool definitions formatted for the Anthropic API tool_use."""
    claude_tools = []
    for tool in TOOLS:
        claude_tools.append({
            "name": tool["name"],
            "description": tool["description"],
            "input_schema": tool["input_schema"],
        })
    return claude_tools


def execute_tool(name: str, device: dict, args: dict = None) -> dict:
    """Execute a registered tool by name.

    Args:
        name: Tool name from the registry.
        device: Device configuration dict.
        args: Additional arguments specific to the tool.

    Returns:
        Tool result dict.
    """
    tool = get_tool_by_name(name)
    if not tool:
        return {"success": False, "error": f"Unknown tool: {name}"}

    args = args or {}
    func = tool["function"]

    # Determine how to call the function based on the tool
    if name == "ssh_command":
        command = args.get("command", "")
        return func(device, command)
    elif name == "routing_table":
        return func(device, filter_destination=args.get("filter_destination"))
    elif name == "session_table":
        return func(
            device,
            count=args.get("count", 20),
            filter_srcip=args.get("filter_srcip"),
            filter_dstip=args.get("filter_dstip"),
            filter_dport=args.get("filter_dport"),
        )
    elif name == "config_backup":
        return func(device, save_path=args.get("save_path"))
    elif name == "top_bandwidth":
        return func(device, top_n=args.get("top_n", 10))
    elif name == "network_logs":
        return func(
            device,
            mode=args.get("mode", "traffic"),
            rows=args.get("rows", 50),
            filter_srcip=args.get("filter_srcip"),
            filter_dstip=args.get("filter_dstip"),
        )
    elif name == "reachability_test":
        return func(
            device,
            source_ip=args.get("source_ip", ""),
            dest_ip=args.get("dest_ip", ""),
        )
    else:
        return func(device)
