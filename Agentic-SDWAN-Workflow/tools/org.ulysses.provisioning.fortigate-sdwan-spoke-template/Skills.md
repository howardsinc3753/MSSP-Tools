# FortiGate SD-WAN Spoke Template - Skills Guide

## Tool Identity
- **Canonical ID:** `org.ulysses.provisioning.fortigate-sdwan-spoke-template/1.1.1`
- **Domain:** provisioning
- **Intent:** configure
- **Vendor:** fortinet

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.1.1 | 2026-01-22 | BUGFIX: set_system_global now ALWAYS called (was conditional on hostname/management_ip) |
| 1.1.0 | 2026-01-22 | Added system global/settings, dual VPN tunnels, ike-tcp-port |
| 1.0.0 | 2026-01-20 | Initial release with single VPN |

## When to Use This Tool

### Primary Use Case
Provision a branch/spoke FortiGate for SD-WAN overlay connectivity to a hub.

### What It Creates (v1.1.0)
1. **System Global Settings** - hostname, management-ip, timezone, admintimeout
2. **System Settings** - location-id, ike-tcp-port (11443)
3. **Loopback Interface** - For BGP peering and health checks
4. **IPsec Phase1 (VPN1)** - Primary tunnel (network-id: 1)
5. **IPsec Phase1 (VPN2)** - Secondary tunnel (network-id: 2) for redundancy
6. **IPsec Phase2** - Quick mode config for both tunnels
7. **BGP Bootstrap Routes** - Static routes to hub loopbacks via tunnel
8. **SD-WAN Zone** - Overlay zone for steering
9. **SD-WAN Members** - Both tunnels assigned to zone
10. **SD-WAN Health Check** - Monitors both VPN1 and VPN2
11. **Firewall Address** - Loopback subnet object
12. **Firewall Policy** - Loopback ↔ SDWAN zone

## Required Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| target_ip | Spoke FortiGate IP | 10.0.0.30 |
| hub_wan_ip | Hub's public IP | 66.110.253.68 |
| loopback_ip | Spoke loopback with mask | "172.16.0.2 255.255.255.255" |
| psk | Pre-shared key | "secretkey123" |

## Optional Parameters

### System Global Settings (NEW v1.1.0)

| Parameter | Default | Description |
|-----------|---------|-------------|
| site_id | - | Site ID for hostname derivation (e.g., 4 → "sdwan-spoke-04") |
| hostname | - | Device hostname (or derived from site_id) |
| management_ip | target_ip | Management IP for SD-WAN fabric |
| timezone | US/Pacific | Device timezone |
| admintimeout | 480 | Admin session timeout (minutes) |

### System Settings (NEW v1.1.0)

| Parameter | Default | Description |
|-----------|---------|-------------|
| ike_tcp_port | 11443 | IKE TCP port (CRITICAL: avoids conflict with HTTPS 443) |

### Tunnel Settings

| Parameter | Default | Description |
|-----------|---------|-------------|
| loopback_name | Spoke_Lo | Loopback interface name |
| tunnel_name | HUB1_VPN1 | Primary IPsec tunnel name (network-id: 1) |
| create_second_vpn | true | Create secondary VPN tunnel for redundancy |
| tunnel_name_2 | HUB1_VPN2 | Secondary IPsec tunnel name (network-id: 2) |
| wan_interface | auto-detect | WAN port for tunnel (auto-detects wan1/wan/wan2/port1) |

### SD-WAN Settings

| Parameter | Default | Description |
|-----------|---------|-------------|
| sdwan_zone | SDWAN_OVERLAY | Zone name |
| hub_loopback_ip | 172.16.255.253 | Hub loopback for health check |
| hub_bgp_loopbacks | ["172.16.255.252", "172.16.255.253"] | Hub BGP loopbacks for bootstrap routes (CRITICAL) |
| network_id | 1 | Overlay network ID for VPN1 (VPN2 uses 2) |

**Note:** FortiOS does not allow hyphens in some object names. Use underscores instead.

### BGP Bootstrap Routes (CRITICAL)

The `hub_bgp_loopbacks` parameter solves a critical chicken-and-egg problem:

