# FortiGate SD-WAN Blueprint Planner

## Purpose
Generate CSV templates for new SD-WAN site deployments with auto-calculated recommended values, then read completed templates to generate full FortiOS CLI configurations.

## When to Use
- Planning a new SD-WAN spoke site deployment
- Planning a new SD-WAN hub site deployment
- Need unique per-site values (loopback IPs, site IDs, BGP ASN)
- Want FortiOS CLI config generated automatically from a simple spreadsheet

## Workflow

### Step 1: Generate Template
```json
{
  "action": "generate-template",
  "role": "spoke",
  "site_name": "Branch3"
}
```

This creates a CSV at `C:\ProgramData\Ulysses\config\blueprints\Branch3_spoke_template.csv` with:
- All required variables
- Recommended next values based on existing manifest
- Descriptions for each field

### Step 2: User Fills CSV
Open the CSV in Excel/Notepad and fill in site-specific values:
- `site_hostname` - Device hostname
- `wan1_ip`, `wan1_gateway` - Primary WAN settings
- `wan2_ip`, `wan2_gateway` - Secondary WAN settings
- `lan_subnet` - LAN network

Most values have recommended defaults calculated automatically!

### Step 3: Generate Config
```json
{
  "action": "plan-site",
  "csv_path": "C:\\ProgramData\\Ulysses\\config\\blueprints\\Branch3_spoke_template.csv",
  "add_to_manifest": true
}
```

Returns complete FortiOS CLI configuration ready to paste into the device.

## Template Variables

### Identity Variables
| Variable | Description | Example |
|----------|-------------|---------|
| site_hostname | Device hostname | Branch3-FGT |
| site_id | Unique site identifier (1-255) | 3 |
| loopback_ip | Site loopback for health checks | 172.16.255.3 |

### WAN Interface Variables
| Variable | Description | Example |
|----------|-------------|---------|
| wan1_interface | Primary WAN port | wan1 |
| wan1_ip | Primary WAN IP/mask | 203.0.113.10/24 |
| wan1_gateway | Primary WAN gateway | 203.0.113.1 |
| wan2_interface | Secondary WAN port | wan2 |
| wan2_ip | Secondary WAN IP/mask | 198.51.100.10/24 |
| wan2_gateway | Secondary WAN gateway | 198.51.100.1 |

### LAN Variables
| Variable | Description | Example |
|----------|-------------|---------|
| lan_interface | LAN port | port5 |
| lan_subnet | LAN network | 10.0.3.0/24 |
| lan_gateway_ip | LAN gateway (this device) | 10.0.3.1 |

### Hub Connection Variables
| Variable | Description | Example |
|----------|-------------|---------|
| hub1_public_ip | Hub1 public IP | 10.0.1.1 |
| hub2_public_ip | Hub2 public IP | 192.168.216.15 |
| hub_loopback | Hub loopback for health check | 172.16.255.253 |

### VPN Variables
| Variable | Description | Example |
|----------|-------------|---------|
| psk | IPsec pre-shared key | Fortinet123! |
| network_id | ADVPN network ID | 1 |
| ike_version | IKE version | 2 |

### SD-WAN Variables
| Variable | Description | Example |
|----------|-------------|---------|
| sdwan_zone | SD-WAN zone name | SDWAN |
| member1_seq | Member 1 sequence number | 100 |
| member2_seq | Member 2 sequence number | 200 |
| member3_seq | Member 3 sequence number | 300 |
| member4_seq | Member 4 sequence number | 400 |

### BGP Variables
| Variable | Description | Example |
|----------|-------------|---------|
| bgp_as | Local BGP AS number | 65003 |
| bgp_router_id | BGP router ID | 172.16.255.3 |
| hub_bgp_as | Hub BGP AS number | 65000 |

### License Type (REQUIRED)
| Variable | Description | Example |
|----------|-------------|---------|
| license_type | **REQUIRED** - 'fortiflex' (VM) or 'standard' (hardware) | fortiflex |
| device_model | Device model name | FortiGate-VM or FortiWiFi-50G-5G |

### Standard License Variables (Hardware Devices)
For pre-licensed hardware appliances (FortiGate, FortiWiFi, etc.):

| Variable | Description | Example |
|----------|-------------|---------|
| device_serial | Hardware device serial number | FW50G5TKXXXXXXXXX |
| license_name | License/contract name | 50G-Lab-FortiGate-SE |
| license_start_date | License start date (YYYY-MM-DD) | 2025-10-21 |
| license_end_date | License end date (YYYY-MM-DD) | 2026-10-21 |

