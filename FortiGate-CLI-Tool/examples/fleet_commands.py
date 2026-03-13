"""Fleet Commands — query multiple FortiGates at once."""

from fortigate_cli import FleetCLI

# Load devices from CSV config file
fleet = FleetCLI(timeout=30)
fleet.load_from_file("devices.csv")

# Or add devices programmatically
# fleet.add("192.168.1.1", "token1", name="HQ")
# fleet.add("192.168.2.1", "token2", name="Branch-1")

# Query system status across fleet
print("=" * 60)
print("FLEET: System Status")
print("=" * 60)
results = fleet.query_all("get system status")
for r in results:
    if r:
        d = r.data
        print(f"  {r.host:<16} {d.get('hostname', '?'):<25} {d.get('model_name', '?')} {d.get('model_number', '')}")
    else:
        print(f"  {r.host:<16} ERROR: {r.error}")

# Query SD-WAN health across fleet
print("\n" + "=" * 60)
print("FLEET: SD-WAN Health")
print("=" * 60)
results = fleet.query_all("diagnose sys sdwan health-check")
for r in results:
    print(f"\n--- {r.host} ---")
    if r:
        for probe, members in r.data.items():
            for member, stats in members.items() if isinstance(members, dict) else []:
                status = stats.get("status", "?")
                latency = stats.get("latency")
                lat_str = f"{latency:.1f}ms" if isinstance(latency, float) else "N/A"
                print(f"  {probe:<20} {member:<15} {status:<5} {lat_str}")
    else:
        print(f"  ERROR: {r.error}")
