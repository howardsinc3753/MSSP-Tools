# FortiGate SD-WAN Manifest Tracker

## Purpose
Single source of truth for SD-WAN network inventory and configuration. Absorbs FortiGate device configurations and tracks all unique per-site settings for blueprint planning and deployment automation.

## When to Use
- Onboarding a new SD-WAN spoke or hub into inventory
- Auditing existing SD-WAN device configurations
- Planning new deployments with unique per-site variables
- Tracking configuration drift across the SD-WAN network
- Generating input data for blueprint templates

## Manifest Location
```
C:/ProgramData/Ulysses/config/sdwan-manifest.yaml
```

## What It Tracks (Per Device)

### Device Identity
- hostname, serial_number, firmware, model
- management_ip, vdom, role (hub/spoke)

### Interfaces
- Physical interfaces (WAN, LAN)
- Tunnel interfaces (IPsec VPNs)
- Loopback interfaces (BGP peering, health checks)
- VLANs and aggregates

### IPsec Configuration
- Phase1: name, type, remote_gw, localid, network_id, auto-discovery settings
- Phase2: proposal, auto-negotiate

### SD-WAN Configuration
- Zones: name, advpn_select, advpn_health_check
- Members: seq_num, interface, zone, source, priority
- Health Checks: name, server, protocol, detect_mode, SLA thresholds
- Neighbors: ip, members, route_metric, health_check
- Services/Rules: name, mode, dst, src, priority_members, SLA binding

### BGP Configuration
- AS number, router_id
- Neighbors (static BGP peers)
- Neighbor Groups (for dynamic ADVPN peers)
- Neighbor Ranges (dynamic peer acceptance)
- Network advertisements

### Firewall Configuration
- Policies: srcintf, dstintf, srcaddr, dstaddr, NAT, action
- Address objects and groups
- Static routes

## Parameters

### Actions

| Action | Description | Required Params |
|--------|-------------|-----------------|
| `absorb` | Onboard device (create or update) | target_ip |
| `list` | List all tracked devices | - |
| `get` | Get full device manifest entry | device_key |
| `remove` | Remove device from tracking | device_key |
| `update-license` | Assign license to device (FortiFlex or Standard) | device_key, license_type, + type-specific params |
| `export` | Export complete manifest | - |

### Parameter Details

| Parameter | Type | Description |
|-----------|------|-------------|
| action | string | Operation to perform |
| target_ip | string | FortiGate management IP (for absorb) |
| device_key | string | Device key like "spoke_192_168_209_30" |
| license_type | string | **REQUIRED for update-license**: 'fortiflex' or 'standard' |

### FortiFlex License Parameters (for VM deployments)
| Parameter | Type | Description |
|-----------|------|-------------|
| fortiflex_serial | string | FortiFlex serial number (FGVMXXXXXX) |
| fortiflex_token | string | FortiFlex license token - **REQUIRED** |
| fortiflex_config_id | string | Config ID used to generate token |
| fortiflex_config_name | string | FortiFlex configuration name |
| fortiflex_status | string | License status (ACTIVE, PENDING, STOPPED) |
| fortiflex_end_date | string | License end date (YYYY-MM-DD) |

### Standard License Parameters (for hardware devices)
| Parameter | Type | Description |
|-----------|------|-------------|
| device_serial | string | Hardware device serial number - **REQUIRED** |
| device_model | string | Device model (e.g., FortiWiFi-50G-5G) |
| license_name | string | License/contract name |
| license_start_date | string | License start date (YYYY-MM-DD) |
| license_end_date | string | License end date (YYYY-MM-DD) |

## Usage Examples

### Absorb a New Spoke
```json
{
  "action": "absorb",
  "target_ip": "10.0.0.30"
}
```

### Absorb a Hub
```json
{
  "action": "absorb",
  "target_ip": "10.0.1.1"
}
```

### List All Tracked Devices
```json
{
  "action": "list"
}
```

### Get Full Device Config
```json
{
  "action": "get",
  "device_key": "spoke_192_168_209_30"
}
```

