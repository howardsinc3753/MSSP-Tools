# SD-WAN Tool Development Targets

**Priority Order for fortigate-ops Solution Pack**

---

## Phase 1: Foundation Tools

### Tool 1: `fortigate-sdwan-status`
**Domain:** NOC
**Priority:** P0

**Purpose:** Get comprehensive SD-WAN health status

**API Calls:**
- `GET /api/v2/monitor/system/sdwan/health-check`
- `GET /api/v2/monitor/system/sdwan/members`

**Parameters:**
```yaml
target_ip: string (required)
include_sla_history: boolean (default: false)
```

**Output:**
```yaml
success: boolean
members:
  - interface: string
    status: string (up/down)
    health_checks:
      - name: string
        latency_ms: number
        jitter_ms: number
        packet_loss_pct: number
        sla_met: boolean
```

---

### Tool 2: `fortigate-bgp-status`
**Domain:** NOC
**Priority:** P0

**Purpose:** Get BGP neighbor status and route summary

**API Calls:**
- `GET /api/v2/monitor/router/bgp/neighbors`
- `GET /api/v2/monitor/router/bgp/paths` (optional)

**Parameters:**
```yaml
target_ip: string (required)
include_routes: boolean (default: false)
neighbor_filter: string (optional - filter by neighbor IP)
```

**Output:**
```yaml
success: boolean
local_as: integer
router_id: string
neighbors:
  - ip: string
    remote_as: integer
    state: string
    uptime_seconds: integer
    prefixes_received: integer
    prefixes_sent: integer
```

---

### Tool 3: `fortigate-vpn-tunnel-status`
**Domain:** NOC
**Priority:** P0

**Purpose:** Get IPsec tunnel status for SD-WAN overlays

**API Calls:**
- `GET /api/v2/monitor/vpn/ipsec`

**Parameters:**
```yaml
target_ip: string (required)
tunnel_filter: string (optional - filter by tunnel name)
```

**Output:**
```yaml
success: boolean
tunnels:
  - name: string
    status: string (up/down)
    remote_gateway: string
    incoming_bytes: integer
    outgoing_bytes: integer
    tunnel_ip: string
```

---

## Phase 2: Hub Provisioning Tools

### Tool 4: `fortigate-loopback-create`
**Domain:** Provisioning
**Priority:** P1

**Purpose:** Create loopback interface for BGP/SDWAN

**API Calls:**
- `POST /api/v2/cmdb/system/interface`

**Parameters:**
```yaml
target_ip: string (required)
loopback_name: string (default: "Lo")
loopback_ip: string (required - e.g., "10.200.1.1/32")
allow_ping: boolean (default: true)
```

---

### Tool 5: `fortigate-ipsec-hub-create`
**Domain:** Provisioning
**Priority:** P1

**Purpose:** Create Hub-side IPsec tunnel (dynamic/dial-up server)

**API Calls:**
- `POST /api/v2/cmdb/vpn.ipsec/phase1-interface`
- `POST /api/v2/cmdb/vpn.ipsec/phase2-interface`

**Parameters:**
```yaml
target_ip: string (required)
tunnel_name: string (required)
wan_interface: string (required - e.g., "wan1")
psk: string (required)
hub_loopback: string (required - for exchange-ip)
enable_advpn: boolean (default: true)
network_id: integer (optional - for multi-vrf)
```

---

### Tool 6: `fortigate-bgp-hub-config`
**Domain:** Provisioning
**Priority:** P1

**Purpose:** Configure BGP on Hub as Route Reflector

**API Calls:**
- `PUT /api/v2/cmdb/router/bgp`
- `POST /api/v2/cmdb/router/bgp/neighbor-group`
- `POST /api/v2/cmdb/router/bgp/neighbor-range`

**Parameters:**
```yaml
target_ip: string (required)
as_number: integer (required)
router_id: string (required - loopback IP)
spoke_prefix: string (required - e.g., "10.200.0.0/16")
neighbor_group_name: string (default: "EDGE")
enable_route_reflector: boolean (default: true)
```

---

## Phase 3: Spoke Provisioning Tools

### Tool 7: `fortigate-ipsec-spoke-create`
**Domain:** Provisioning
**Priority:** P1

**Purpose:** Create Spoke-side IPsec tunnel to Hub

**API Calls:**
- `POST /api/v2/cmdb/vpn.ipsec/phase1-interface`
- `POST /api/v2/cmdb/vpn.ipsec/phase2-interface`

