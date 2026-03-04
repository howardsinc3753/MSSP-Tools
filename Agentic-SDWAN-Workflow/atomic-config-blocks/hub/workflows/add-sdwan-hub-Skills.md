# Add SD-WAN Hub Skills

**SecBot Persona Active** 🛡️
- **Voice**: Confident, upbeat, direct
- **Verification-Obsessed**: Every block gets verified before proceeding to the next
- **Escalates Early**: Problems get surfaced immediately with clear paths forward
- **Celebrates Wins**: Hub deployment success gets acknowledged
- **Happy-Go-Lucky**: "Let's build this hub!" energy throughout

---

## Overview

The `/add-sdwan-hub` workflow deploys a complete FortiGate SD-WAN hub using 10 composable blocks (020-029) based on NFR-025 framework. The hub accepts dynamic spoke connections via ADVPN (Auto Discovery VPN), provides BGP route reflection, and enables spoke-to-spoke shortcuts.

**Key Architectural Pattern**: Dual Loopback Design
- **Hub_Lo** (172.16.255.253): Hub system services, ADVPN hub identifier
- **BGP_Lo** (172.16.255.252): BGP router-ID, BGP update-source, IPsec exchange-ip-addr4

**Deployment Strategy**: Atomic template (ATOMIC_HUB_TEMPLATE.conf) contains all 10 blocks in dependency order for single-push deployment.

---

## How to Call

### Option 1: Single Atomic Push (Recommended)

```
Use fortigate-config-push/2.0.0 with ATOMIC_HUB_TEMPLATE.conf after parameter substitution
```

**Steps**:
1. Copy ATOMIC_HUB_TEMPLATE.conf to deployment directory
2. Substitute all {{PARAMETERS}} with actual values
3. Push via fortigate-config-push/2.0.0
4. Verify each section using verification commands

### Option 2: Incremental Block Push (Testing/Troubleshooting)

```
Push blocks 020-029 individually in dependency order
```

**Dependency Order**:
```
020 (system-global)
 ↓
021 (system-settings)
 ↓
022 (interfaces: WAN, LAN, Hub_Lo, BGP_Lo)
 ↓
023 (ipsec-phase1-template)
 ↓
024 (ipsec-phase2-template)
 ↓
025 (bgp-base)
 ↓
026 (bgp-neighbor-range)
 ↓
027 (sdwan-zone)
 ↓
028 (sdwan-healthcheck)
 ↓
029 (firewall-policies)
```

---

## Parameters

### Required Parameters

| Parameter | Type | Example | Description |
|-----------|------|---------|-------------|
| `HUB_HOSTNAME` | string | `howard-sdwan-hub-2` | Hub device hostname |
| `WAN_IP_CIDR` | cidr | `10.0.1.20/24` | Hub WAN IP with subnet |
| `LAN_IP_CIDR` | cidr | `10.250.250.1/24` | Hub LAN IP with subnet |
| `HUB_LOOPBACK_IP` | ip_address | `172.16.255.253` | Hub services loopback |
| `BGP_LOOPBACK_IP` | ip_address | `172.16.255.252` | BGP operations loopback |
| `HUB_WAN_IP` | ip_address | `10.0.1.20` | Hub WAN IP (no CIDR, for IPsec local-gw) |
| `PSK` | string (sensitive) | `YourSecurePassword123` | IPsec pre-shared key |
| `BGP_AS` | integer | `65000` | Hub BGP AS (iBGP with spokes) |
| `ROUTER_ID` | ip_address | `172.16.255.252` | BGP router-ID (same as BGP_LOOPBACK_IP) |
| `ADVERTISED_NETWORKS` | string | `10.250.250.0` | Hub LAN network to advertise |
| `ADVERTISED_NETMASK` | string | `255.255.255.0` | Netmask for advertised network |

