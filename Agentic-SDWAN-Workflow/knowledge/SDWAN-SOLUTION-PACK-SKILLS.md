# FortiGate SD-WAN Solution Pack - AI Skills Guide

**Entry Point for AI Agents**

This document brings you up to speed on the SD-WAN automation capabilities.
Read this FIRST before performing any SD-WAN operations.

---

## What This Solution Pack Does

Fully automates FortiGate SD-WAN deployment and management:
- **Plan** new SD-WAN sites with unique values
- **Deploy** configuration to devices via API (no human paste)
- **Verify** tunnel status and health
- **Track** all devices in a central manifest

**Human provides:** WAN IP (from ISP), LAN subnet
**AI handles:** Everything else - 100% automated

---

## Tool Inventory

### Deployment Tools

| Tool | Version | Purpose |
|------|---------|---------|
| `fortigate-sdwan-blueprint-planner` | 1.0.2 | Generate CSV templates + FortiOS CLI config |
| `fortigate-config-push` | 1.0.0 | Push CLI config to device via REST API |
| `fortigate-sdwan-manifest-tracker` | 1.0.1 | Track devices in central manifest |

### Diagnostic Tools

| Tool | Version | Purpose |
|------|---------|---------|
| `fortigate-sdwan-status` | 1.0.0 | Check SD-WAN health, tunnels, SLA |
| `fortigate-health-check` | 1.0.1 | Basic device health (CPU, memory, uptime) |

### Configuration Tools

| Tool | Version | Purpose |
|------|---------|---------|
| `fortigate-sdwan-zone` | 1.0.0 | Create/manage SD-WAN zones |
| `fortigate-sdwan-member` | 1.0.2 | Add interfaces to SD-WAN |
| `fortigate-sdwan-neighbor` | 1.1.0 | Configure SD-WAN BGP neighbors |
| `fortigate-sdwan-health-check` | 1.1.0 | Create SD-WAN health checks (spoke/hub modes) |

---

## Primary Workflow: Deploy New SD-WAN Site

```
USER: "Deploy new SD-WAN spoke site"
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: Generate Template                                  │
│  Tool: fortigate-sdwan-blueprint-planner                    │
│  Action: generate-template                                  │
│                                                             │
│  AI reads manifest, calculates:                             │
│  • Next site ID (e.g., 3)                                   │
│  • Next loopback IP (172.16.0.3)                            │
│  • Next member seq-nums (3, 4)                              │
│  • Unique VPN localids (Br3-HUB1-VPN1)                      │
│  • Hub connection info from existing hub in manifest        │
│                                                             │
│  Returns: CSV template with recommended values              │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
    USER: Fills in WAN IP, LAN subnet in CSV
    USER: "Done, generate the config"
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: Generate Config                                    │
│  Tool: fortigate-sdwan-blueprint-planner                    │
│  Action: plan-site                                          │
│  Params: csv_path = "...\Branch3_template.csv"              │
│                                                             │
│  AI validates input, generates 247-line FortiOS CLI:        │
│  • System hostname                                          │
│  • Interfaces (WAN, LAN, Loopback, VPN tunnels)             │
│  • IPsec Phase1/Phase2 with ADVPN                           │
│  • SD-WAN zones, members, health-check, neighbor            │
│  • BGP with neighbor-group and neighbor-range               │
│  • Firewall policies                                        │
│                                                             │
│  Returns: Branch3_config.txt                                │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 3: Push Config to Device                              │
│  Tool: fortigate-config-push                                │
│  Params: target_ip, config_path                             │
│                                                             │
│  AI parses CLI into API calls, pushes to FortiGate:         │
│  • 16+ config blocks pushed automatically                   │
│  • Handles PUT (update) and POST (create)                   │
│  • Reports success/failure per block                        │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 4: Verify Deployment                                  │
│  Tool: fortigate-sdwan-status                               │
│  Params: target_ip                                          │
│                                                             │
│  AI checks:                                                 │
│  • IPsec tunnels UP                                         │
│  • SD-WAN health check passing                              │
│  • BGP neighbors established                                │
│                                                             │
│  Returns: HUB1-VPN1 ✓ UP, HUB1-VPN2 ✓ UP                    │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 5: Track in Manifest                                  │
│  Tool: fortigate-sdwan-manifest-tracker                     │
│  Action: absorb                                             │
│  Params: target_ip                                          │
│                                                             │
│  AI onboards device to manifest:                            │
│  • Captures all interfaces, IPsec, SD-WAN, BGP settings     │
│  • Tracks unique per-site values                            │
│  • Ready for next deployment                                │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
AI: "Branch3 deployed. Tunnels UP. Added to manifest."
```

