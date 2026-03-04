# FortiGate BGP Troubleshoot - Skills Guide

## Tool Identity
- **Canonical ID:** `org.ulysses.noc.fortigate-bgp-troubleshoot/1.0.0`
- **Domain:** noc
- **Intent:** troubleshoot
- **Vendor:** fortinet

## When to Use This Tool

### Primary Use Cases
1. **SD-WAN BGP health check** - Verify BGP sessions are established
2. **Route troubleshooting** - Check if prefixes are being received/advertised
3. **Neighbor diagnostics** - Investigate BGP session issues
4. **Pre/post change validation** - Verify BGP state before/after changes
5. **FMG/overlay failover testing** - Confirm route advertisement for failover paths

### Common Scenarios
- "Is BGP up with my neighbors?"
- "What routes am I receiving from the spoke?"
- "What routes am I advertising to the hub?"
- "Why isn't my prefix being advertised?"
- "Generate a full BGP troubleshooting report"

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| target_ip | Yes | - | FortiGate management IP |
| action | No | summary | Diagnostic action (see below) |
| neighbor_ip | Conditional | - | Required for received/advertised actions |
| verify_ssl | No | false | Verify SSL certificates |

### Actions

| Action | Description | Requires neighbor_ip |
|--------|-------------|---------------------|
| summary | BGP overview with neighbor states | No |
| neighbors | Detailed neighbor capabilities | No |
| paths | Full BGP RIB | No |
| received | Routes received from neighbor | Yes |
| advertised | Routes advertised to neighbor | Yes |
| report | Comprehensive troubleshooting report | No |

## Example Usage

### Quick BGP Summary
```json
{
  "target_ip": "10.0.1.1",
  "action": "summary"
}
```
**Output:**
```json
{
  "success": true,
  "action": "summary",
  "target_ip": "10.0.1.1",
  "router_id": "172.16.255.253",
  "local_as": "65000",
  "neighbor_count": 1,
  "neighbors": [
    {
      "ip": "172.16.0.2",
      "remote_as": "65000",
      "state": "Established",
      "up_time": "11:35:43",
      "prefixes_received": 2
    }
  ]
}
```

### Check Routes Received from Spoke
```json
{
  "target_ip": "10.0.1.1",
  "action": "received",
  "neighbor_ip": "172.16.0.2"
}
```
**Output:**
```json
{
  "success": true,
  "action": "received",
  "neighbor": "172.16.0.2",
  "routes": [
    {
      "network": "10.199.199.1/32",
      "next_hop": "172.16.0.2",
      "local_pref": 100,
      "origin": "i"
    },
    {
      "network": "10.0.0.0/24",
      "next_hop": "172.16.0.2",
      "local_pref": 100,
      "origin": "i"
    }
  ],
  "count": 2
}
```

### Check Routes Advertised to Spoke
```json
{
  "target_ip": "10.0.1.1",
  "action": "advertised",
  "neighbor_ip": "172.16.0.2"
}
```

### Full Troubleshooting Report
```json
{
  "target_ip": "10.0.1.1",
  "action": "report"
}
```
Returns comprehensive data including summary, all neighbors with their received/advertised routes.

### View BGP RIB (All Paths)
```json
{
  "target_ip": "10.0.1.1",
  "action": "paths"
}
```

## CLI Equivalents

| Tool Action | FortiOS CLI Command |
|-------------|---------------------|
| summary | `get router info bgp summary` |
| neighbors | `get router info bgp neighbors` |
| paths | `get router info bgp network` |
| received | `get router info bgp neighbors <ip> received-routes` |
| advertised | `get router info bgp neighbors <ip> advertised-routes` |

## Troubleshooting Workflows

### 1. BGP Session Not Established
```json
{"target_ip": "10.0.1.1", "action": "summary"}
```
Check:
- Is neighbor listed?
- What is the state? (Idle, Active, Connect, OpenSent, OpenConfirm, Established)
- Are there any prefixes received?

### 2. Missing Route Advertisement
1. Check if route is in BGP network statements:
   - Use `fortigate-bgp-network-advertise` with action `list`
2. Check if route exists in RIB (BGP requires route in RIB to advertise)
3. Check received routes on peer to see if it arrived

### 3. SD-WAN Failover Verification
1. Get BGP summary on Hub
2. Check received routes from Spoke overlay IP
3. Verify WAN subnet is being advertised
4. Test connectivity to Spoke via WAN path

## Related Tools
- `fortigate-bgp-network-advertise` - Add/remove BGP network statements
- `fortigate-sdwan-health-check` - SD-WAN health check status
- `fortigate-sdwan-neighbor` - SD-WAN BGP neighbor config
- `fortigate-health-check` - Device connectivity test

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| "No credentials found" | Missing API token | Check fortigate_credentials.yaml |
| "Failed to get BGP summary" | API error or BGP not configured | Verify BGP is enabled |
| "neighbor_ip is required" | Missing parameter | Specify neighbor_ip for received/advertised |
| "401 Unauthorized" | Invalid/expired token | Regenerate API token on FortiGate |

## Output Interpretation

### Neighbor States
| State | Meaning |
|-------|---------|
| Idle | Not attempting connection |
| Connect | TCP connection in progress |
| Active | Trying to connect |
| OpenSent | Open message sent, waiting for reply |
| OpenConfirm | Received Open, waiting for Keepalive |
| Established | BGP session up and exchanging routes |

### Origin Codes
| Code | Meaning |
|------|---------|
| i | IGP - learned via network statement |
| e | EGP - learned via EGP (rare) |
| ? | Incomplete - redistributed route |