### Optional Parameters with Defaults

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `TIMEZONE` | string | `US/Pacific` | System timezone |
| `ADMINTIMEOUT` | integer | `480` | Admin session timeout (minutes) |
| `WAN_INTERFACE` | string | `port1` | WAN interface name |
| `LAN_INTERFACE` | string | `port2` | LAN interface name |
| `HUB_LOOPBACK` | string | `Hub_Lo` | Hub loopback interface name |
| `BGP_LOOPBACK` | string | `BGP_Lo` | BGP loopback interface name |
| `LOCATION_ID` | ip_address | `0.0.0.0` | ADVPN location ID (0.0.0.0 = use WAN IP). Verified: FortiOS 7.4+ accepts IP format |
| `IKE_TCP_PORT` | integer | `11443` | IKE over TCP port (must match spokes) |
| `IKE_VERSION` | integer | `2` | IKE version |
| `NETWORK_ID_VPN1` | integer | `1` | IPsec network-id for VPN1 |
| `NETWORK_ID_VPN2` | integer | `2` | IPsec network-id for VPN2 |
| `PROPOSAL` | string | `aes256-sha256` | IPsec phase2 proposal |
| `DHGRP` | string | `20 21` | Diffie-Hellman groups |
| `IBGP_MULTIPATH` | string | `enable` | iBGP multipath |
| `GRACEFUL_RESTART` | string | `enable` | BGP graceful restart |
| `HOLDTIME_TIMER` | integer | `180` | BGP holdtime timer |
| `KEEPALIVE_TIMER` | integer | `60` | BGP keepalive timer |
| `NEIGHBOR_GROUP_NAME` | string | `EDGE` | BGP neighbor group for spokes |
| `NEIGHBOR_RANGE_PREFIX` | string | `172.16.0.0` | Spoke loopback range |
| `NEIGHBOR_RANGE_NETMASK` | string | `255.255.0.0` | Spoke loopback netmask |
| `REMOTE_AS` | integer | `65000` | Spoke AS (same as hub for iBGP) |
| `ZONE_NAME` | string | `SDWAN_OVERLAY` | SD-WAN zone name |
| `MEMBER_SEQ_VPN1` | integer | `100` | SD-WAN member seq for VPN1 (hub uses 100) |
| `MEMBER_SEQ_VPN2` | integer | `2` | SD-WAN member seq for VPN2 (hub uses 2) |
| `HEALTH_CHECK_NAME` | string | `From_Edge` | Health-check name |
| `HEALTH_CHECK_TARGET` | ip_address | Same as BGP_LOOPBACK_IP | Health-check target IP |
| `INTERVAL_MS` | integer | `1000` | Health-check interval (ms) |
| `FAILTIME_SECONDS` | integer | `5` | Link failtime (seconds) |
| `RECOVERYTIME_SECONDS` | integer | `5` | Link recoverytime (seconds) |

### Critical Parameter Notes

1. **HUB_WAN_IP vs WAN_IP_CIDR**:
   - `WAN_IP_CIDR` = `10.0.1.20/24` (for interface config)
   - `HUB_WAN_IP` = `10.0.1.20` (for IPsec local-gw, no CIDR)

2. **BGP_LOOPBACK_IP = ROUTER_ID = HEALTH_CHECK_TARGET**:
   - All three should be the same IP (e.g., 172.16.255.252)

3. **Hub Seq Numbers (GAP-51)**:
   - Hub uses `MEMBER_SEQ_VPN1=100`, `MEMBER_SEQ_VPN2=2`
   - Spokes use seq 3/4 (per GAP-51)
   - These are INDEPENDENT - no conflict

4. **PSK Security**:
   - Must match between hub and all spokes
   - Store securely, never commit to git

---

## Interpreting Results

### Success Indicators

After pushing ATOMIC_HUB_TEMPLATE.conf, verify each section:

#### 1. System Global (Block 020)
```bash
get system global | grep hostname
```
**Expected**: `hostname: howard-sdwan-hub-2`

#### 2. System Settings (Block 021)
```bash
get system settings | grep -E 'location-id|ike-tcp-port'
```
**Expected**:
```
location-id: 0.0.0.0
ike-tcp-port: 11443
```

#### 3. Interfaces (Block 022)
```bash
get system interface Hub_Lo
get system interface BGP_Lo
```
**Expected**:
```
name: Hub_Lo
ip: 172.16.255.253 255.255.255.255
type: loopback

name: BGP_Lo
ip: 172.16.255.252 255.255.255.255
type: loopback
```

#### 4. IPsec Phase1 Templates (Block 023)
```bash
get vpn ipsec phase1-interface SPOKE_VPN1
get vpn ipsec phase1-interface SPOKE_VPN2
```
**Expected**:
```
type: dynamic
peertype: any
local-gw: 10.0.1.20
mode-cfg: disable
exchange-ip-addr4: 172.16.255.252
auto-discovery-sender: enable
network-overlay: enable
network-id: 1 (VPN1) or 2 (VPN2)
dpd-retrycount: 3 (VPN1), 2 (VPN2)
dpd-retryinterval: 5 (VPN1), 3 (VPN2)
```

**CRITICAL**: Verify `peertype: any` is present (GAP-52 fix)

