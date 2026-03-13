# FortiGate CLI Tool

Query FortiGate devices and deploy configuration via the FortiOS REST API — no SSH or paramiko required.

## Disclaimer

This script is provided for educational and diagnostic purposes only. It is **NOT** an official Fortinet product, tool, or support utility, and is not endorsed, tested, or maintained by Fortinet, Inc. Use at your own risk.

## How It Works

The tool uses two approaches depending on the operation:

| Operation | Method | Endpoint |
|-----------|--------|----------|
| **Read** (get/show/diagnose) | Structured JSON API | `GET /api/v2/monitor/{resource}` |
| **Read config** (show commands) | CMDB API | `GET /api/v2/cmdb/{path}` |
| **Write** (config scripts) | Multipart file upload | `POST /api/v2/monitor/system/config-script/upload` |

**Requirements:** FortiOS 7.2+ with a REST API admin token (Bearer authentication).

## Quick Start

```bash
pip install -r requirements.txt
```

```python
from fortigate_cli import FortiGateCLI

fg = FortiGateCLI("192.168.1.1", api_token="your_token")

# Query — returns structured JSON (not CLI text)
result = fg.query("get system status")
print(result.data)  # {'hostname': '...', 'model_name': '...', ...}

# SD-WAN health checks
result = fg.get_sdwan_health()
for probe, members in result.data.items():
    print(f"{probe}: {members}")

# Read CMDB config (equivalent to "show system interface")
data = fg.get_cmdb("system/interface")

# Deploy configuration
result = fg.deploy_config('''
    config system interface
        edit "wan"
            set alias "WAN-Uplink"
        next
    end
''')
print(result.success)  # True
```

## Command Line Usage

```bash
# Query device status (returns structured JSON)
python fortigate_cli.py --host 192.168.1.1 --token $FG_TOKEN -q "get system status"

# SD-WAN health
python fortigate_cli.py --host 192.168.1.1 --token $FG_TOKEN -q "diagnose sys sdwan health-check"

# Read CMDB config
python fortigate_cli.py --host 192.168.1.1 --token $FG_TOKEN --cmdb "firewall/policy"

# Direct API endpoint access
python fortigate_cli.py --host 192.168.1.1 --token $FG_TOKEN --api-get "/monitor/system/performance/status"

# Deploy config script from file
python fortigate_cli.py --host 192.168.1.1 --token $FG_TOKEN -d config_script.txt

# Multi-device from config file
python fortigate_cli.py --config devices.csv -q "get system status"

# List all supported CLI → API mappings
python fortigate_cli.py --list-commands

# JSON output
python fortigate_cli.py --host 192.168.1.1 --token $FG_TOKEN -q "get system status" --json
```

## Supported CLI Command Mappings

| CLI Command | REST API Endpoint |
|-------------|-------------------|
| `get system status` | `/monitor/system/status` |
| `get system performance status` | `/monitor/system/performance/status` |
| `get system interface` | `/monitor/system/interface` |
| `get router info routing-table all` | `/monitor/router/ipv4` |
| `diagnose sys sdwan health-check` | `/monitor/virtual-wan/health-check` |
| `diagnose sys sdwan member` | `/monitor/virtual-wan/members` |
| `diagnose sys sdwan intf-sla-log` | `/monitor/virtual-wan/sla-log` |
| `get vpn ipsec tunnel summary` | `/monitor/vpn/ipsec` |
| `get router info bgp summary` | `/monitor/router/bgp/neighbors` |
| `diagnose sys ha status` | `/monitor/system/ha-peer` |
| `diagnose sys session stat` | `/monitor/firewall/session` |

For commands without a built-in mapping, use `--api-get` or `--cmdb` directly.

## API Token Setup

1. Log into FortiGate GUI
2. **System > Administrators > Create New > REST API Admin**
3. Set admin profile:
   - **Read-only** profile for queries
   - **Full access** profile if deploying config (`deploy_config()`)
4. Restrict trusted hosts to your management IP
5. Copy the generated API token

## Config Deployment Safety

Config scripts are validated before deployment:

| Action | Status |
|--------|--------|
| Config blocks (`config`, `set`, `edit`, `end`) | Allowed |
| Admin user changes (`config system admin`) | Always blocked |
| Password changes (`set password`) | Always blocked |
| Destructive ops (`factoryreset`, `reboot`, `shutdown`) | Always blocked |

## Multi-Device Fleet Mode

```python
from fortigate_cli import FleetCLI

fleet = FleetCLI()
fleet.add("192.168.1.1", "token1", name="HQ")
fleet.add("192.168.2.1", "token2", name="Branch-1")

# Or load from CSV
fleet.load_from_file("devices.csv")

# Query all devices
results = fleet.query_all("get system status")
for r in results:
    if r:
        print(f"{r.host}: {r.data.get('hostname')}")

# Deploy config to all devices
results = fleet.deploy_config_all(config_script)
```

## Files

```
FortiGate-CLI-Tool/
├── fortigate_cli.py        # Main tool (single file, no install needed)
├── requirements.txt        # Python dependencies
├── devices.csv.example     # Multi-device config template
├── README.md
├── LICENSE
└── examples/
    ├── basic_usage.py       # Single device queries
    ├── sdwan_health_check.py # SD-WAN diagnostics
    └── fleet_commands.py    # Multi-device fleet operations
```

## License

MIT License. See Fortinet disclaimer above.
