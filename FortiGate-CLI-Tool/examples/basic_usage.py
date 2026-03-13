"""Basic usage — connect to a FortiGate and query device status."""

import os
from fortigate_cli import FortiGateCLI

# Initialize — use env vars or pass directly
fg = FortiGateCLI(
    host=os.environ.get("FORTIGATE_HOST", "192.168.1.1"),
    api_token=os.environ.get("FORTIGATE_API_TOKEN", "your_token_here"),
)

# Query system status (returns structured JSON)
result = fg.get_system_status()
if result:
    print(f"Hostname: {result.data.get('hostname')}")
    print(f"Model: {result.data.get('model_name')} {result.data.get('model_number')}")

# Query routing table
result = fg.get_routing_table()
if result:
    print(f"\nRouting table: {len(result.data)} routes")
    for route in result.data[:5]:
        print(f"  {route['ip_mask']:<20} via {route['gateway']:<16} dev {route['interface']}")

# Query CPU/memory performance
result = fg.get_performance()
if result:
    cpu = result.data.get("cpu", {})
    mem = result.data.get("mem", {})
    print(f"\nCPU: {100 - cpu.get('idle', 0):.0f}% used")
    if isinstance(mem, dict) and mem.get("total"):
        print(f"Memory: {mem['used']/mem['total']*100:.1f}% used")

# Read CMDB config (equivalent to "show system interface")
data = fg.get_cmdb("system/interface")
for iface in data.get("results", [])[:5]:
    print(f"  {iface['name']:<20} ip={iface.get('ip', 'N/A'):<20} status={iface.get('status')}")

fg.close()