#### 5. IPsec Phase2 Selectors (Block 024)
```bash
get vpn ipsec phase2-interface SPOKE_VPN1
```
**Expected**:
```
phase1name: SPOKE_VPN1
src-subnet: 0.0.0.0 0.0.0.0
dst-subnet: 0.0.0.0 0.0.0.0
```

#### 6. BGP Base (Block 025)
```bash
get router info bgp summary
```
**Expected**:
```
Router ID: 172.16.255.252
AS: 65000
```

**Verify additional-path**:
```bash
get router bgp | grep -E 'additional-path|ebgp-multipath|recursive-inherit'
```
**Expected**:
```
ebgp-multipath: enable
additional-path: enable
additional-path-select: 4
recursive-inherit-priority: enable
```

#### 7. BGP Neighbor Range (Block 026)
```bash
get router bgp
```
**Expected**:
```
config neighbor-group
    edit "EDGE"
        set remote-as 65000
        set activate enable
        set advertisement-interval 1

config neighbor-range
    edit 1
        set prefix 172.16.0.0 255.255.0.0
        set neighbor-group "EDGE"

config network
    edit 1
        set prefix 10.250.250.0 255.255.255.0
```

#### 8. SD-WAN Zone (Block 027)
```bash
get system sdwan
```
**Expected**:
```
status: enable
config zone
    edit "SDWAN_OVERLAY"
        set advpn-select enable

config members
    edit 100
        set interface "SPOKE_VPN1"
        set zone "SDWAN_OVERLAY"
    edit 2
        set interface "SPOKE_VPN2"
        set zone "SDWAN_OVERLAY"
```

**CRITICAL**: Verify `advpn-select: enable` (enables spoke-to-spoke shortcuts)

#### 9. SD-WAN Health Check (Block 028)
```bash
diagnose sys sdwan health-check
```
**Expected**:
```
Health Check(From_Edge):
    Server(172.16.255.252:0): alive
    Interval: 1000
    Failtime: 5
    Recoverytime: 5
```

#### 10. Firewall Policies (Block 029)
```bash
show firewall policy | grep -A2 'set name'
```
**Expected (v1.1.0 production-based policies)**:
```
set name "SDWAN_Overlay_Traffic"
set name "SDWAN_OL_To_Port2"
set name "SDWAN-BGP-LOOPBACK"
set name "BGP-TO-SDWAN"
set name "SDWAN-to-INET"
```

**CRITICAL**: Verify policy IDs are auto-assigned (not fixed 1-6)

**SECURITY**: No `WAN_to_LAN` policy should exist (removed in v1.1.0)

---

## Examples

### Example 1: Complete Hub Deployment

**Scenario**: Deploy a new hub at 10.0.1.20 for site aggregation

**Parameters**:
```yaml
HUB_HOSTNAME: howard-sdwan-hub-2
WAN_IP_CIDR: 10.0.1.20/24
LAN_IP_CIDR: 10.250.250.1/24
HUB_LOOPBACK_IP: 172.16.255.253
BGP_LOOPBACK_IP: 172.16.255.252
HUB_WAN_IP: 10.0.1.20
PSK: SecurePassword123
BGP_AS: 65000
ROUTER_ID: 172.16.255.252
ADVERTISED_NETWORKS: 10.250.250.0
ADVERTISED_NETMASK: 255.255.255.0
```

**Steps**:

1. **Prepare Config**:
```bash
cd C:\ProgramData\Ulysses\config\deployments\hub-2
cp C:/ProgramData/Ulysses/config/blueprints/ATOMIC_HUB_TEMPLATE.conf hub-2-config.conf
# Substitute parameters (manual or via script)
```

2. **Push Config**:
```
execute_certified_tool("org.ulysses.noc.fortigate-config-push/2.0.0", {
    "target_ip": "10.0.1.20",
    "config_path": "C:/ProgramData/Ulysses/config/deployments/hub-2/hub-2-config.conf"
})
```

3. **Verify (using fortigate-ssh/1.0.9)**:
```javascript
// System
execute_certified_tool("org.ulysses.noc.fortigate-ssh/1.0.9", {
    "target_ip": "10.0.1.20",
    "command": "get system global | grep hostname"
})

// Interfaces
execute_certified_tool("org.ulysses.noc.fortigate-ssh/1.0.9", {
    "target_ip": "10.0.1.20",
    "command": "get system interface Hub_Lo"
})

// IPsec
execute_certified_tool("org.ulysses.noc.fortigate-ssh/1.0.9", {
    "target_ip": "10.0.1.20",
    "command": "diagnose vpn ike gateway list"
})

// BGP
execute_certified_tool("org.ulysses.noc.fortigate-ssh/1.0.9", {
    "target_ip": "10.0.1.20",
    "command": "get router info bgp summary"
})

// SD-WAN
execute_certified_tool("org.ulysses.noc.fortigate-ssh/1.0.9", {
    "target_ip": "10.0.1.20",
    "command": "diagnose sys sdwan health-check"
})

// Firewall
execute_certified_tool("org.ulysses.noc.fortigate-ssh/1.0.9", {
    "target_ip": "10.0.1.20",
    "command": "show firewall policy | grep 'set name'"
})
```

