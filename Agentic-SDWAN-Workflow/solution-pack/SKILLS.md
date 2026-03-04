# FortiGate Operations - AI Skills Guide

**Pack ID:** `org.ulysses.solution.fortigate-ops/1.0.0`
**Domain:** NOC / Security / Provisioning / Response
**Vendor:** Fortinet

---

## Purpose

This Skills.md provides AI agents with the knowledge needed to:
1. Route FortiGate-related requests to the correct tools
2. Extract parameters from natural language (device IP, action type)
3. Execute monitoring, security, provisioning, and response operations
4. Understand FortiGate API capabilities and limitations

---

## Quick Reference - Available Tools

| Tool | Domain | What It Does |
|------|--------|--------------|
| `fortigate-health-check` | NOC | CPU, memory, sessions, firmware |
| `fortigate-interface-status` | NOC | Interface up/down, counters |
| `fortigate-routing-table` | NOC | IPv4/IPv6 routes |
| `fortigate-session-table` | NOC | Active sessions |
| `fortigate-arp-table` | NOC | ARP cache |
| `fortigate-performance-status` | NOC | Detailed metrics |
| `fortigate-running-processes` | NOC | System processes |
| `fortigate-network-analyzer` | NOC | Traffic analysis |
| `fortigate-ssh` | NOC | SSH command exec |

---

## Device Registry

### Lab Devices

| Device ID | Model | IP | Role |
|-----------|-------|-----|------|
| `lab-71f` | FortiGate 71F | 192.168.209.62 | Lab Primary |
| `fw-50g` | FortiGate 50G | 192.168.209.30 | Lab Secondary |

### Credential Lookup

Credentials stored in: `config/fortigate_credentials.yaml`

When user says "the 71F" or "lab firewall" → use `192.168.209.62`
When user says "the 50G" or "backup firewall" → use `192.168.209.30`

---

## Intent Detection Patterns

### NOC Health Check

**Keywords:** health, status, check, cpu, memory, uptime, firmware, version
**Entities:** fortigate, firewall, device IP

**Example intents:**
- "Check the health of the 71F"
- "Is the FortiGate healthy?"
- "What's the CPU usage on 192.168.209.62?"
- "FortiGate status"

**Tool:** `org.ulysses.noc.fortigate-health-check/1.0.0`

**Parameter extraction:**
```yaml
target_ip:
  - Direct IP: "192.168.209.62" → use as-is
  - Device alias: "71F" → lookup 192.168.209.62
  - Default: use 192.168.209.62 (lab-71f)
```

---

### Interface Monitoring

**Keywords:** interface, port, link, up, down, traffic, counters
**Entities:** wan1, wan2, lan, port1-port10, dmz

**Example intents:**
- "Show interface status on the firewall"
- "Is wan1 up on the 71F?"
- "Interface counters"

**Tool:** `org.ulysses.noc.fortigate-interface-status/1.0.0`

---

### Routing Information

**Keywords:** route, routing, gateway, nexthop, static, bgp, ospf
**Entities:** subnet, destination, next-hop IP

**Example intents:**
- "Show routing table"
- "What's the default gateway?"
- "Routes to 10.0.0.0/8"

**Tool:** `org.ulysses.noc.fortigate-routing-table/1.0.0`

---

### Session Analysis

**Keywords:** session, connection, active, traffic, flow
**Entities:** source IP, destination IP, protocol, port

**Example intents:**
- "How many active sessions?"
- "Show sessions from 192.168.1.100"
- "Session count"

**Tool:** `org.ulysses.noc.fortigate-session-table/1.0.0`

---

### ARP Cache

**Keywords:** arp, mac, mac address, layer 2, neighbor
**Entities:** IP address, MAC address, interface

**Example intents:**
- "Show ARP table"
- "What's the MAC for 192.168.1.1?"
- "ARP cache on the firewall"

**Tool:** `org.ulysses.noc.fortigate-arp-table/1.0.0`

---

## Future Capabilities (Planned)

### SOC Security (v1.1.0)
- Threat log queries
- Policy analysis
- VPN monitoring
- IPS signature status

### Provisioning (v1.2.0)
- Device onboarding
- FortiFlex license provisioning
- SDWAN Hub configuration
- Config backup/restore
- Policy push

### Response (v1.3.0)
- IP blocking
- Host quarantine
- Session termination
- Debug capture

---

## Parameter Defaults

| Parameter | Default | Notes |
|-----------|---------|-------|
| `target_ip` | 192.168.209.62 | Lab 71F |
| `timeout` | 30 | Seconds |
| `verify_ssl` | false | Lab certs self-signed |

---

## Error Handling

| Error | Likely Cause | Resolution |
|-------|--------------|------------|
| "Connection refused" | Device unreachable | Check network, verify IP |
| "401 Unauthorized" | Invalid API token | Verify credentials in config |
| "403 Forbidden" | Insufficient permissions | Check API user permissions |
| "Timeout" | Device slow/overloaded | Increase timeout, check device health |
| "SSL certificate verify failed" | Self-signed cert | Set verify_ssl: false |

---

## Runbook Reference

### fortigate-triage

**Purpose:** Sequential health check and diagnostics
**Steps:**
1. Health check
2. Interface status
3. Routing table
4. Session summary

