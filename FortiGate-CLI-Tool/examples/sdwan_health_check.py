"""SD-WAN Health Check — collect SD-WAN diagnostics from a FortiGate."""

import os
from fortigate_cli import FortiGateCLI

fg = FortiGateCLI(
    host=os.environ.get("FORTIGATE_HOST", "192.168.1.1"),
    api_token=os.environ.get("FORTIGATE_API_TOKEN", "your_token_here"),
)

print("=" * 60)
print("SD-WAN HEALTH CHECK")
print("=" * 60)

# SD-WAN Health Check SLA Probes
result = fg.get_sdwan_health()
if result:
    for probe_name, members in result.data.items():
        print(f"\n  Probe: {probe_name}")
        if isinstance(members, dict):
            for member, stats in members.items():
                status = stats.get("status", "?")
                latency = stats.get("latency", "N/A")
                jitter = stats.get("jitter", "N/A")
                loss = stats.get("packet_loss", "N/A")
                if isinstance(latency, float):
                    print(f"    {member:<20} status={status:<5} latency={latency:.1f}ms jitter={jitter:.2f}ms loss={loss}")
                else:
                    print(f"    {member:<20} status={status}")
                # Check child interfaces (ADVPN shortcuts)
                for child_name, child_stats in stats.get("child_intfs", {}).items():
                    cl = child_stats.get("latency", "?")
                    cs = child_stats.get("status", "?")
                    if isinstance(cl, float):
                        print(f"      └─ {child_name:<18} status={cs:<5} latency={cl:.1f}ms")
else:
    print(f"  Failed: {result.error}")

# SD-WAN Members
print("\n" + "-" * 60)
result = fg.get_sdwan_members()
if result:
    print("  SD-WAN Members:")
    for member in result.data:
        if isinstance(member, dict):
            print(f"    {member.get('interface', '?'):<20} zone={member.get('zone', '?')}")

# BGP Neighbors
print("\n" + "-" * 60)
result = fg.get_bgp_neighbors()
if result:
    print("  BGP Neighbors:")
    for nbr in result.data:
        if isinstance(nbr, dict):
            print(f"    {nbr.get('neighbor_ip', '?'):<16} AS={nbr.get('remote_as', '?'):<6} state={nbr.get('state', '?')}")

fg.close()