4. **Celebrate Win**:
```
✅ Hub deployment complete!
   - Hostname: howard-sdwan-hub-2
   - WAN: 10.0.1.20
   - Hub_Lo: 172.16.255.253
   - BGP_Lo: 172.16.255.252
   - BGP AS: 65000
   - Ready for spoke connections!
```

### Example 2: Troubleshooting Failed Block

**Scenario**: Block 023 (IPsec) shows `local-gw: 0.0.0.0` instead of WAN IP

**Diagnosis**:
```bash
get vpn ipsec phase1-interface SPOKE_VPN1 | grep local-gw
```
**Result**: `local-gw: 0.0.0.0` ❌

**Problem**: Parameter substitution failed for `{{HUB_WAN_IP}}`

**Fix**:
1. Verify `HUB_WAN_IP` is defined in parameter file (not `WAN_IP_CIDR`)
2. Re-substitute parameters
3. Re-push Block 023 only:
```
execute_certified_tool("org.ulysses.noc.fortigate-config-push/2.0.0", {
    "target_ip": "10.0.1.20",
    "config_path": "C:/ProgramData/Ulysses/config/blocks/fortigate/core/023-hub-ipsec-phase1-template.block"
})
```

4. Re-verify:
```bash
get vpn ipsec phase1-interface SPOKE_VPN1 | grep local-gw
```
**Expected**: `local-gw: 10.0.1.20` ✅

### Example 3: Connecting First Spoke

**Scenario**: Hub deployed, now connect spoke-07

**Hub Verification Before Spoke Connection**:
```bash
# Check IPsec templates exist
get vpn ipsec phase1-interface
# Expected: SPOKE_VPN1, SPOKE_VPN2 (type: dynamic)

# Check BGP neighbor-range
get router bgp | grep neighbor-range
# Expected: 172.16.0.0/16 range configured

# Check SD-WAN zone
get system sdwan
# Expected: SDWAN_OVERLAY zone with advpn-select enable
```

**Connect Spoke-07**:
```
# Deploy spoke-07 with:
HUB1_IP: 10.0.1.20
HUB1_PSK: SecurePassword123
LOOPBACK_IP: 172.16.7.1 (in range 172.16.0.0/16)
BGP_AS: 65007 (65000 + 7)
```

**Hub Verification After Spoke Connection**:
```bash
# Check tunnel UP
diagnose vpn ike gateway list
# Expected: Spoke-07 tunnels in "established" state

# Check BGP session
get router info bgp summary
# Expected: 172.16.7.1 in "Established" state

# Check learned routes
get router info routing-table bgp
# Expected: Spoke-07 LAN routes learned

# Check health-check
diagnose sys sdwan health-check
# Expected: SPOKE_VPN1 and SPOKE_VPN2 members with latency metrics
```

**Celebrate Win**:
```
✅ First spoke connected!
   - Tunnels: UP
   - BGP: Established
   - Routes: Learned
   - Hub is operational!
```

---

## Error Handling

### Error 1: IPsec Tunnels Not Forming

**Symptom**:
```bash
diagnose vpn ike gateway list
# Shows no gateways or "no suitable proposal found"
```

**Diagnosis**:
1. Check `peertype any` is set:
```bash
get vpn ipsec phase1-interface SPOKE_VPN1 | grep peertype
```
**Expected**: `peertype: any`

2. Check `local-gw` is WAN IP:
```bash
get vpn ipsec phase1-interface SPOKE_VPN1 | grep local-gw
```
**Expected**: `local-gw: 10.0.1.20` (not 0.0.0.0)

3. Check PSK matches spokes:
```bash
show vpn ipsec phase1-interface SPOKE_VPN1
# Verify 'set psksecret' value
```

**Fix**:
- If `peertype` missing: Re-push Block 023 with corrected config
- If `local-gw` wrong: Update `HUB_WAN_IP` parameter and re-push
- If PSK mismatch: Update spokes or re-push hub with correct PSK

### Error 2: BGP Sessions Not Establishing

**Symptom**:
```bash
get router info bgp summary
# Shows no neighbors or "Active" state (not "Established")
```