### Export Complete Manifest
```json
{
  "action": "export"
}
```

### Remove a Device
```json
{
  "action": "remove",
  "device_key": "spoke_192_168_209_30"
}
```

### Assign FortiFlex License (VM Deployment)
```json
{
  "action": "update-license",
  "device_key": "hub_192_168_215_15",
  "license_type": "fortiflex",
  "fortiflex_serial": "FGVMMLTMXXXXXXXXX",
  "fortiflex_token": "58A7B75F319C5518CD04",
  "fortiflex_config_name": "FGT_VM_Lab1",
  "fortiflex_status": "ACTIVE",
  "fortiflex_end_date": "2027-05-29",
  "device_model": "FortiGate-VM"
}
```

### Assign Standard License (Hardware Device)
```json
{
  "action": "update-license",
  "device_key": "spoke_192_168_209_30",
  "license_type": "standard",
  "device_serial": "FW50G5TKXXXXXXXXX",
  "device_model": "FortiWiFi-50G-5G",
  "license_name": "50G-Lab-FortiGate-SE",
  "license_start_date": "2025-10-21",
  "license_end_date": "2026-10-21"
}
```

## License Types - Critical Distinction

The manifest tracker supports **two different license types**:

### FortiFlex License (for VM deployments)
- **When to use**: FortiGate-VM in VMware, Hyper-V, AWS, Azure, etc.
- **Key characteristic**: Requires token application via CLI
- **Serial format**: FGVMXXXXXX (e.g., FGVMMLTMXXXXXXXXX)
- **Deployment step**: `execute vm-license install <token>`

### Standard License (for hardware devices)
- **When to use**: Physical FortiGate appliances, FortiWiFi devices
- **Key characteristic**: Pre-licensed, no token application needed
- **Serial format**: Various (e.g., FW50G5TKXXXXXXXXX, FGT100FT...)
- **Deployment step**: Apply config directly

## License Tracking in Manifest

### Device Entry with FortiFlex (VM)
```yaml
devices:
  hub_192_168_215_15:
    role: hub
    device_name: "SD-WAN-Hub"
    license_type: fortiflex
    device_model: "FortiGate-VM"
    license:
      type: fortiflex
      serial: "FGVMMLTMXXXXXXXXX"
      token: "58A7B75F319C5518CD04"
      config_id: "53713"
      config_name: "FGT_VM_Lab1"
      status: "ACTIVE"
      end_date: "2027-05-29"
      assigned_at: "2026-01-18T10:30:00"
```

### Device Entry with Standard License (Hardware)
```yaml
devices:
  spoke_192_168_209_30:
    role: spoke
    device_name: "Branch1"
    license_type: standard
    device_model: "FortiWiFi-50G-5G"
    license:
      type: standard
      device_serial: "FW50G5TKXXXXXXXXX"
      license_name: "50G-Lab-FortiGate-SE"
      start_date: "2025-10-21"
      end_date: "2026-10-21"
      assigned_at: "2026-01-18T10:30:00"
```

### update-license Response - FortiFlex
```json
{
  "success": true,
  "message": "FortiFlex license assigned to hub_192_168_215_15",
  "device_key": "hub_192_168_215_15",
  "device_name": "SD-WAN-Hub",
  "license_type": "fortiflex",
  "license": {
    "type": "fortiflex",
    "serial": "FGVMMLTMXXXXXXXXX",
    "token": "58A7B75F319C5518CD04",
    "status": "ACTIVE",
    "end_date": "2027-05-29"
  },
  "requires_token_application": true,
  "license_command": "execute vm-license install 58A7B75F319C5518CD04",
  "next_steps": [
    "1. Deploy FortiGate VM",
    "2. Run: execute vm-license install 58A7B75F319C5518CD04",
    "3. Wait for device reboot",
    "4. Apply SD-WAN configuration"
  ]
}
```