**When to use:**
- Regular health monitoring
- Troubleshooting connectivity issues
- Before/after maintenance

---

## Confidence Scoring

| Confidence | Action |
|------------|--------|
| >= 0.90 | Execute autonomously, no confirmation needed |
| 0.75 - 0.89 | Execute with brief confirmation |
| 0.50 - 0.74 | Clarify device or action before executing |
| < 0.50 | Ask user for specific device and action |

### High Confidence Triggers
- Explicit device IP provided
- Clear action verb (check, show, list)
- Single unambiguous tool match

### Low Confidence Triggers
- Multiple devices could match
- Ambiguous action requested
- Missing required parameters

---

## API Quick Reference

**Base URL Pattern:** `https://{device_ip}/api/v2/`

| Operation | Method | Endpoint |
|-----------|--------|----------|
| System status | GET | `/monitor/system/status` |
| Interfaces | GET | `/monitor/system/interface` |
| Routes | GET | `/monitor/router/ipv4` |
| Sessions | GET | `/monitor/firewall/session` |
| ARP | GET | `/monitor/network/arp` |
| Performance | GET | `/monitor/system/resource/usage` |

**Authentication:** Bearer token in header
```
Authorization: Bearer {api_token}
```

---

---

## Invocable Skills (Slash Commands)

### `/add-sdwan-site` - SD-WAN Site Provisioning Workflow

**Canonical ID:** `fortigate-sdwan`
**Path:** `solution_packs/fortigate-ops/workflows/add-sdwan-site/Skills.md`

**Purpose:** Provisions a new SD-WAN spoke site with complete ADVPN configuration.

**IMPORTANT:** This skill forces reading of prerequisites before allowing tool execution.

When invoked, the skill will:
1. **Force-read** `Skills.md` (workflow guide)
2. **Force-read** `BASELINE_TEMPLATE.yaml` (naming constants)
3. **Force-read** `BLOCK_0_BLUEPRINT_WIZARD.yaml` (parameters)
4. **Force-call** `list_certified_tools()` to verify versions
5. **Force-call** `list_accessible_devices()` to verify credentials
6. **Require** `process_log` output before tool execution

**Example invocation:**
```
/add-sdwan-site
```

**Minimum Tool Versions Required:**
| Tool | Version | Reason |
|------|---------|--------|
| kvm-fortios-provision | 1.0.11+ | rest-api-key-url-query enable + admintimeout 480 |
| fortigate-sdwan-spoke-template | 1.3.0+ | ADVPN zone+neighbor config |

**Pre-Flight Checklist (Agent Must Confirm):**
| Setting | Expected Value |
|---------|----------------|
| Loopback name | `Spoke-Lo` |
| Tunnel names | `HUB1-VPN1`, `HUB1-VPN2` |
| SD-WAN zone | `SDWAN_OVERLAY` |
| Health check | `HUB_Health` |
| ike-tcp-port | `11443` |
| transport | `udp` |

**Governance:**
- Sensitive parameters (`admin_password`, `psk`) require `AskUserQuestion` confirmation
- Tool calls logged to trace file for audit
- Hook validation blocks tool execution without prerequisites

---

### `/sdwan-developer` - Solution Pack Developer Mode

**Canonical ID:** `sdwan-developer`
**Path:** `solution_packs/fortigate-ops/developer-skill.md`

**Purpose:** Onboards AI agents who need to BUILD, EXTEND, or MAINTAIN the solution pack.

**Use this skill when:**
- Adding new features to spoke template (ADVPN, VXLAN, etc.)
- Adding new deployment paths (AWS, Azure, hardware)
- Modifying workflow blocks
- Fixing bugs in tools
- Understanding the architecture

**IMPORTANT:** This skill is for DEVELOPMENT, not deployment. Use `/add-sdwan-site` to deploy sites.

When invoked, the skill will:
1. **Force-read** `DEVELOPER_ONBOARDING.md` (architecture guide)
2. **Force-read** `BASELINE_TEMPLATE.yaml` (naming contract)
3. **Force-read** `fortigate-sdwan-spoke-template.py` (current code)
4. **Force-read** `Skills.md` (workflow documentation)
5. **Require** `developer_process_log` before making changes

**Example invocation:**
```
/sdwan-developer
```

**Key Files the Developer Must Understand:**

| File | Purpose |
|------|---------|
| `BASELINE_TEMPLATE.yaml` | THE CONTRACT - naming conventions |
| `DEVELOPER_ONBOARDING.md` | Architecture and how-to guides |
| `fortigate-sdwan-spoke-template.py` | Main configuration generator |
| `BLOCK_*.yaml` | Workflow phase definitions |

**Development Tasks Supported:**
- Add new configuration sections to spoke template
- Add new deployment platforms (AWS, Azure)
- Modify workflow steps
- Fix bugs and improve reliability
- Extend contract validation

---

## Related Solution Packs

| Pack | Relationship |
|------|--------------|
| `fortinet-ecosystem` | Parent (planned) |
| `fortimanager-central` | Sibling - centralized management |
| `fortianalyzer-intel` | Sibling - logging and analytics |
| `fortiflex-licensing` | Sibling - license management |