**Problem:** Spoke cannot establish BGP to hub because it has no route to hub's loopback IPs.
BGP learns routes from hub, but BGP can't start until it can reach hub's BGP loopback.

**Solution:** This tool creates static /32 routes to hub loopbacks via the IPsec tunnel:
```
172.16.255.252/32 -> HUB1_VPN1 (static route seq 900)
172.16.255.253/32 -> HUB1_VPN1 (static route seq 901)
```

Once BGP establishes, it learns all prefixes dynamically. The static routes provide the
initial bootstrap path. Without these routes, BGP will be stuck in "Connect" state.

## Auto-Configured Settings (from Fortinet 4D-Demo)

This tool automatically configures the following settings based on best practices:

| Setting | Value | Purpose |
|---------|-------|---------|
| `location-id` | Loopback IP | SD-WAN device identification |
| `exchange-ip-addr4` | Loopback IP | SD-WAN overlay routing |
| `auto-discovery-sender` | enable | Spoke sends ADVPN shortcuts |
| `auto-discovery-receiver` | enable | Spoke receives shortcuts from hub |
| `dhgrp` | 20 21 | Modern DH groups for security |
| `transport` | udp | Consistent transport for spoke |
| `net-device` | enable | Standard for static/spoke tunnels |
| `localid` | spoke-{tunnel_name} | Helps hub identify this spoke |
| `priority` | 10 | SD-WAN member base priority |
| `priority-in-sla` | 10 | Priority when SLA met |
| `priority-out-sla` | 20 | Priority when SLA not met |

## Example Usage

```json
{
  "target_ip": "10.0.0.30",
  "hub_wan_ip": "66.110.253.68",
  "loopback_ip": "172.16.0.2 255.255.255.255",
  "psk": "fortinet123",
  "tunnel_name": "HUB1_VPN1",
  "sdwan_zone": "SDWAN_HUB",
  "hub_loopback_ip": "172.16.255.253"
}
```

## Output

```json
{
  "success": true,
  "components_created": [
    "loopback:Spoke_Lo",
    "phase1:HUB1_VPN1",
    "phase2:HUB1_VPN1",
    "static-route:172.16.255.252/32->HUB1_VPN1",
    "static-route:172.16.255.253/32->HUB1_VPN1",
    "sdwan:enabled",
    "zone:SDWAN_HUB",
    "member:HUB1_VPN1->SDWAN_HUB",
    "health_check:HUB_Health",
    "address:SDWAN_Loopbacks",
    "policy:SDWAN_Overlay_Traffic"
  ],
  "config_summary": {
    "loopback": "Spoke_Lo (172.16.0.2 255.255.255.255)",
    "tunnel": "HUB1_VPN1 -> 66.110.253.68",
    "wan_interface": "wan",
    "sdwan_zone": "SDWAN_HUB",
    "health_check_target": "172.16.255.253",
    "bgp_bootstrap_routes": [
      "172.16.255.252/32 via HUB1_VPN1",
      "172.16.255.253/32 via HUB1_VPN1"
    ]
  }
}
```

## Topology

```
[Spoke: 10.0.0.30]
    └── wan1 ─────IPsec────► [Hub: 66.110.253.68]
    └── Spoke-Lo (172.16.0.2)
              │
              ▼
        SD-WAN Zone: SDWAN-HUB
              │
        Health Check → 172.16.255.253 (Hub-Lo)
```

## Prerequisites

### Credential Check (CRITICAL)
Before using this tool, verify credentials are configured:

1. **Check for existing credentials:**
   - Primary path: `~/.config/mcp/fortigate_credentials.yaml`
   - Windows secondary: `~/AppData/Local/mcp/fortigate_credentials.yaml`
   - System-wide: `C:/ProgramData/mcp/fortigate_credentials.yaml`

2. **If no credentials exist:**
   Use `fortigate-credential-manager` to register the device first:
   ```
   fortigate-credential-manager action=register target_ip=10.0.0.30
   ```

3. **Verify credential access:**
   Use `fortigate-health-check` to confirm connectivity before provisioning.

## PSK Configuration (CRITICAL)