### update-license Response - Standard
```json
{
  "success": true,
  "message": "Standard hardware license assigned to spoke_192_168_209_30",
  "device_key": "spoke_192_168_209_30",
  "device_name": "Branch1",
  "license_type": "standard",
  "license": {
    "type": "standard",
    "device_serial": "FW50G5TKXXXXXXXXX",
    "license_name": "50G-Lab-FortiGate-SE",
    "end_date": "2026-10-21"
  },
  "requires_token_application": false,
  "next_steps": [
    "1. Hardware device FW50G5TKXXXXXXXXX is pre-licensed",
    "2. Apply SD-WAN configuration directly",
    "3. No license token application required"
  ]
}
```

### List Response with License Info
```json
{
  "success": true,
  "devices": [
    {
      "device_key": "spoke_192_168_209_30",
      "device_name": "Branch1",
      "license_type": "standard",
      "license": {
        "type": "standard",
        "device_serial": "FW50G5TKXXXXXXXXX",
        "end_date": "2026-10-21",
        "requires_token": false
      }
    },
    {
      "device_key": "hub_192_168_215_15",
      "device_name": "SD-WAN-Hub",
      "license_type": "fortiflex",
      "license": {
        "type": "fortiflex",
        "serial": "FGVMMLTMXXXXXXXXX",
        "status": "ACTIVE",
        "end_date": "2027-05-29",
        "requires_token": true
      }
    }
  ]
}
```

## Workflows by License Type

### FortiFlex (VM) Workflow
```
1. fortiflex-token-create         -> Get serial + token
2. sdwan-manifest-tracker absorb  -> Onboard device
3. sdwan-manifest-tracker update-license license_type=fortiflex -> Assign token
4. Deploy FortiGate VM
5. Apply license: execute vm-license install <token>
6. Wait for reboot
7. Apply SD-WAN configuration
```

### Standard (Hardware) Workflow
```
1. sdwan-manifest-tracker absorb  -> Onboard device
2. sdwan-manifest-tracker update-license license_type=standard -> Record license info
3. Power on hardware device (already licensed)
4. Apply SD-WAN configuration directly
```

## Output Examples

### Absorb Response
```json
{
  "success": true,
  "action": "create",
  "device_key": "spoke_192_168_209_30",
  "role": "spoke",
  "device_name": "howard-sdwan-spoke-1",
  "management_ip": "10.0.0.30",
  "serial_number": "FW50G5TKXXXXXXXXX",
  "firmware": "v7.6.5",
  "summary": {
    "interfaces": 8,
    "ipsec_tunnels": 2,
    "sdwan_members": 3,
    "sdwan_zones": 2,
    "sdwan_health_checks": 6,
    "sdwan_services": 0,
    "bgp_neighbors": 2,
    "policies": 2,
    "static_routes": 3
  },
  "manifest_path": "C:/ProgramData/Ulysses/config/sdwan-manifest.yaml"
}
```

### List Response
```json
{
  "success": true,
  "network_name": "SD-WAN Network",
  "as_number": 65000,
  "device_count": 2,
  "devices": [
    {
      "device_key": "spoke_192_168_209_30",
      "role": "spoke",
      "device_name": "howard-sdwan-spoke-1",
      "management_ip": "10.0.0.30",
      "serial_number": "FW50G5TKXXXXXXXXX",
      "firmware": "v7.6.5",
      "last_absorbed": "2025-01-17T14:30:00"
    },
    {
      "device_key": "hub_192_168_215_15",
      "role": "hub",
      "device_name": "howard-sdwan-hub-1",
      "management_ip": "10.0.1.1",
      "serial_number": "FGVMMLTMXXXXXXXXX",
      "firmware": "v7.6.5",
      "last_absorbed": "2025-01-17T14:31:00"
    }
  ]
}
```

## Manifest Structure