### FortiFlex License Variables (VM Deployments)
For FortiGate-VM deployments that require license token application:

| Variable | Description | Example |
|----------|-------------|---------|
| fortiflex_token | FortiFlex license token | 58A7B75F319C5518CD04 |
| fortiflex_serial | FortiFlex serial number (FGVMXXXXXX) | FGVMMLTMXXXXXXXXX |
| fortiflex_config_id | FortiFlex config ID | 53713 |
| fortiflex_config_name | FortiFlex configuration name | FGT_VM_Lab1 |
| fortiflex_status | License status | ACTIVE |
| fortiflex_end_date | License end date (YYYY-MM-DD) | 2027-05-29 |

## License Type - Critical Decision Point

**IMPORTANT**: The `license_type` field determines the deployment workflow:

### Standard License (Hardware Devices)
- **When to use**: FortiGate appliances, FortiWiFi, physical hardware
- **Examples**: FortiWiFi-50G-5G, FortiGate-100F, FortiGate-60E
- **Workflow**: Device is pre-licensed → Apply config directly
- **No token application needed**

### FortiFlex License (VM Deployments)
- **When to use**: FortiGate-VM deployments in VMware, Hyper-V, AWS, Azure, etc.
- **Examples**: FortiGate-VM with FGVMXXXXXX serial
- **Workflow**: Deploy VM → Apply license token → Wait for reboot → Apply config
- **Token application required**: `execute vm-license <token>`

## Workflow Examples

### Workflow 1: Hardware Device (Standard License)

```
1. sdwan-blueprint generate-template -> Create CSV template
2. Fill CSV with:
   - license_type: standard
   - device_serial: FW50G5TKXXXXXXXXX
   - device_model: FortiWiFi-50G-5G
   - license_name: 50G-Lab-FortiGate-SE
   - Site-specific values (WAN IP, LAN, etc.)
3. sdwan-blueprint plan-site      -> Generate config
4. Power on hardware device
5. Apply configuration directly (device is pre-licensed)
```

### Workflow 2: VM Deployment (FortiFlex License)

```
1. fortiflex-programs-list        -> Get program SN, check points
2. fortiflex-config-create        -> Create "sdwan-spoke-2cpu-ent"
3. fortiflex-token-create         -> Generate token from config
4. sdwan-blueprint generate-template -> Create CSV template
5. Fill CSV with:
   - license_type: fortiflex
   - fortiflex_token: 58A7B75F319C5518CD04
   - fortiflex_serial: FGVMMLTMXXXXXXXXX
   - Site-specific values
6. sdwan-blueprint plan-site      -> Generate config with license command
7. Deploy FortiGate VM
8. Apply license: execute vm-license <token>
9. Wait for reboot
10. Apply remaining config
```

### Generated Config - Standard License

When `license_type=standard`:

```
# ============================================
# LICENSE TYPE: Standard (Hardware-Based)
# ============================================
# Model: FortiWiFi-50G-5G
# Device Serial: FW50G5TKXXXXXXXXX
# License Name: 50G-Lab-FortiGate-SE
# Start Date: 2025-10-21
# End Date: 2026-10-21
#
# Hardware devices are pre-licensed. No token application required.
# Apply configuration directly to the device.
```

### Generated Config - FortiFlex License

When `license_type=fortiflex`:

```
# ============================================
# LICENSE TYPE: FortiFlex (VM Token-Based)
# ============================================
# Model: FortiGate-VM
# FortiFlex Serial: FGVMMLTMXXXXXXXXX
# Config ID: 53713
# Config Name: FGT_VM_Lab1
# Status: ACTIVE
# End Date: 2027-05-29
#
# IMPORTANT: Run this command FIRST after initial VM boot:
#   execute vm-license 58A7B75F319C5518CD04
#
# After license installation, the device will reboot.
# Then apply the remaining configuration below.
```

### plan-site Response with License Info

```json
{
  "success": true,
  "action": "plan-site",
  "site_name": "Branch3",
  "license_type": "fortiflex",
  "license": {
    "type": "fortiflex",
    "serial": "FGVMMLTMXXXXXXXXX",
    "token": "58A7B75F319C5518CD04",
    "requires_token_application": true,
    "license_command": "execute vm-license 58A7B75F319C5518CD04"
  }
}
```

## Usage Examples

