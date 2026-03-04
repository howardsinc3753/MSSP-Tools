# FortiGate SD-WAN API Reference

**For Tool Development**
**FortiOS Version:** 7.6.x

---

## Authentication

All API calls require Bearer token authentication:

```bash
curl -sk "https://{fortigate_ip}/api/v2/..." \
  -H "Authorization: Bearer {api_token}"
```

---

## SD-WAN Monitor APIs

### Get SD-WAN Health Check Status

```bash
GET /api/v2/monitor/system/sdwan/health-check

# Response
{
  "results": [
    {
      "name": "HUB",
      "members": [
        {
          "seq_num": 1,
          "interface": "H1_INET",
          "status": "alive",
          "latency": 12.5,
          "jitter": 2.3,
          "packet_loss": 0,
          "sla_targets_met": true
        }
      ]
    }
  ]
}
```

### Get SD-WAN Member Status

```bash
GET /api/v2/monitor/system/sdwan/members

# Response
{
  "results": [
    {
      "seq_num": 1,
      "interface": "H1_INET",
      "zone": "virtual-wan-link",
      "status": "up",
      "gateway": "10.10.10.1",
      "source_ip": "10.10.10.2"
    }
  ]
}
```

### Get SD-WAN Service/Rule Status

```bash
GET /api/v2/monitor/system/sdwan/service

# Response
{
  "results": [
    {
      "id": 1,
      "name": "DEFAULT",
      "mode": "sla",
      "state": "active",
      "member": 1
    }
  ]
}
```

---

## SD-WAN Configuration APIs

### Get SD-WAN Global Config

```bash
GET /api/v2/cmdb/system/sdwan

# Response
{
  "results": {
    "status": "enable",
    "load-balance-mode": "source-ip-based",
    "speedtest-bypass-routing": "disable"
  }
}
```

### Create SD-WAN Member

```bash
POST /api/v2/cmdb/system/sdwan/members

# Request Body
{
  "seq-num": 3,
  "interface": "H3_INET",
  "zone": "virtual-wan-link",
  "gateway": "0.0.0.0",
  "source": "0.0.0.0",
  "cost": 0,
  "weight": 1,
  "status": "enable"
}
```

### Create Health Check

```bash
POST /api/v2/cmdb/system/sdwan/health-check

# Request Body
{
  "name": "HUB_NEW",
  "server": ["10.200.99.1"],
  "protocol": "ping",
  "interval": 1000,
  "probe-timeout": 500,
  "failtime": 3,
  "recoverytime": 3,
  "members": [
    {"seq-num": 1},
    {"seq-num": 2}
  ],
  "sla": [
    {
      "id": 1,
      "latency-threshold": 100,
      "jitter-threshold": 50,
      "packetloss-threshold": 5
    }
  ]
}
```

### Create SD-WAN Rule/Service

```bash
POST /api/v2/cmdb/system/sdwan/service

# Request Body
{
  "id": 10,
  "name": "VOICE_TRAFFIC",
  "mode": "priority",
  "protocol": 17,
  "start-port": 5060,
  "end-port": 5061,
  "health-check": "HUB",
  "priority-members": [
    {"seq-num": 1},
    {"seq-num": 2}
  ]
}
```

### Delete SD-WAN Rule

```bash
DELETE /api/v2/cmdb/system/sdwan/service/{id}
```

---

## VPN IPsec APIs

### Get IPsec Tunnel Status

```bash
GET /api/v2/monitor/vpn/ipsec

# Response
{
  "results": [
    {
      "proxyid": [],
      "name": "H1_INET",
      "incoming_bytes": 123456,
      "outgoing_bytes": 654321,
      "rgwy": "203.0.113.1",
      "creation_time": 1234567890,
      "tun_id": "10.255.1.1"
    }
  ]
}
```

### Create Phase 1 Interface (Hub - Dynamic)

```bash
POST /api/v2/cmdb/vpn.ipsec/phase1-interface

# Hub Request Body
{
  "name": "H1_INET",
  "type": "dynamic",
  "interface": "wan1",
  "ike-version": "2",
  "peertype": "any",
  "proposal": "aes256gcm-prfsha256 aes256-sha256",
  "dpd": "on-idle",
  "dpd-retrycount": 2,
  "dpd-retryinterval": 5,
  "psksecret": "{psk}",
  "mode-cfg": "enable",
  "auto-discovery-sender": "enable",
  "exchange-ip-addr4": "{hub_loopback}",
  "add-route": "disable",
  "net-device": "disable"
}
```

### Create Phase 1 Interface (Spoke - Dial-up)

```bash
POST /api/v2/cmdb/vpn.ipsec/phase1-interface

# Spoke Request Body
{
  "name": "H1_INET",
  "interface": "wan1",
  "ike-version": "2",
  "peertype": "any",
  "proposal": "aes256gcm-prfsha256 aes256-sha256",
  "dpd": "on-idle",
  "dpd-retrycount": 3,
  "dpd-retryinterval": 5,
  "psksecret": "{psk}",
  "remote-gw": "{hub_wan_ip}",
  "auto-discovery-receiver": "enable",
  "exchange-ip-addr4": "{spoke_loopback}",
  "add-route": "disable",
  "net-device": "disable"
}
```

### Create Phase 2 Interface

```bash
POST /api/v2/cmdb/vpn.ipsec/phase2-interface

# Request Body
{
  "name": "H1_INET_P2",
  "phase1name": "H1_INET",
  "proposal": "aes256gcm",
  "keepalive": "enable",
  "keylifeseconds": 3600
}
```

