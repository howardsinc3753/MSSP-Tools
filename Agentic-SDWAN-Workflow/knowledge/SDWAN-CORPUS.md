# FortiGate SD-WAN Knowledge Corpus

**Version:** 1.0.0
**FortiOS Target:** 7.6.x
**Last Updated:** 2025-01-14
**Purpose:** Reference for building SDWAN provisioning tools

---

## Source References

| Resource | URL | Description |
|----------|-----|-------------|
| ADVPN Reference (7.6) | https://github.com/fortinet-solutions-cse/sdwan-advpn-reference/tree/release/7.6 | Jinja templates for Hub/Spoke |
| 4D Demo Configs | https://github.com/fortinet/4D-Demo/tree/main/4D-SDWAN/7.6 | Single/Dual Hub examples |
| Fortinet SD-WAN Docs | https://docs.fortinet.com/4d-resources/SD-WAN | Official documentation |

---

## Architecture Overview

### Deployment Models

| Model | Description | Use Case |
|-------|-------------|----------|
| Single Hub | One datacenter hub | Small deployments |
| Dual Hub | Primary/Secondary DCs | Redundancy |
| Multi-Region | Multiple regional hubs | Global enterprise |
| MSSP | Multi-tenant overlay | Service provider |

### Component Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                      REGION (AS 65001)                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐                    ┌─────────────┐         │
│  │   HUB-1     │◄──── iBGP ────────►│   HUB-2     │         │
│  │  (DC-West)  │     Route          │  (DC-East)  │         │
│  │             │    Reflector       │             │         │
│  └──────┬──────┘                    └──────┬──────┘         │
│         │ IPsec/ADVPN                      │                │
│         │                                  │                │
│  ┌──────▼──────┐  ┌─────────────┐  ┌──────▼──────┐         │
│  │   SPOKE-1   │  │   SPOKE-2   │  │   SPOKE-3   │         │
│  │  (Branch)   │  │  (Branch)   │  │  (Branch)   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

---

## Hub Configuration

### 1. Underlay (01-Hub-Underlay)

**Purpose:** Physical interfaces, zones, basic connectivity

```fortios
# System Settings
config system settings
    set location-id {loopback_ip}
    set allow-subnet-overlap enable
end

# Loopback Interfaces
config system interface
    edit "Lo"
        set vdom "root"
        set type loopback
        set ip {loopback}/32
        set allowaccess ping
    next
    edit "Lo-HC"
        set vdom "root"
        set type loopback
        set ip 10.200.99.1/32
        set allowaccess ping
        set description "Health-check responder"
    next
end

# WAN Zone
config system zone
    edit "WAN"
        set interface "wan1" "wan2"
    next
end

# LAN Zone
config system zone
    edit "LAN"
        set interface "port1" "port2"
    next
end
```

**Key Variables:**
- `loopback`: Device identity IP (/32)
- `Lo-HC`: Health check responder (10.200.99.1/32)
- `pe_vrf`: Provider Edge VRF (0 or 1)

### 2. Overlay (02-Hub-Overlay)

**Purpose:** IPsec tunnels, ADVPN auto-discovery

```fortios
# IPsec Phase 1 - Dynamic (accepts spoke connections)
config vpn ipsec phase1-interface
    edit "H1_INET"
        set type dynamic
        set interface "wan1"
        set ike-version 2
        set peertype any
        set net-device disable
        set mode-cfg enable
        set proposal aes256gcm-prfsha256 aes256-sha256
        set dpd on-idle
        set dpd-retrycount 2
        set dpd-retryinterval 5
        set psksecret {psk}
        # OR for certificate auth:
        # set authmethod signature
        # set certificate "{cert_name}"
        set exchange-ip-addr4 {loopback}
        set auto-discovery-sender enable
        set add-route disable
    next
end

# IPsec Phase 2
config vpn ipsec phase2-interface
    edit "H1_INET_P2"
        set phase1name "H1_INET"
        set proposal aes256gcm
        set keepalive enable
    next
end
```

**ADVPN Settings:**
- `auto-discovery-sender enable`: Hub advertises to spokes
- `exchange-ip-addr4`: Loopback for dynamic BGP peering
- `mode-cfg enable`: Push config to spokes

### 3. Routing (03-Hub-Routing)

**Purpose:** BGP configuration, route reflection

```fortios
config router bgp
    set as {region_as}
    set router-id {loopback}
    set keepalive-timer 15
    set holdtime-timer 45
    set ibgp-multipath enable
    set ebgp-multipath enable
    set recursive-next-hop enable
    set graceful-restart enable

    # Neighbor Group for Spokes
    config neighbor-group
        edit "EDGE"
            set remote-as {region_as}
            set update-source "Lo"
            set route-reflector-client enable
            set soft-reconfiguration enable
            set next-hop-self enable
        next
    end

    # Dynamic Neighbor Range
    config neighbor-range
        edit 1
            set prefix {spoke_summary}
            set neighbor-group "EDGE"
        next
    end

    # Network Advertisements
    config network
        edit 1
            set prefix {lo_summary}
            set route-map "LOCAL_REGION"
        next
    end
end

# Route Maps
config router route-map
    edit "LOCAL_REGION"
        config rule
            edit 1
                set set-community no-export
                set set-tag 100
            next
        end
    next
    edit "LAN_TAG"
        config rule
            edit 1
                set set-tag 100
            next
        end
    next
end
```

