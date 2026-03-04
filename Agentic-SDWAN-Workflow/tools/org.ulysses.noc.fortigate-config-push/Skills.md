# FortiGate Config Push v2.0.0

## Purpose
Push FortiOS CLI configuration to a FortiGate device via SSH. Sends CLI commands directly - no API translation required.

## When to Use
- Deploying a new SD-WAN spoke/hub from blueprint
- Applying bulk configuration changes
- Automating FortiGate provisioning
- Any scenario where you have CLI config to push

## The Automation Gap This Closes

```
BEFORE (Human in loop):
  Blueprint -> CLI Config -> [USER PASTES VIA SSH] -> FortiGate

AFTER (100% AI):
  Blueprint -> CLI Config -> [THIS TOOL] -> FortiGate
```

## v2.0.0 Changes (GAP-26 Fix)

**Previous versions (v1.x)** tried CLI->API translation which failed for:
- `system settings` (no API mapping)
- Nested SD-WAN configs (parser couldn't handle 3+ levels)
- Multi-interface firewall policies (API format wrong)

**This version (v2.0.0)** uses SSH to push CLI directly - works for ALL config types.

## Parameters

### Required
| Parameter | Type | Description |
|-----------|------|-------------|
| target_ip | string | FortiGate management IP |

### Config Source (one required)
| Parameter | Type | Description |
|-----------|------|-------------|
| config_path | string | Path to CLI config file |
| config_text | string | CLI config as string |

### Optional
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| dry_run | boolean | false | Parse only, don't push |

## Usage Examples

### Push Config from File
```json
{
  "target_ip": "10.0.0.45",
  "config_path": "C:\\ProgramData\\Ulysses\\config\\blueprints\\site-07\\atomic-config-spoke-07.conf"
}
```

### Push Config from String
```json
{
  "target_ip": "10.0.0.45",
  "config_text": "config system global\nset hostname \"sdwan-spoke-07\"\nend"
}
```

### Dry Run (Parse Only)
```json
{
  "target_ip": "10.0.0.45",
  "config_path": "C:\\ProgramData\\Ulysses\\config\\blueprints\\site-07\\atomic-config-spoke-07.conf",
  "dry_run": true
}
```

## Full SD-WAN Deployment Workflow

### Step 1: Generate Config from Atomic Template
Use `ATOMIC_SPOKE_TEMPLATE.conf` and replace parameters:
- `{{SITE_ID}}` - Site number (e.g., 7)
- `{{HOSTNAME}}` - Device hostname (e.g., sdwan-spoke-07)
- `{{MANAGEMENT_IP}}` - WAN IP (e.g., 10.0.0.45)
- `{{LOOPBACK_IP}}` - Loopback: 172.16.0.{{SITE_ID}}
- `{{LAN_SUBNET}}`, `{{LAN_GATEWAY}}`, `{{LAN_MASK}}`
- `{{PSK_SECRET}}` - IPsec pre-shared key

### Step 2: Push Config (THIS TOOL)
```json
{
  "target_ip": "10.0.0.45",
  "config_path": "C:\\ProgramData\\Ulysses\\config\\blueprints\\site-07\\atomic-config-spoke-07.conf"
}
```

### Step 3: Verify Tunnels
```json
// fortigate-sdwan-status
{
  "target_ip": "10.0.0.45"
}
// Verify: HUB1-VPN1 UP, HUB1-VPN2 UP, BGP Established
```

## Config Format Requirements

### Flat CLI Format (CORRECT)
```
config system global
set hostname "sdwan-spoke-07"
end

config system interface
edit "port1"
set vdom "root"
set mode dhcp
next
end
```

### NOT Nested (WRONG)
```
config system global
  set hostname "sdwan-spoke-07"
  config system interface    <-- WRONG: no nesting
    edit "port1"
```

## Supported Config Sections

All FortiOS CLI config sections are supported via SSH push:

| CLI Section | Status |
|-------------|--------|
| system global | Supported |
| system interface | Supported |
| system settings | Supported |
| system sdwan | Supported |
| vpn ipsec phase1-interface | Supported |
| vpn ipsec phase2-interface | Supported |
| router static | Supported |
| router bgp | Supported |
| firewall address | Supported |
| firewall policy | Supported |
| system dhcp server | Supported |

## Output Example

### Success
```json
{
  "success": true,
  "target": "10.0.0.45",
  "method": "SSH_CLI",
  "sections_total": 12,
  "sections_success": 12,
  "sections_failed": 0,
  "pushed_at": "2026-01-25T18:30:00.000000",
  "results": [
    {"section": "system global", "success": true, "output": "OK"},
    {"section": "system interface", "success": true, "output": "OK"},
    {"section": "vpn ipsec phase1-interface", "success": true, "output": "OK"}
  ]
}
```

### Partial Failure
```json
{
  "success": false,
  "target": "10.0.0.45",
  "method": "SSH_CLI",
  "sections_total": 12,
  "sections_success": 11,
  "sections_failed": 1,
  "results": [
    {"section": "firewall policy", "success": false,
     "output": "Command fail. entry not found in datasource"}
  ]
}
```

### Dry Run
```json
{
  "success": true,
  "mode": "dry_run",
  "target": "10.0.0.45",
  "sections_parsed": 12,
  "sections": [
    {"name": "system global", "lines": 6},
    {"name": "system interface", "lines": 45},
    {"name": "vpn ipsec phase1-interface", "lines": 40}
  ]
}
```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| No SSH password | Device not in credentials | Add ssh_password to fortigate_credentials.yaml |
| SSH auth failed | Wrong password | Verify ssh_username and ssh_password |
| Connection timeout | Network issue | Check firewall allows SSH (port 22) |
| Command fail | Invalid CLI syntax | Check config format matches FortiOS version |

## Prerequisites

1. **SSH Credentials**: Device must have `ssh_username` and `ssh_password` in credentials file
2. **Network Access**: Tool must reach FortiGate on SSH/22
3. **SSH Access**: FortiGate must have SSH access enabled on management interface

### Credentials File Location
```
C:\ProgramData\Ulysses\config\fortigate_credentials.yaml
```

### Credentials Format
```yaml
devices:
  sdwan-spoke-07:
    host: 10.0.0.45
    ssh_username: admin
    ssh_password: "FG@dm!n2026!"
    api_token: <optional>
    verify_ssl: false
default_lookup:
  10.0.0.45: sdwan-spoke-07
```

## Related Tools
- `fortigate-sdwan-blueprint-planner` - Generate config
- `fortigate-sdwan-status` - Verify tunnels
- `fortigate-sdwan-manifest-tracker` - Track device
- `fortigate-health-check` - Basic health check

## Known Gaps

### GAP-24: Firewall Policy Interface Binding
Firewall policies using tunnel interfaces directly (`dstintf HUB1-VPN1`) will BLOCK SD-WAN member binding.

**Solution:** Always use SD-WAN zones in firewall policies:
```
set dstintf "SDWAN_OVERLAY"   # CORRECT
set dstintf "HUB1-VPN1"       # WRONG - blocks SD-WAN binding
```

### GAP-25: SD-WAN Neighbor Required
SD-WAN neighbor config is required for BGP/SLA integration:
```
config system sdwan
config neighbor
edit "172.16.255.252"
set member 3 4
set health-check "HUB_Health"
set sla-id 1
next
end
end
```

### GAP-27: Static Route Equal Distance
Static routes to hub loopbacks must have EQUAL distance for BGP ECMP:
```
edit 900
set dst 172.16.255.252 255.255.255.255
set device "HUB1-VPN1"
next
edit 902
set dst 172.16.255.252 255.255.255.255
set device "HUB1-VPN2"
next
```
Do NOT set `distance 15` on backup routes - both routes must be equal for BGP multipath.

## Security Notes
- Uses SSH with password authentication
- Credentials stored in production path: `C:\ProgramData\Ulysses\config\`
- SSH host key verification uses AutoAddPolicy (acceptable for lab environments)