### Delete IPsec Tunnel

```bash
DELETE /api/v2/cmdb/vpn.ipsec/phase1-interface/{name}
DELETE /api/v2/cmdb/vpn.ipsec/phase2-interface/{name}
```

---

## BGP APIs

### Get BGP Summary

```bash
GET /api/v2/monitor/router/bgp/neighbors

# Response
{
  "results": [
    {
      "neighbor_ip": "10.200.1.1",
      "remote_as": 65001,
      "state": "Established",
      "uptime": 86400,
      "prefixes_received": 15,
      "prefixes_sent": 5
    }
  ]
}
```

### Get BGP Paths

```bash
GET /api/v2/monitor/router/bgp/paths

# Filter by prefix
GET /api/v2/monitor/router/bgp/paths?prefix=10.0.0.0/8
```

### Configure BGP (Full Replace)

```bash
PUT /api/v2/cmdb/router/bgp

# Request Body
{
  "as": 65001,
  "router-id": "10.200.1.1",
  "keepalive-timer": 15,
  "holdtime-timer": 45,
  "ibgp-multipath": "enable",
  "ebgp-multipath": "enable",
  "recursive-next-hop": "enable",
  "graceful-restart": "enable"
}
```

### Add BGP Neighbor

```bash
POST /api/v2/cmdb/router/bgp/neighbor

# Request Body
{
  "ip": "10.200.1.2",
  "remote-as": 65001,
  "update-source": "Lo",
  "soft-reconfiguration": "enable",
  "next-hop-self": "enable"
}
```

### Add BGP Neighbor Group (for Hub RR)

```bash
POST /api/v2/cmdb/router/bgp/neighbor-group

# Request Body
{
  "name": "EDGE",
  "remote-as": 65001,
  "update-source": "Lo",
  "route-reflector-client": "enable",
  "soft-reconfiguration": "enable",
  "next-hop-self": "enable"
}
```

### Add BGP Neighbor Range (Dynamic Peering)

```bash
POST /api/v2/cmdb/router/bgp/neighbor-range

# Request Body
{
  "id": 1,
  "prefix": "10.200.0.0/16",
  "neighbor-group": "EDGE"
}
```

### Add BGP Network

```bash
POST /api/v2/cmdb/router/bgp/network

# Request Body
{
  "id": 1,
  "prefix": "10.200.0.0/14",
  "route-map": "LOCAL_REGION"
}
```

---

## Interface APIs

### Create Loopback Interface

```bash
POST /api/v2/cmdb/system/interface

# Request Body
{
  "name": "Lo",
  "vdom": "root",
  "type": "loopback",
  "ip": "10.200.1.1 255.255.255.255",
  "allowaccess": "ping"
}
```

### Create Tunnel Interface (for overlay)

```bash
POST /api/v2/cmdb/system/interface

# Request Body - Created automatically by phase1
# But can override:
{
  "name": "H1_INET",
  "vdom": "root",
  "type": "tunnel",
  "remote-ip": "0.0.0.0 0.0.0.0",
  "interface": "wan1"
}
```

---

## Route Map APIs

### Create Route Map

```bash
POST /api/v2/cmdb/router/route-map

# Request Body
{
  "name": "LAN_TAG",
  "rule": [
    {
      "id": 1,
      "action": "permit",
      "set-tag": 100
    }
  ]
}
```

### Create Route Map with Community

```bash
POST /api/v2/cmdb/router/route-map

# Request Body
{
  "name": "LOCAL_REGION",
  "rule": [
    {
      "id": 1,
      "action": "permit",
      "set-community": "no-export",
      "set-tag": 100
    }
  ]
}
```

---

## Zone APIs

### Create SD-WAN Zone

```bash
POST /api/v2/cmdb/system/sdwan/zone

# Request Body
{
  "name": "HUB_ZONE",
  "service-sla-tie-break": "cfg-order"
}
```

### Create System Zone

```bash
POST /api/v2/cmdb/system/zone

# Request Body
{
  "name": "WAN",
  "interface": [
    {"interface-name": "wan1"},
    {"interface-name": "wan2"}
  ]
}
```

---

## Error Codes

| HTTP Code | Meaning |
|-----------|---------|
| 200 | Success |
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid/expired token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 424 | Failed Dependency - Related object missing |
| 500 | Internal Error |

---

## Python Helper Template

```python
import httpx
from typing import Dict, Any, Optional

class FortiGateSDWAN:
    def __init__(self, host: str, token: str, verify_ssl: bool = False):
        self.base_url = f"https://{host}/api/v2"
        self.headers = {"Authorization": f"Bearer {token}"}
        self.verify = verify_ssl

    async def get_sdwan_health(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(verify=self.verify) as client:
            r = await client.get(
                f"{self.base_url}/monitor/system/sdwan/health-check",
                headers=self.headers
            )
            return r.json()

    async def create_ipsec_phase1(self, config: Dict) -> Dict[str, Any]:
        async with httpx.AsyncClient(verify=self.verify) as client:
            r = await client.post(
                f"{self.base_url}/cmdb/vpn.ipsec/phase1-interface",
                headers=self.headers,
                json=config
            )
            return r.json()

    async def create_bgp_neighbor(self, neighbor: Dict) -> Dict[str, Any]:
        async with httpx.AsyncClient(verify=self.verify) as client:
            r = await client.post(
                f"{self.base_url}/cmdb/router/bgp/neighbor",
                headers=self.headers,
                json=neighbor
            )
            return r.json()
```