**BGP Parameters:**
- AS: Regional AS number (e.g., 65001)
- Router-ID: Loopback IP
- Route Reflector: Hub reflects routes to spokes
- iBGP Multipath: Load balance across equal-cost paths

---

## Spoke/Edge Configuration

### 1. Underlay (01-Edge-Underlay)

```fortios
# WAN Interfaces with Bandwidth Shaping
config system interface
    edit "wan1"
        set vdom "root"
        set mode dhcp
        set role wan
        set estimated-upstream-bandwidth 100000
        set estimated-downstream-bandwidth 100000
    next
    edit "wan2"
        set vdom "root"
        set mode dhcp
        set role wan
        set estimated-upstream-bandwidth 50000
        set estimated-downstream-bandwidth 50000
    next
end

# Loopback for BGP
config system interface
    edit "Lo"
        set vdom "root"
        set type loopback
        set ip {spoke_loopback}/32
        set allowaccess ping
    next
end
```

### 2. Overlay (02-Edge-Overlay)

```fortios
# IPsec Phase 1 - Dial-up to Hub
config vpn ipsec phase1-interface
    edit "H1_INET"
        set interface "wan1"
        set ike-version 2
        set peertype any
        set net-device disable
        set proposal aes256gcm-prfsha256 aes256-sha256
        set dpd on-idle
        set dpd-retrycount 3
        set dpd-retryinterval 5
        set idle-timeout enable
        set remote-gw {hub1_wan_ip}
        set psksecret {psk}
        set exchange-ip-addr4 {spoke_loopback}
        set auto-discovery-receiver enable
        set add-route disable
    next
end

# IPsec Phase 2
config vpn ipsec phase2-interface
    edit "H1_INET_P2"
        set phase1name "H1_INET"
        set proposal aes256gcm
        set keepalive enable
    next
end
```

**ADVPN Settings for Spoke:**
- `auto-discovery-receiver enable`: Learns shortcut routes
- `idle-timeout enable`: Cleans up unused tunnels

### 3. Routing (03-Edge-Routing)

```fortios
config router bgp
    set as {region_as}
    set router-id {spoke_loopback}
    set keepalive-timer 15
    set holdtime-timer 45
    set ibgp-multipath enable
    set recursive-next-hop enable
    set graceful-restart enable

    # Hub Neighbors
    config neighbor
        edit {hub1_loopback}
            set remote-as {region_as}
            set update-source "Lo"
            set soft-reconfiguration enable
        next
        edit {hub2_loopback}
            set remote-as {region_as}
            set update-source "Lo"
            set soft-reconfiguration enable
        next
    end

    # Advertise LAN Networks
    config network
        edit 1
            set prefix {lan_subnet}
            set route-map "LAN_TAG"
        next
    end
end
```

---

## SD-WAN Configuration

### Health Checks (Performance SLA)

```fortios
config system sdwan
    set status enable

    # Define Members
    config members
        edit 1
            set interface "H1_INET"
            set zone "virtual-wan-link"
        next
        edit 2
            set interface "H2_INET"
            set zone "virtual-wan-link"
        next
    end

    # Health Checks
    config health-check
        edit "HUB"
            set server {hub_hc_ip}
            set protocol ping
            set interval 1000
            set probe-timeout 500
            set failtime 3
            set recoverytime 3
            set sla-fail-log-period 30
            set members 1 2
            config sla
                edit 1
                    set latency-threshold 100
                    set jitter-threshold 50
                    set packetloss-threshold 5
                next
            end
        next
        edit "INTERNET"
            set server "8.8.8.8" "1.1.1.1"
            set protocol ping
            set interval 1000
            set members 1 2
            config sla
                edit 1
                    set latency-threshold 150
                    set jitter-threshold 100
                    set packetloss-threshold 10
                next
            end
        next
    end
end
```

**Health Check Protocols:**
- `ping`: ICMP echo
- `http`: HTTP GET
- `dns`: DNS query
- `tcp-echo`: TCP connection
- `udp-echo`: UDP probe
- `twamp`: RFC 5357 measurement

**SLA Metrics:**
- Latency (ms)
- Jitter (ms)
- Packet Loss (%)
- MOS (Mean Opinion Score)

### SD-WAN Rules

```fortios
config system sdwan
    config service
        # Implicit Default Rule
        edit 1
            set name "DEFAULT"
            set mode sla
            set dst "all"
            set src "all"
            config sla
                edit "HUB"
                    set id 1
                next
            end
            set priority-members 1 2
        next

        # Best Quality for Voice
        edit 2
            set name "VOICE"
            set mode priority
            set protocol 17
            set start-port 5060
            set end-port 5061
            set health-check "HUB"
            set priority-members 1 2
        next

        # Lowest Cost for Bulk
        edit 3
            set name "BULK"
            set mode sla
            set dst "all"
            set internet-service enable
            set internet-service-app-ctrl 16354  # Windows Update
            config sla
                edit "INTERNET"
                    set id 1
                next
            end
            set priority-members 2 1
        next
    end
end
```