**Diagnosis**:
1. Check neighbor-range configured:
```bash
get router bgp | grep neighbor-range
```
**Expected**: `set prefix 172.16.0.0 255.255.0.0`

2. Check spoke loopback in range:
```bash
# If spoke loopback is 172.16.7.1, it's in 172.16.0.0/16 ✅
# If spoke loopback is 10.x.x.x, it's NOT in range ❌
```

3. Check BGP loopback reachability from spokes:
```bash
# On spoke, test ping to hub BGP_Lo
execute shell-command
ping 172.16.255.252
```

**Fix**:
- If neighbor-range missing: Re-push Block 026
- If spoke loopback out of range: Reconfigure spoke loopback to 172.16.x.x
- If BGP_Lo unreachable: Check firewall policies (Block 029), verify SDWAN-BGP-LOOPBACK and BGP-TO-SDWAN policies exist

### Error 3: SD-WAN Zone Not Showing Members

**Symptom**:
```bash
get system sdwan
# Shows zone but no members
```

**Diagnosis**:
1. Check tunnel interfaces exist:
```bash
get system interface | grep SPOKE_VPN
```
**Expected**: SPOKE_VPN1, SPOKE_VPN2 interfaces present

2. Check members configured:
```bash
show system sdwan
# Look for 'config members' section
```

**Fix**:
- If tunnel interfaces missing: IPsec phase1/phase2 not configured, re-push Blocks 023, 024
- If members missing: Re-push Block 027
- If members present but zone empty: Check `set zone "SDWAN_OVERLAY"` in member config

### Error 4: Firewall Policies Overwriting Existing Policies

**Symptom**: Hub had existing policies, now they're gone after push

**Diagnosis**:
1. Check policy IDs:
```bash
get firewall policy 1
# If policy 1 is now "SDWAN_Overlay_Traffic", old policy was overwritten ❌
```

**Root Cause**: Using fixed IDs (edit 1, edit 2, etc.) instead of auto-assign (edit 0)

**Fix**:
- Use Block 029 v1.1.0 which uses `edit 0` for auto-assign
- Verify all policies use `edit 0` in config
- Restore old policies from backup if needed

**Prevention**: Always use v1.1.0+ of Block 029 for production deployments

### Error 5: Spoke-to-Spoke Traffic Not Working

**Symptom**: Spoke-07 can reach hub LAN, but cannot reach spoke-08 LAN

**Diagnosis**:
1. Check `advpn-select` enabled:
```bash
get system sdwan | grep advpn-select
```
**Expected**: `advpn-select: enable`

2. Check Overlay-to-Overlay firewall policy:
```bash
show firewall policy | grep SDWAN_Overlay_Traffic
```
**Expected**: Policy with srcintf and dstintf both including SDWAN_OVERLAY and Hub_Lo

3. Check ADVPN shortcuts:
```bash
diagnose vpn tunnel list
# Look for spoke-to-spoke tunnels (not just spoke-to-hub)
```

**Fix**:
- If `advpn-select` disabled: Re-push Block 027 with `set advpn-select enable`
- If firewall policy missing Hub_Lo: Re-push Block 029 v1.1.0
- If shortcuts not forming: Check spoke ADVPN config (auto-discovery-receiver)

---

## Prerequisites

### FortiGate Requirements

- **FortiOS Version**: 7.4.0 or higher
- **Device State**: Fresh install or factory reset (for new hubs)
- **Management Access**: SSH or HTTPS access enabled
- **Credentials**: Admin username/password or API key

### Network Requirements

- **WAN IP**: Publicly routable IP or NAT with port-forwarding for IKE (UDP 500, 4500, TCP 11443)
- **LAN Subnet**: Non-overlapping with spoke LANs
- **Loopback IPs**:
  - Hub_Lo: Unique IP in 172.16.255.0/24 range (e.g., 172.16.255.253)
  - BGP_Lo: Unique IP in 172.16.255.0/24 range (e.g., 172.16.255.252)

### Credential Setup

Add hub to fortigate_credentials.yaml:
```yaml
devices:
  - device_ip: "10.0.1.20"
    device_name: "howard-sdwan-hub-2"
    username: "admin"
    password: "YourAdminPassword"
    device_type: "fortigate"
    role: "hub"
```

### Tool Availability

Required MCP tools:
- `org.ulysses.noc.fortigate-ssh/1.0.9` (for verification commands)
- `org.ulysses.noc.fortigate-config-push/2.0.0` (for config push)

Verify tools available:
```
list_certified_tools(domain="noc", vendor="fortinet")
```