### PSK Best Practices
| Guideline | Reason |
|-----------|--------|
| Use identical PSK on Hub and Spoke | Mismatched PSK = tunnel won't establish |
| Keep PSK simple during initial setup | Complex PSKs can have encoding issues |
| Test with simple PSK first (e.g., "password") | Eliminates PSK as variable during troubleshooting |
| Change to strong PSK after tunnel verified | Production security |

### PSK Troubleshooting
If tunnel won't establish and config looks correct:
1. Simplify PSK to something basic (e.g., "password")
2. Apply identical PSK on both hub AND spoke
3. Bring tunnel up - if it works, original PSK had issues
4. Then change to production-strength PSK

## Critical Technical Details

### net-device Setting
This tool correctly sets `net-device: enable` for spoke (static) tunnels.

| Tunnel Type | net-device | Why |
|-------------|------------|-----|
| Static (Spoke) | `enable` | Standard for initiating tunnels |
| Dynamic (Hub) | `disable` | Required for SD-WAN member addition |

**Note:** Spoke tunnels use static mode and can safely have `net-device enable`.

### Firewall Policy Requirement
Tunnels will NOT negotiate until they are referenced in a firewall policy.
This tool creates the required policy automatically.

### Network ID Matching
The `network_id` parameter **must match** the hub's tunnel:
- Hub: `network_id: 1` on SPOKE_VPN1 → Spoke: `network_id: 1` on HUB1_VPN1
- For VPN2: Hub `network_id: 2` → Spoke `network_id: 2`

## Troubleshooting

### Tunnel Won't Come Up
1. **Check PSK** - Must be identical on hub and spoke
2. **Check Firewall Policy** - Tunnel must be in a policy or SD-WAN zone that's in a policy
3. **Check Hub Reachability** - Spoke must reach hub's WAN IP (try ping)
4. **Check Phase1 Settings** - IKE version, proposals must match hub
5. **Check Hub Dynamic Tunnel** - Hub must have matching dynamic tunnel accepting connections

### Can't Ping Hub Loopback After Tunnel Up
1. **Check Phase2** - Both ends must have matching selectors
2. **Check Routing** - May need static route or BGP for loopback subnet
3. **Check Firewall Policy** - Policy must allow traffic on overlay

### BGP Stuck in "Connect" State
1. **Check Bootstrap Routes** - Run `get router info routing-table static`
2. **Verify Routes to Hub Loopback** - Must see `172.16.255.252/32 via HUB1_VPN1`
3. **If Missing** - Re-run template or manually add:
   ```
   config router static
   edit 900
   set dst 172.16.255.252 255.255.255.255
   set device HUB1_VPN1
   set comment "BGP bootstrap to hub loopback"
   next
   end
   ```
4. **Check Tunnel Status** - IPsec must be UP before BGP can work

### SD-WAN Health Check Failing
1. **Check Hub Loopback IP** - Must match `hub_loopback_ip` parameter
2. **Check Tunnel Status** - Tunnel must be UP first
3. **Check Policy** - Health check traffic must be allowed

## Adding Additional Tunnels

To add a second VPN tunnel to an existing spoke (e.g., VPN2 for redundancy):

**Use `fortigate-ipsec-tunnel-create` instead of this template:**
```json
{
  "target_ip": "10.0.0.30",
  "tunnel_name": "HUB2_VPN2",
  "tunnel_type": "static",
  "interface": "wan",
  "remote_gw": "66.110.253.68",
  "psk": "password",
  "network_id": 2
}
```

The separate tool is preferred because:
- This template creates full SD-WAN infrastructure (loopback, zone, health-check, policy)
- For additional tunnels, you only need Phase1 + Phase2
- Then add the new tunnel to the existing SD-WAN zone

### After Creating Additional Tunnel
1. Add tunnel to existing SD-WAN zone as member
2. Tunnel will auto-negotiate once in zone (policy already exists)
3. Verify with `fortigate-ipsec-tunnel action=status`

## Related Tools
- `fortigate-sdwan-hub-template` - Configure hub side
- `fortigate-ipsec-tunnel-create` - Add individual tunnels to existing setup
- `fortigate-credential-manager` - Register device credentials
- `fortigate-set-hostname` - Set device name first
- `fortigate-health-check` - Verify device status