**Steering Modes:**
| Mode | Description |
|------|-------------|
| `manual` | Fixed member priority |
| `priority` | Ordered preference list |
| `sla` | SLA-based selection |
| `load-balance` | Distribute across members |

---

## API Endpoints Reference

### SD-WAN Monitor APIs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v2/monitor/system/sdwan/health-check` | GET | Health check status |
| `/api/v2/monitor/system/sdwan/members` | GET | Member interface status |
| `/api/v2/monitor/system/sdwan/neighbor` | GET | SD-WAN neighbor info |
| `/api/v2/monitor/router/bgp/paths` | GET | BGP path information |
| `/api/v2/monitor/router/bgp/neighbors` | GET | BGP neighbor status |

### SD-WAN Configuration APIs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v2/cmdb/system/sdwan` | GET/PUT | SD-WAN global config |
| `/api/v2/cmdb/system/sdwan/members` | GET/POST | Member interfaces |
| `/api/v2/cmdb/system/sdwan/health-check` | GET/POST | Health checks |
| `/api/v2/cmdb/system/sdwan/service` | GET/POST | SD-WAN rules |
| `/api/v2/cmdb/system/sdwan/zone` | GET/POST | SD-WAN zones |

### VPN APIs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v2/cmdb/vpn.ipsec/phase1-interface` | GET/POST | IPsec Phase 1 |
| `/api/v2/cmdb/vpn.ipsec/phase2-interface` | GET/POST | IPsec Phase 2 |
| `/api/v2/monitor/vpn/ipsec` | GET | IPsec tunnel status |

### BGP APIs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v2/cmdb/router/bgp` | GET/PUT | BGP configuration |
| `/api/v2/cmdb/router/bgp/neighbor` | GET/POST | BGP neighbors |
| `/api/v2/cmdb/router/route-map` | GET/POST | Route maps |

---

## Tool Development Targets

### Priority 1: Hub Provisioning

| Tool | Purpose | API Used |
|------|---------|----------|
| `fortigate-sdwan-hub-init` | Initialize SD-WAN hub | Multiple |
| `fortigate-sdwan-overlay-create` | Create overlay tunnels | vpn.ipsec |
| `fortigate-bgp-hub-config` | Configure BGP RR | router/bgp |

### Priority 2: Spoke Provisioning

| Tool | Purpose | API Used |
|------|---------|----------|
| `fortigate-sdwan-spoke-join` | Join spoke to hub | vpn.ipsec, bgp |
| `fortigate-sdwan-health-check` | Configure health checks | system/sdwan |
| `fortigate-sdwan-rule-create` | Add steering rules | system/sdwan/service |

### Priority 3: Monitoring

| Tool | Purpose | API Used |
|------|---------|----------|
| `fortigate-sdwan-status` | Overall SD-WAN health | monitor/system/sdwan |
| `fortigate-bgp-neighbor-status` | BGP peer status | monitor/router/bgp |
| `fortigate-vpn-tunnel-status` | IPsec tunnel health | monitor/vpn/ipsec |

---

## Configuration Variables Reference

### Project-Level Variables

```yaml
project:
  name: "my-sdwan"
  lo_summary: "10.200.0.0/14"
  regions:
    region1:
      as: 65001
      hubs:
        - name: "DC-WEST"
          loopback: "10.200.1.1"
          wan_ip: "203.0.113.1"
        - name: "DC-EAST"
          loopback: "10.200.1.2"
          wan_ip: "203.0.113.2"
```

### Device-Level Variables

```yaml
device:
  hostname: "FG-BRANCH-001"
  loopback: "10.200.10.1"
  region: "region1"
  profile: "spoke"
  interfaces:
    - name: "wan1"
      role: "wan"
      ip: "dhcp"
    - name: "port1"
      role: "lan"
      ip: "192.168.1.1/24"
```

---

## CLI Command Quick Reference

### Diagnostics

```fortios
# SD-WAN Status
diagnose sys sdwan health-check-info
diagnose sys sdwan member-info
diagnose sys sdwan service-info

# BGP Status
get router info bgp summary
get router info bgp neighbors
diagnose ip router bgp all

# IPsec Status
diagnose vpn ipsec status
diagnose vpn tunnel list
get vpn ipsec tunnel summary
```

### Configuration Verification

```fortios
# Show SD-WAN Config
show system sdwan
show full-configuration system sdwan

# Show BGP Config
show router bgp
get router info routing-table all

# Show VPN Config
show vpn ipsec phase1-interface
show vpn ipsec phase2-interface
```

---

## Next Steps

1. **Build `fortigate-sdwan-hub-init`** - Complete hub provisioning
2. **Build `fortigate-sdwan-spoke-join`** - Spoke onboarding
3. **Build `fortigate-sdwan-status`** - Monitoring dashboard
4. **Create runbook: `sdwan-site-onboard`** - End-to-end automation
