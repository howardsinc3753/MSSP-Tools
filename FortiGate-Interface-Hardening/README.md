# FortiGate Unused Interface Hardening Tool

Automatically discovers and disables unused physical interfaces on any FortiGate model. Reduces attack surface by ensuring only operational ports remain admin-enabled.

## Disclaimer

This script is provided for educational and diagnostic purposes only. It is **NOT** an official Fortinet product, tool, or support utility, and is not endorsed, tested, or maintained by Fortinet, Inc. Use at your own risk. Always test in a non-production environment first.

## The Problem

Every FortiGate model ships with a different set of physical interfaces — from 4 ports on a FortiWiFi 50G to 30+ on a FortiGate 3000 series. After deployment, many ports sit unused with cables unplugged, but they remain **admin-enabled** by default. Each one is a potential attack vector:

- An attacker with physical access can plug into an unused port
- Compliance frameworks (CIS FortiGate Benchmark, NIST 800-41) require disabling unused interfaces
- MSSP audits flag admin-enabled interfaces with no link as a hardening gap

The challenge: with **50+ FortiGate hardware models**, each with different interface names and layouts, you can't maintain a static list. You need dynamic discovery.

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│  1. DISCOVER          API: /monitor/system/             │
│     Query all         available-interfaces              │
│     physical          ─── Returns link status,          │
│     interfaces            type, speed, IP               │
│                                                         │
│  2. CROSS-REFERENCE   API: /cmdb/system/sdwan           │
│     Check every            /cmdb/vpn.ipsec/phase1       │
│     config section         /cmdb/firewall/policy        │
│     that could             /cmdb/system.dhcp/server     │
│     reference an           /cmdb/system/ha              │
│     interface              /cmdb/system/zone            │
│                            /cmdb/router/static          │
│                                                         │
│  3. CLASSIFY                                            │
│     ┌──────────────┬──────────────┬──────────────┐      │
│     │ Link Up      │ Link Down    │ Link Down    │      │
│     │ = Active     │ + Config Ref │ + No Refs    │      │
│     │ (no change)  │ = WARN ONLY  │ = DISABLE    │      │
│     └──────────────┴──────────────┴──────────────┘      │
│                                                         │
│  4. GENERATE          config system interface           │
│     Hardening +           edit "lan1"                   │
│     Rollback                  set status down           │
│     scripts               next                          │
│                       end                               │
│                                                         │
│  5. DEPLOY (optional) API: config-script/upload         │
└─────────────────────────────────────────────────────────┘
```

## Safety Guarantees

The tool will **NEVER** disable an interface that:

| Condition | Example |
|-----------|---------|
| Has link up (cable plugged in) | `wan`, `lan3` with active link |
| Is referenced in SD-WAN config | SD-WAN member interface |
| Is bound to a VPN tunnel | IPsec phase1 binding |
| Is used in a firewall policy | Source or destination interface |
| Has a DHCP server configured | `lan` serving DHCP to clients |
| Is an HA heartbeat interface | `ha1`, `ha2` |
| Is in a zone | SD-WAN zone member |
| Is in a static route | Gateway interface |
| Has an IP address assigned | Management or service interface |
| Is a management port | `mgmt`, `mgmt1`, `mgmt2` |
| Is a hardware switch parent | `lan` (aggregate of `lan1`-`lan4`) |

A **rollback script** is always generated alongside the hardening script.

## Quick Start

```bash
pip install -r requirements.txt
```

### Audit Only (Dry-Run — Default)

```bash
python fortigate_harden_interfaces.py \
    --host 192.168.1.1 \
    --token $FORTIGATE_API_TOKEN
```

Output:
```
======================================================================
  FORTIGATE INTERFACE HARDENING AUDIT
======================================================================
  Device:    Branch-Office-1 (192.168.1.1)
  Model:     FortiWiFi 50G-5G
======================================================================

  Total physical interfaces: 7
  Active (link up):          2
  Already disabled:          1

  ACTIVE INTERFACES (link up — no change)
  wan             physical       1000       sdwan-member, vpn:HUB1-VPN1
  lan3            physical       1000       -

  UNUSED INTERFACES — CANDIDATES FOR DISABLING (4)
  lan1            physical       down       No link, no config references
  lan2            physical       down       No link, no config references
  a               physical       down       No link, no config references
  wwan            physical       down       No link, no config references

  ALREADY ADMIN DISABLED (1)
    modem

  To apply these changes, re-run with --deploy flag.
======================================================================
```

### Save Scripts for Review

```bash
python fortigate_harden_interfaces.py \
    --host 192.168.1.1 \
    --token $FORTIGATE_API_TOKEN \
    --save-scripts
```

Creates:
- `harden_Branch-Office-1.txt` — Hardening script
- `rollback_Branch-Office-1.txt` — Rollback script

### Deploy to Device

```bash
python fortigate_harden_interfaces.py \
    --host 192.168.1.1 \
    --token $FORTIGATE_API_TOKEN \
    --deploy
```

### Fleet Mode (Multiple Devices)

```bash
# Audit all devices
python fortigate_harden_interfaces.py --config devices.csv

# Audit and save scripts for each device
python fortigate_harden_interfaces.py --config devices.csv --save-scripts

# Deploy to all devices
python fortigate_harden_interfaces.py --config devices.csv --deploy
```

### JSON Output (for Automation)

```bash
python fortigate_harden_interfaces.py \
    --host 192.168.1.1 \
    --token $FORTIGATE_API_TOKEN \
    --json
```

## Python API

```python
from fortigate_harden_interfaces import InterfaceAnalyzer

# Audit a device
with InterfaceAnalyzer("192.168.1.1", api_token="your_token") as analyzer:
    report = analyzer.audit()
    report.print_summary()

    # View generated scripts
    print(report.hardening_script())
    print(report.rollback_script())

    # Export as JSON
    data = report.to_dict()

# Deploy hardening
with InterfaceAnalyzer("192.168.1.1", api_token="your_token") as analyzer:
    report = analyzer.harden(deploy=True)
    if report.deploy_success:
        print(f"Disabled {len(report.candidates)} unused interfaces")
```

## API Token Requirements

| Permission | Needed For |
|------------|-----------|
| `sysgrp: read` | Reading interface config, HA, zones |
| `netgrp: read` | Reading SD-WAN, routing, VPN config |
| `fwgrp: read` | Reading firewall policies |
| `sysgrp: read-write` | Deploying config changes (`--deploy`) |

Minimum profile for audit-only: `super_admin_readonly`
Minimum profile for deploy: `super_admin` or custom with `sysgrp: read-write`

## Files

```
FortiGate-Interface-Hardening/
├── fortigate_harden_interfaces.py  # Main tool (single file)
├── requirements.txt                # Python dependencies
├── devices.csv.example             # Multi-device config template
├── README.md
└── LICENSE
```

## License

MIT License. See Fortinet disclaimer above.