**Parameters:**
```yaml
target_ip: string (required)
tunnel_name: string (required)
wan_interface: string (required)
hub_wan_ip: string (required - hub public IP)
psk: string (required)
spoke_loopback: string (required)
enable_advpn: boolean (default: true)
```

---

### Tool 8: `fortigate-bgp-spoke-config`
**Domain:** Provisioning
**Priority:** P1

**Purpose:** Configure BGP on Spoke to peer with Hub(s)

**API Calls:**
- `PUT /api/v2/cmdb/router/bgp`
- `POST /api/v2/cmdb/router/bgp/neighbor`
- `POST /api/v2/cmdb/router/bgp/network`

**Parameters:**
```yaml
target_ip: string (required)
as_number: integer (required)
router_id: string (required - spoke loopback)
hub_loopbacks: list[string] (required - hub loopback IPs)
advertise_networks: list[string] (optional - LAN prefixes)
```

---

### Tool 9: `fortigate-sdwan-member-add`
**Domain:** Provisioning
**Priority:** P1

**Purpose:** Add interface to SD-WAN

**API Calls:**
- `POST /api/v2/cmdb/system/sdwan/members`

**Parameters:**
```yaml
target_ip: string (required)
interface_name: string (required)
zone: string (default: "virtual-wan-link")
cost: integer (default: 0)
weight: integer (default: 1)
gateway: string (default: "0.0.0.0")
```

---

### Tool 10: `fortigate-sdwan-healthcheck-create`
**Domain:** Provisioning
**Priority:** P1

**Purpose:** Create SD-WAN health check

**API Calls:**
- `POST /api/v2/cmdb/system/sdwan/health-check`

**Parameters:**
```yaml
target_ip: string (required)
name: string (required)
server: list[string] (required - probe targets)
protocol: string (default: "ping", enum: ping|http|dns|tcp-echo)
interval_ms: integer (default: 1000)
failtime: integer (default: 3)
recoverytime: integer (default: 3)
latency_threshold: integer (default: 100)
jitter_threshold: integer (default: 50)
packetloss_threshold: integer (default: 5)
members: list[integer] (required - member seq nums)
```

---

### Tool 11: `fortigate-sdwan-rule-create`
**Domain:** Provisioning
**Priority:** P2

**Purpose:** Create SD-WAN steering rule

**API Calls:**
- `POST /api/v2/cmdb/system/sdwan/service`

**Parameters:**
```yaml
target_ip: string (required)
name: string (required)
mode: string (required, enum: manual|priority|sla|load-balance)
health_check: string (optional)
priority_members: list[integer] (optional)
dst_address: string (default: "all")
src_address: string (default: "all")
protocol: integer (optional - 6=TCP, 17=UDP)
start_port: integer (optional)
end_port: integer (optional)
```

---

## Phase 4: Composite Runbooks

### Runbook: `sdwan-hub-bootstrap`
**Steps:**
1. `fortigate-loopback-create`
2. `fortigate-ipsec-hub-create`
3. `fortigate-bgp-hub-config`
4. `fortigate-sdwan-member-add`
5. `fortigate-sdwan-healthcheck-create`

### Runbook: `sdwan-spoke-onboard`
**Steps:**
1. `fortigate-loopback-create`
2. `fortigate-ipsec-spoke-create`
3. `fortigate-bgp-spoke-config`
4. `fortigate-sdwan-member-add`
5. `fortigate-sdwan-healthcheck-create`
6. `fortigate-sdwan-rule-create` (default)

---

## Development Order

| Order | Tool | Type | Depends On |
|-------|------|------|------------|
| 1 | `fortigate-sdwan-status` | Monitor | - |
| 2 | `fortigate-bgp-status` | Monitor | - |
| 3 | `fortigate-vpn-tunnel-status` | Monitor | - |
| 4 | `fortigate-loopback-create` | Provision | - |
| 5 | `fortigate-ipsec-hub-create` | Provision | #4 |
| 6 | `fortigate-bgp-hub-config` | Provision | #4 |
| 7 | `fortigate-ipsec-spoke-create` | Provision | #4 |
| 8 | `fortigate-bgp-spoke-config` | Provision | #4, #7 |
| 9 | `fortigate-sdwan-member-add` | Provision | #5 or #7 |
| 10 | `fortigate-sdwan-healthcheck-create` | Provision | #9 |
| 11 | `fortigate-sdwan-rule-create` | Provision | #10 |

---

## Which Tool First?

**Recommended starting point:** `fortigate-sdwan-status`

Why:
- Read-only (safe)
- Validates API connectivity
- Useful immediately for monitoring
- Tests the SD-WAN API surface

Then proceed with `fortigate-loopback-create` as first provisioning tool.
