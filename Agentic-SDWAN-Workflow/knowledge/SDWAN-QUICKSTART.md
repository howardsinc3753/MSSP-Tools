# FortiGate SD-WAN Quick Start

**Load this at the start of any SD-WAN conversation**

## Available Tools

| Tool | Use For |
|------|---------|
| `fortigate-sdwan-blueprint-planner` | Plan new sites, generate config |
| `fortigate-config-push` | Push config to device |
| `fortigate-sdwan-status` | Check tunnel/health status |
| `fortigate-sdwan-manifest-tracker` | Track device inventory |

## Deploy New Site (5 Steps)

```
1. generate-template     → CSV with recommended values
2. User fills WAN/LAN    → Only human input needed
3. plan-site             → 247-line FortiOS CLI
4. config-push           → Push to device via API
5. absorb to manifest    → Track the device
```

## Key Commands

```json
// Plan new site
{"tool": "fortigate-sdwan-blueprint-planner", "action": "generate-template"}
{"tool": "fortigate-sdwan-blueprint-planner", "action": "plan-site", "csv_path": "..."}

// Push config
{"tool": "fortigate-config-push", "target_ip": "x.x.x.x", "config_path": "..."}

// Verify
{"tool": "fortigate-sdwan-status", "target_ip": "x.x.x.x"}

// Track
{"tool": "fortigate-sdwan-manifest-tracker", "action": "absorb", "target_ip": "x.x.x.x"}
```

## Unique Per-Site Values (Auto-Calculated)

- Loopback: `172.16.0.{site_id}`
- VPN LocalID: `Br{site_id}-HUB1-VPN1`
- BGP Router ID: = Loopback

## Current Network

- **Hub**: 192.168.215.15 (loopbacks: 172.16.255.253, 172.16.255.252)
- **Spoke1**: 192.168.209.30 (loopback: 172.16.0.2)
- **Manifest**: `C:\ProgramData\Ulysses\config\sdwan-manifest.yaml`

## Full Docs

See: `SDWAN-SOLUTION-PACK-SKILLS.md`
