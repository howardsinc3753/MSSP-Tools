# FortiGate SD-WAN Status Tool

## Purpose
Diagnostic tool for retrieving real-time SD-WAN operational status from FortiGate devices. Provides unified view of health check probes, SD-WAN members, BGP neighbors, and IPsec tunnels.

Based on FortiOS monitor API endpoints for live operational data.

## When to Use
- Troubleshooting SD-WAN path selection issues
- Verifying health check probe status (latency, jitter, packet loss)
- Checking BGP neighbor session states
- Validating IPsec tunnel connectivity
- Quick health assessment of SD-WAN overlay network

## What It Shows

### Health Check Probes
Real-time SLA metrics from SD-WAN health checks:
```
Health Check: HUB_Health
├── Member: HUB1-VPN1
│   ├── Status: alive/dead
│   ├── Latency: 15.2ms
│   ├── Jitter: 2.1ms
│   └── Packet Loss: 0%
└── Member: HUB2-VPN2
    ├── Status: alive
    ├── Latency: 12.8ms
    └── Jitter: 1.5ms
```

### BGP Neighbors
BGP session states and route counts:
```
Neighbor: 172.16.255.253
├── State: Established
├── Remote AS: 65000
├── Routes Received: 5
└── Uptime: 2d 5h
```

### IPsec Tunnels
VPN tunnel status:
```
Tunnel: HUB1-VPN1
├── Phase1: up/down
├── Phase2: up/down
├── Incoming SA: active
└── Outgoing SA: active
```

## Parameters

### Required
| Parameter | Type | Description |
|-----------|------|-------------|
| target_ip | string | FortiGate management IP |

### Optional Filters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| include_health_checks | boolean | true | Include health check probe status |
| include_members | boolean | true | Include SD-WAN member status |
| include_bgp | boolean | true | Include BGP neighbor status |
| include_ipsec | boolean | true | Include IPsec tunnel status |
| health_check_name | string | - | Filter to specific health check |

## Usage Examples

### Full Status Check
```json
{
  "target_ip": "10.0.0.30"
}
```

### Health Checks Only
```json
{
  "target_ip": "10.0.0.30",
  "include_health_checks": true,
  "include_members": false,
  "include_bgp": false,
  "include_ipsec": false
}
```

### Specific Health Check
```json
{
  "target_ip": "10.0.0.30",
  "health_check_name": "HUB_Health"
}
```

### BGP and IPsec Only
```json
{
  "target_ip": "10.0.0.30",
  "include_health_checks": false,
  "include_members": false,
  "include_bgp": true,
  "include_ipsec": true
}
```

## CLI Equivalents

### Health Check Status
```
diagnose sys sdwan health-check status
```

### SD-WAN Member Status
```
diagnose sys sdwan member
```

### BGP Neighbors
```
get router info bgp summary
diagnose ip router bgp neighbor-info <ip>
```

### IPsec Tunnels
```
diagnose vpn tunnel list
get vpn ipsec tunnel summary
```

## Output Examples

### Full Status Response
```json
{
  "success": true,
  "target_ip": "10.0.0.30",
  "health_checks": [
    {
      "name": "HUB_Health",
      "members": [
        {
          "interface": "HUB1-VPN1",
          "status": "alive",
          "latency": 15.2,
          "jitter": 2.1,
          "packet_loss": 0.0,
          "sla_targets_met": 1
        },
        {
          "interface": "HUB2-VPN2",
          "status": "alive",
          "latency": 12.8,
          "jitter": 1.5,
          "packet_loss": 0.0,
          "sla_targets_met": 1
        }
      ]
    }
  ],
  "bgp_neighbors": [
    {
      "neighbor_ip": "172.16.255.253",
      "remote_as": 65000,
      "state": "Established",
      "routes_received": 5,
      "uptime": "2d 5h 30m"
    }
  ],
  "ipsec_tunnels": [
    {
      "name": "HUB1-VPN1",
      "phase1_status": "up",
      "phase2_status": "up",
      "incoming_bytes": 1234567,
      "outgoing_bytes": 7654321
    }
  ],
  "summary": {
    "health_checks_up": 2,
    "health_checks_down": 0,
    "bgp_established": 1,
    "bgp_down": 1,
    "ipsec_up": 1,
    "ipsec_down": 1
  }
}
```

## Interpreting Results

### Health Check States
| Status | Meaning |
|--------|---------|
| alive | Probe responding, SLA may or may not be met |
| dead | Probe not responding |

### BGP States
| State | Meaning |
|-------|---------|
| Established | Session up, routes exchanging |
| Connect | TCP connection attempt |
| Active | Waiting for connection |
| Idle | Session not started |
| OpenSent | OPEN message sent |
| OpenConfirm | OPEN received, waiting confirmation |

### IPsec States
| Status | Meaning |
|--------|---------|
| up | Tunnel established |
| down | Tunnel not established |
| connecting | Negotiation in progress |

## Troubleshooting Scenarios

### Health Check Dead
1. Check IPsec tunnel status - Phase2 must be up
2. Verify firewall policy allows probe traffic
3. Check health check server IP is reachable
4. Verify probe protocol (ping/http/dns)

### BGP Stuck in Connect
1. Check IPsec tunnel - must be Phase2 up
2. Verify BGP neighbor IP is correct
3. Check firewall policy for BGP (TCP 179)
4. Verify AS numbers match configuration

### IPsec Phase2 Down
1. Check Phase1 status first
2. Verify Phase2 selectors match
3. Check for PSK mismatch
4. Review IPsec logs: `diagnose vpn ike log-filter dst-addr4 <peer_ip>`

## API Endpoints Used
- `/api/v2/monitor/virtual-wan/health-check` - Health check probe status
- `/api/v2/cmdb/system/sdwan/members` - SD-WAN member configuration
- `/api/v2/monitor/router/bgp/neighbors` - BGP neighbor status
- `/api/v2/monitor/vpn/ipsec` - IPsec tunnel status

## Related Tools
- `fortigate-sdwan-health-check` - Configure health checks
- `fortigate-sdwan-member` - Configure SD-WAN members
- `fortigate-sdwan-zone` - Configure SD-WAN zones
- `fortigate-sdwan-neighbor` - Configure BGP neighbor bindings
- `fortigate-vpn-ipsec-phase1` - Configure IPsec Phase1
- `fortigate-vpn-ipsec-phase2` - Configure IPsec Phase2

## References
- [FortiOS SD-WAN Diagnose Commands](https://docs.fortinet.com/document/fortigate/7.6.5/administration-guide/818746/sd-wan-related-diagnose-commands)
- [FortiOS Monitor API](https://fndn.fortinet.net/index.php?/fortiapi/1-fortios/)