### Generate Spoke Template
```json
{
  "action": "generate-template",
  "role": "spoke",
  "site_name": "RemoteSite1"
}
```

### Generate Hub Template
```json
{
  "action": "generate-template",
  "role": "hub",
  "site_name": "DC-Hub2"
}
```

### Plan Site from CSV
```json
{
  "action": "plan-site",
  "csv_path": "C:\\ProgramData\\Ulysses\\config\\blueprints\\RemoteSite1_spoke_template.csv"
}
```

### Plan and Add to Manifest
```json
{
  "action": "plan-site",
  "csv_path": "C:\\ProgramData\\Ulysses\\config\\blueprints\\RemoteSite1_spoke_template.csv",
  "add_to_manifest": true
}
```

## Generated Config Sections

The `plan-site` action generates complete FortiOS CLI including:

1. **System Settings**
   - Hostname configuration
   - Loopback interface

2. **Physical Interfaces**
   - WAN1, WAN2 configuration
   - LAN interface

3. **IPsec VPN**
   - Phase1 interfaces (to Hub1 via WAN1/WAN2, to Hub2 via WAN1/WAN2)
   - Phase2 selectors
   - ADVPN settings (add-route, auto-discovery-sender)

4. **SD-WAN Configuration**
   - Zone creation
   - Member configuration with costs
   - Health check (HUB) with embed-measured-health
   - BGP neighbor configuration

5. **BGP Configuration**
   - Router ID and AS number
   - Neighbor group for hub connections
   - Network advertisements

6. **Firewall Policies**
   - LAN to SD-WAN (outbound)
   - SD-WAN to LAN (inbound from hub/spokes)
   - Health check allow policy

## Auto-Calculated Values

The `generate-template` action reads the existing manifest and calculates:

| Value | Logic |
|-------|-------|
| site_id | Max existing + 1 |
| loopback_ip | 172.16.255.{site_id} |
| bgp_as | 65000 + site_id |
| bgp_router_id | Same as loopback_ip |
| member1_seq | (site_id * 100) |
| member2_seq | (site_id * 100) + 100 |
| member3_seq | (site_id * 100) + 200 |
| member4_seq | (site_id * 100) + 300 |

## Output Example

### generate-template Response
```json
{
  "success": true,
  "action": "generate-template",
  "role": "spoke",
  "template_path": "C:/ProgramData/Ulysses/config/blueprints/Branch3_spoke_template.csv",
  "variables": {
    "site_id": {"value": 3, "description": "Unique site identifier"},
    "loopback_ip": {"value": "172.16.255.3", "description": "Site loopback IP"}
  }
}
```

### plan-site Response
```json
{
  "success": true,
  "action": "plan-site",
  "site_name": "Branch3-FGT",
  "role": "spoke",
  "config": "# FortiOS Configuration for Branch3-FGT\n...",
  "config_sections": ["system", "interfaces", "ipsec", "sdwan", "bgp", "firewall"]
}
```

## Error Handling

### Missing Required Fields
```json
{
  "success": false,
  "error": "Missing required fields",
  "validation_errors": [
    "site_hostname is required",
    "wan1_ip is required"
  ]
}
```

### Invalid CSV Format
```json
{
  "success": false,
  "error": "CSV parsing failed",
  "details": "Could not parse line 5"
}
```

## Related Tools

### SD-WAN Tools
- `fortigate-sdwan-manifest-tracker` - Track deployed devices and licenses
- `fortigate-sdwan-spoke-template` - Apply spoke config to device
- `fortigate-sdwan-hub-template` - Apply hub config to device

### FortiFlex Tools (for VM licensing)
- `fortiflex-programs-list` - List FortiFlex programs and point balance
- `fortiflex-config-list` - List available configurations
- `fortiflex-config-create` - Create new configurations
- `fortiflex-token-create` - Generate license tokens for VMs
- `fortiflex-entitlements-list` - List all entitlements/licenses

## Best Practices

1. **Always generate fresh template** - Values are calculated from current manifest
2. **Review recommended values** - Auto-calculated values may need adjustment
3. **Use add_to_manifest** - Keep manifest updated with planned sites
4. **Backup before applying** - Generated configs are complete replacements

## CSV Format

The CSV uses a simple 3-column format:
```
variable,value,description
site_hostname,Branch3-FGT,Device hostname
site_id,3,Unique site identifier (1-255)
loopback_ip,172.16.255.3,Site loopback for health checks
...
```

Open in Excel for easy editing, or use any text editor.