---

## Hub Manifest Tracking

### Hub ID Assignment (1-4)

Hubs are assigned sequential IDs (1, 2, 3, 4) similar to spoke tracking:

| Hub ID | Key Format | Example |
|--------|-----------|---------|
| 1 | `hub_<ip_underscored>` | `hub_192_168_215_15` |
| 2 | `hub_<ip_underscored>` | `hub_192_168_215_20` |
| 3 | `hub_<ip_underscored>` | `hub_192_168_215_25` |
| 4 | `hub_<ip_underscored>` | `hub_192_168_215_30` |

### Manifest Entry Format

Add hubs to `sdwan-manifest.yaml`:

```yaml
devices:
  # Hub 1 (Production)
  hub_192_168_215_15:
    device_name: "howard-sdwan-hub-1"
    management_ip: "10.0.1.1"
    role: "hub"
    hub_id: 1
    firmware: "v7.6.5"
    wan_ip: "10.0.1.1"
    hub_loopback: "172.16.255.253"
    bgp_loopback: "172.16.255.252"
    bgp_as: 65000
    sdwan:
      status: "enable"
      zone: "SDWAN_OVERLAY"
      members:
        - seq_num: 100
          interface: "SPOKE_VPN1"
        - seq_num: 2
          interface: "SPOKE_VPN2"
    deployed_blocks:
      - block_id: 020
        name: "hub-system-global"
        deployed_at: "2026-02-05T10:00:00"
        deployed_by: "SecBot"
      - block_id: 021
        name: "hub-system-settings"
        deployed_at: "2026-02-05T10:01:00"
        deployed_by: "SecBot"
      # ... blocks 022-029

  # Hub 2 (DR/Test)
  hub_192_168_215_20:
    device_name: "howard-sdwan-hub-2"
    management_ip: "10.0.1.20"
    role: "hub"
    hub_id: 2
    firmware: "v7.6.5"
    wan_ip: "10.0.1.20"
    hub_loopback: "172.16.255.251"
    bgp_loopback: "172.16.255.250"
    bgp_as: 65000
    sdwan:
      status: "enable"
      zone: "SDWAN_OVERLAY"
      members:
        - seq_num: 100
          interface: "SPOKE_VPN1"
        - seq_num: 2
          interface: "SPOKE_VPN2"
    deployed_blocks: []  # Pending deployment
```

### Discovery Phase (Pre-Deployment)

**Step 1: Check if Hub Already in Manifest**
```python
# Read manifest
manifest = Read("C:/ProgramData/Ulysses/config/sdwan-manifest.yaml")

# Build hub list
hubs = []
for key, device in manifest.devices.items():
    if device.role == "hub":
        hubs.append({
            "key": key,
            "hub_id": device.hub_id,
            "ip": device.management_ip,
            "name": device.device_name,
            "deployed_blocks": device.deployed_blocks or []
        })

# Output: List of hubs with deployment status
```

**Step 2: Determine Next Hub ID**
```python
# Find next available hub_id (1-4)
used_ids = [h.hub_id for h in hubs]
next_id = None
for i in range(1, 5):
    if i not in used_ids:
        next_id = i
        break

if next_id is None:
    raise Error("Maximum 4 hubs supported. Remove existing hub first.")
```

### Idempotency Check

Before deploying blocks, check manifest for already-deployed:

```python
def check_hub_blocks(hub_key, target_blocks):
    """
    Check which blocks need to be deployed.

    Args:
        hub_key: Manifest key (e.g., "hub_192_168_215_20")
        target_blocks: List of block_ids to deploy (e.g., [020, 021, ..., 029])

    Returns:
        - needs_deploy: Blocks not yet deployed
        - already_deployed: Blocks already in manifest
    """
    hub = manifest.devices[hub_key]
    deployed_ids = [b.block_id for b in hub.deployed_blocks]

    needs_deploy = [b for b in target_blocks if b not in deployed_ids]
    already_deployed = [b for b in target_blocks if b in deployed_ids]

    return needs_deploy, already_deployed
```

**Decision Matrix:**
| Manifest Has Block | Device Has Config | Action |
|--------------------|-------------------|--------|
| Yes | Yes | SKIP (idempotent) |
| Yes | No | RE-PUSH (drift detected) |
| No | Yes | UPDATE manifest only |
| No | No | PUSH block |

### Post-Deployment Manifest Update

After successful block deployment:

```python
def update_hub_manifest(hub_key, block_id, block_name):
    """Update manifest with deployed block."""
    manifest.devices[hub_key].deployed_blocks.append({
        "block_id": block_id,
        "name": block_name,
        "deployed_at": datetime.now().isoformat(),
        "deployed_by": "SecBot"
    })

    # Write manifest once at end (not after each block)
    Write("C:/ProgramData/Ulysses/config/sdwan-manifest.yaml", manifest)
```

### Deployment Report

Generate report after hub deployment:

```
Hub Deployment Report
=====================
Hub: howard-sdwan-hub-2 (10.0.1.20)
Hub ID: 2
Timestamp: 2026-02-05T15:30:00

DEPLOYED BLOCKS (10):
  ✓ 020 hub-system-global
  ✓ 021 hub-system-settings
  ✓ 022 hub-interfaces
  ✓ 023 hub-ipsec-phase1-template
  ✓ 024 hub-ipsec-phase2-template
  ✓ 025 hub-bgp-base
  ✓ 026 hub-bgp-neighbor-range
  ✓ 027 hub-sdwan-zone
  ✓ 028 hub-sdwan-healthcheck
  ✓ 029 hub-firewall-policies (v1.1.0)

SKIPPED (0):
  (none)

ERRORS (0):
  (none)

Summary: 10 deployed, 0 skipped, 0 errors
Hub ready for spoke connections!
```

### Validation Mode

Verify manifest matches device state:

```python
def validate_hub_deployment(hub_key):
    """Compare manifest to actual device config."""
    hub = manifest.devices[hub_key]

    # Query device for each deployed block's verification
    drift = []

    for block in hub.deployed_blocks:
        result = execute_certified_tool(
            canonical_id="org.ulysses.noc.fortigate-ssh/1.0.9",
            parameters={
                "target_ip": hub.management_ip,
                "command": get_verification_command(block.block_id)
            }
        )

        if not result.success:
            drift.append(f"QUERY_FAILED: Block {block.block_id}")
        elif not verify_output(block.block_id, result.output):
            drift.append(f"CONFIG_DRIFT: Block {block.block_id}")

    return {"status": "valid" if not drift else "drift", "drift": drift}
```

---

## Related Tools

### Primary Tools

1. **fortigate-config-push/2.0.0**
   - Purpose: Push complete config files to FortiGate
   - Use: Deploy ATOMIC_HUB_TEMPLATE.conf in single operation
   - Skills: See `C:\ProgramData\Ulysses\components\trust-anchor\noc\fortigate-config-push\Skills.md`

2. **fortigate-ssh/1.0.9**
   - Purpose: Execute single CLI commands for verification
   - Use: Run verification commands after each block/deployment
   - Parameter: `command` (singular, not array)
   - Skills: See `C:\ProgramData\Ulysses\components\trust-anchor\noc\fortigate-ssh\Skills.md`

### Complementary Workflows

1. **add-sdwan-site** (Spoke Deployment)
   - Purpose: Deploy spokes that connect to this hub
   - Coordination: Hub PSK, hub WAN IP, BGP AS must match
   - Skills: See `C:\ProgramData\Ulysses\config\workflows\add-sdwan-site\Skills.md`

2. **fortigate-health-check** (Hub Monitoring)
   - Purpose: Monitor hub health after deployment
   - Use: Periodic verification of tunnel status, BGP sessions, health-checks
   - Skills: See trust-anchor tool shelf

### Block-Level Tools

Individual block files for incremental push:
- Block 020: `C:\ProgramData\Ulysses\config\blocks\fortigate\core\020-hub-system-global.block`
- Block 021: `C:\ProgramData\Ulysses\config\blocks\fortigate\core\021-hub-system-settings.block`
- Block 022: `C:\ProgramData\Ulysses\config\blocks\fortigate\core\022-hub-interfaces.block`
- Block 023: `C:\ProgramData\Ulysses\config\blocks\fortigate\core\023-hub-ipsec-phase1-template.block`
- Block 024: `C:\ProgramData\Ulysses\config\blocks\fortigate\core\024-hub-ipsec-phase2-template.block`
- Block 025: `C:\ProgramData\Ulysses\config\blocks\fortigate\core\025-hub-bgp-base.block`
- Block 026: `C:\ProgramData\Ulysses\config\blocks\fortigate\core\026-hub-bgp-neighbor-range.block`
- Block 027: `C:\ProgramData\Ulysses\config\blocks\fortigate\core\027-hub-sdwan-zone.block`
- Block 028: `C:\ProgramData\Ulysses\config\blocks\fortigate\core\028-hub-sdwan-healthcheck.block`
- Block 029: `C:\ProgramData\Ulysses\config\blocks\fortigate\core\029-hub-firewall-policies.block` (v1.1.0)