```yaml
manifest_version: "1.0.0"
created: "2025-01-17T14:30:00"
last_updated: "2025-01-17T14:35:00"
network:
  name: "SD-WAN Network"
  as_number: 65000
  loopback_range: "172.16.0.0/16"
devices:
  spoke_192_168_209_30:
    role: spoke
    management_ip: "10.0.0.30"
    device_name: "howard-sdwan-spoke-1"
    serial_number: "FW50G5TKXXXXXXXXX"
    firmware: "v7.6.5"
    vdom: "root"
    last_absorbed: "2025-01-17T14:30:00"
    interfaces:
      physical: [...]
      tunnel: [...]
      loopback: [...]
    ipsec:
      phase1: [...]
      phase2: [...]
    sdwan:
      status: enable
      zones: [...]
      members: [...]
      health_checks: [...]
      neighbors: [...]
      services: [...]
    bgp:
      enabled: true
      as_number: 65000
      router_id: "172.16.0.2"
      neighbors: [...]
      neighbor_groups: [...]
      neighbor_ranges: [...]
    policies: [...]
    static_routes: [...]
    addresses:
      addresses: [...]
      groups: [...]
  hub_192_168_215_15:
    role: hub
    # Similar structure...
```

## Role Detection

The tool automatically determines if a device is a **hub** or **spoke** based on:

1. **Dynamic IPsec tunnels** - Hub uses `type: dynamic` for Phase1
2. **Remote detect mode** - Hub health check uses `detect-mode: remote`
3. **Auto-discovery-sender** - Hub has sender enabled on dynamic tunnels

## Use Cases

### 1. Initial Onboarding
```
1. Deploy hub and spoke(s)
2. Absorb each device into manifest
3. Review manifest for completeness
4. Use manifest as input for blueprints
```

### 2. Configuration Drift Detection
```
1. Absorb device (updates existing entry)
2. Compare last_absorbed timestamps
3. Diff against previous export
```

### 3. Blueprint Planning
```
1. Export manifest
2. Extract unique variables per site
3. Generate Jinja2 templates
4. Use manifest values for new deployments
```

### 4. Multi-Site Rollout
```
1. Deploy new FortiGate at site
2. Absorb into manifest (auto-assigns device_key)
3. Update manifest with site-specific values
4. Generate config from blueprint
```

## Unique Variables for Templates

After absorbing devices, use the manifest to identify unique per-site variables:

| Category | Variable | Example |
|----------|----------|---------|
| Identity | device_name | Branch1, Branch2 |
| Identity | loopback_ip | 172.16.0.1, 172.16.0.2 |
| WAN | wan_ip | 10.198.1.2, 10.198.3.2 |
| WAN | wan_gateway | 10.198.1.1, 10.198.3.1 |
| LAN | lan_subnet | 10.1.1.0/24, 10.2.1.0/24 |
| VPN | localid | Br1-HUB1-VPN1, Br2-HUB1-VPN1 |
| VPN | exchange_ip | 172.16.0.1, 172.16.0.2 |
| SD-WAN | member_seq | 3, 4 (unique per tunnel) |
| BGP | router_id | 172.16.0.1, 172.16.0.2 |

## Related Tools

### SD-WAN Tools
- `fortigate-sdwan-health-check` - Configure health checks
- `fortigate-sdwan-zone` - Configure SD-WAN zones
- `fortigate-sdwan-neighbor` - Configure BGP neighbor bindings
- `fortigate-sdwan-status` - Real-time SD-WAN status
- `fortigate-sdwan-blueprint-planner` - Generate site deployment configs
- `fortigate-credential-manager` - Manage device credentials

### FortiFlex Tools
- `fortiflex-programs-list` - List FortiFlex programs and point balance
- `fortiflex-config-list` - List available configurations
- `fortiflex-config-create` - Create new configurations
- `fortiflex-token-create` - Generate license tokens for VMs
- `fortiflex-entitlements-list` - List all entitlements/licenses

## Prerequisites
1. FortiGate device accessible via HTTPS
2. API credentials configured in fortigate_credentials.yaml
3. Write access to C:/ProgramData/Ulysses/config/

## Troubleshooting

### Device Not Found in Credentials
```json
{
  "success": false,
  "error": "No credentials found for 192.168.x.x",
  "hint": "Use fortigate-credential-manager to register device first"
}
```

### Manifest File Location
If manifest doesn't exist, it will be created automatically at:
```
C:/ProgramData/Ulysses/config/sdwan-manifest.yaml
```