---

## Quick Reference: Tool Parameters

### fortigate-sdwan-blueprint-planner

```json
// Generate template
{"action": "generate-template"}

// Generate config from filled template
{"action": "plan-site", "csv_path": "C:\\...\\template.csv", "add_to_manifest": true}
```

### fortigate-config-push

```json
// Push config to device
{"target_ip": "192.168.1.99", "config_path": "C:\\...\\config.txt"}

// Dry run (parse only)
{"target_ip": "192.168.1.99", "config_path": "...", "dry_run": true}
```

### fortigate-sdwan-manifest-tracker

```json
// Onboard device
{"action": "absorb", "target_ip": "192.168.1.99"}

// List tracked devices
{"action": "list"}

// Get device details
{"action": "get", "device_key": "spoke_192_168_1_99"}

// Export full manifest
{"action": "export"}
```

### fortigate-sdwan-status

```json
// Check SD-WAN health
{"target_ip": "192.168.1.99"}
```

---

## Architecture: SD-WAN Network Model

```
                    ┌─────────────────────┐
                    │       HUB           │
                    │  10.0.1.1     │
                    │                     │
                    │  Loopbacks:         │
                    │  • Hub_Lo: 172.16.255.253 (health-check)
                    │  • BGP_Lo: 172.16.255.252 (peering)
                    │                     │
                    │  IPsec (dynamic):   │
                    │  • SPOKE_VPN1 (net-id: 1)
                    │  • SPOKE_VPN2 (net-id: 2)
                    │                     │
                    │  BGP: AS 65000      │
                    │  neighbor-range: 172.16.0.0/16
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │    SPOKE 1      │ │    SPOKE 2      │ │    SPOKE 3      │
    │  10.0.0.30 │ │  (future)       │ │  (planned)      │
    │                 │ │                 │ │                 │
    │  Loopback:      │ │  Loopback:      │ │  Loopback:      │
    │  172.16.0.2     │ │  172.16.0.X     │ │  172.16.0.3     │
    │                 │ │                 │ │                 │
    │  IPsec:         │ │                 │ │                 │
    │  • HUB1-VPN1    │ │                 │ │                 │
    │  • HUB1-VPN2    │ │                 │ │                 │
    │                 │ │                 │ │                 │
    │  BGP: AS 65000  │ │                 │ │                 │
    │  peer: Hub_Lo   │ │                 │ │                 │
    └─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

## Manifest Location

```
C:\ProgramData\Ulysses\config\sdwan-manifest.yaml
```

Contains:
- Network metadata (AS number, loopback range)
- All devices (hub + spokes)
- Per-device: interfaces, IPsec, SD-WAN, BGP, policies, addresses

---

## Unique Per-Site Values

These values MUST be unique per site (tracked in manifest):

| Value | Pattern | Example |
|-------|---------|---------|
| Site ID | Sequential integer | 1, 2, 3... |
| Loopback IP | 172.16.0.{site_id} | 172.16.0.3 |
| VPN LocalID | Br{site_id}-HUB1-VPN1 | Br3-HUB1-VPN1 |
| SD-WAN Member Seq | site_id * 100 | 300, 301 |
| BGP Router ID | = Loopback IP | 172.16.0.3 |

---

## Troubleshooting

### Tunnel Not Coming Up

1. Check IPsec status:
   ```json
   {"tool": "fortigate-sdwan-status", "target_ip": "..."}
   ```

2. Verify PSK matches hub

3. Check network-id matches (VPN1 = 1, VPN2 = 2)

4. Ensure hub allows dynamic peers (type: dynamic)

### Health Check Failing

1. Verify hub loopback is correct (172.16.255.253)

2. Check firewall policy allows ICMP on overlay

3. For spoke: `embed-measured-health enable`

4. For hub: `detect-mode remote`

### BGP Not Establishing

1. Check AS number matches (65000)

2. Verify update-source is loopback

3. Ensure hub has neighbor-range covering 172.16.0.0/16

---

## Related Files

| File | Purpose |
|------|---------|
| `SDWAN-API-REFERENCE.md` | FortiGate API endpoints |
| `SDWAN-CORPUS.md` | Detailed configuration examples |
| `SDWAN-TOOL-TARGETS.md` | Original development roadmap |

---

## Version History

| Date | Change |
|------|--------|
| 2026-01-17 | Initial release with full deployment workflow |
| 2026-01-17 | Added fortigate-config-push for 100% automation |