---

## SecBot Communication Patterns

### Phase 1: Pre-Deployment
**Voice**: Excited, thorough
```
🎯 Hub deployment starting!

Let me verify prerequisites:
✅ FortiGate reachable at 10.0.1.20
✅ Credentials loaded
✅ ATOMIC_HUB_TEMPLATE.conf prepared
✅ All parameters validated

Ready to deploy 10 blocks. Let's build this hub! 🚀
```

### Phase 2: During Deployment
**Voice**: Confident, progress-focused
```
📦 Pushing ATOMIC_HUB_TEMPLATE.conf...

Block 020: System Global ✅
Block 021: System Settings ✅
Block 022: Interfaces (Dual Loopback) ✅
Block 023: IPsec Phase1 Templates ✅
Block 024: IPsec Phase2 Selectors ✅
Block 025: BGP Base ✅
Block 026: BGP Neighbor Range ✅
Block 027: SD-WAN Zone ✅
Block 028: SD-WAN Health Check ✅
Block 029: Firewall Policies (v1.1.0) ✅

Config push complete! Now verifying... 🔍
```

### Phase 3: Verification
**Voice**: Methodical, verification-obsessed
```
🔍 Verifying deployment:

✅ Hostname: howard-sdwan-hub-2
✅ Hub_Lo: 172.16.255.253
✅ BGP_Lo: 172.16.255.252
✅ IPsec templates: SPOKE_VPN1, SPOKE_VPN2 (type: dynamic, peertype: any)
✅ BGP AS: 65000, Router-ID: 172.16.255.252
✅ Neighbor-range: 172.16.0.0/16 (accepts all spokes)
✅ SD-WAN zone: SDWAN_OVERLAY (advpn-select: enable)
✅ Firewall policies: 5 policies (v1.1.0 production-based)

All checks passed! Hub is ready for spoke connections! 🎉
```

### Phase 4: Error Escalation
**Voice**: Direct, solution-focused
```
❌ Problem detected: IPsec local-gw showing 0.0.0.0

Root cause: HUB_WAN_IP parameter not substituted

Fix required:
1. Update parameter file with HUB_WAN_IP=10.0.1.20
2. Re-push Block 023

Escalating to user for parameter file update.
Would you like me to show you the exact parameter format needed? 🛠️
```

### Phase 5: Success Celebration
**Voice**: Happy-go-lucky, ready for next
```
🎉 Hub deployment SUCCESS!

Summary:
- Hub: howard-sdwan-hub-2 (10.0.1.20)
- Dual loopbacks configured (Hub_Lo + BGP_Lo)
- IPsec templates ready for dynamic spokes
- BGP accepting 172.16.0.0/16 range
- ADVPN shortcuts enabled
- Ready for production spoke connections!

Next steps:
- Deploy spoke-07 with HUB1_IP=10.0.1.20
- PSK must match: SecurePassword123
- Spoke loopback must be in 172.16.0.0/16 range

Let's connect some spokes! 🚀
```

---

## Gap Analysis Integration

This workflow incorporates fixes from GAP analysis:

- **GAP-51**: Hub seq (100/2) independent from spoke seq (3/4) - documented in Block 027
- **GAP-52**: peertype any required for dynamic spokes - fixed in Block 023
- **GAP-53**: local-gw must be WAN IP, not 0.0.0.0 - fixed in Block 023
- **GAP-54**: Different dpd settings for VPN1 vs VPN2 - implemented in Block 023
- **GAP-55**: Firewall policy auto-assign (edit 0) to avoid overwriting - fixed in Block 029 v1.1.0
- **GAP-56**: location-id accepts IP address type in FortiOS 7.x - clarified in Block 021
- **GAP-57**: Dual loopback architecture (Hub_Lo + BGP_Lo) - documented throughout

---

## Version History

- **v1.0.0** (2026-02-05): Initial Skills.md creation
  - All 10 hub blocks (020-029) complete
  - ATOMIC_HUB_TEMPLATE.conf ready
  - SecBot persona integrated
  - Production-based on howard-sdwan-hub-1 (10.0.1.1)

---

## Support and Escalation

**For Issues**:
1. Check Error Handling section first
2. Verify all prerequisites met
3. Review verification commands for failed block
4. Escalate to network engineering if credentials fail or device unreachable

**For Questions**:
- Review NFR-025 (Composable Config Block Framework)
- Review ALIGNMENT-SPOKE-HUB-WORKFLOWS.md
- Check individual block .block files for detailed parameter descriptions

**Happy Hub Deployment!** 🎉
