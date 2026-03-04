# FortiGate Operations - Train Your Human Guide

**Solution Pack:** `org.ulysses.solution.fortigate-ops/1.0.0`
**Version:** 1.0.0
**Last Updated:** 2025-01-14

---

## What This Pack Does

FortiGate Operations provides a unified interface for managing Fortinet FortiGate firewalls through the Project Ulysses platform. It wraps FortiGate REST API calls into certified, auditable tools that can be executed by humans or AI agents.

**Current Capabilities:**
- NOC monitoring (health, interfaces, routing, sessions)
- Device credential management
- Sequential triage runbook

**Coming Soon:**
- SOC security monitoring
- Device provisioning and onboarding
- Incident response tools
- Intelligent (agentic) workflows

---

## Quick Start

### Prerequisites

1. FortiGate device(s) with REST API enabled
2. API token generated for REST API admin
3. Trust Anchor running on port 8000
4. Network connectivity to FortiGate management interface

### Verify Setup

```bash
# Check Trust Anchor is running
curl http://192.168.209.115:8000/health

# Check FortiGate tool is registered
curl http://192.168.209.115:8000/tools | grep fortigate-health-check
```

### First Health Check

```bash
curl -X POST http://192.168.209.115:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_id": "org.ulysses.noc.fortigate-health-check/1.0.0",
    "parameters": {
      "target_ip": "192.168.209.62"
    }
  }'
```

---

## Adding New Devices

### Step 1: Generate API Token on FortiGate

1. Log into FortiGate GUI
2. Navigate to **System → Administrators**
3. Click **Create New → REST API Admin**
4. Configure:
   - Username: `ulysses-api`
   - Administrator Profile: `prof_admin` (or custom read-only)
   - PKI Group: Leave empty
   - Trusted Hosts: Add Trust Anchor IP
5. Click **OK** and copy the generated API key

### Step 2: Add to Credentials File

Edit `config/fortigate_credentials.yaml`:

```yaml
devices:
  # Existing devices...

  new-device-name:
    host: "192.168.x.x"
    api_token: "YOUR_API_TOKEN_HERE"
    verify_ssl: false

default_lookup:
  # Existing mappings...
  "192.168.x.x": "new-device-name"
```

### Step 3: Test Connectivity

```bash
curl -X POST http://192.168.209.115:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_id": "org.ulysses.noc.fortigate-health-check/1.0.0",
    "parameters": {
      "target_ip": "192.168.x.x"
    }
  }'
```

---

## Common Operations

### Health Check

Check device health metrics:

```bash
curl -X POST http://192.168.209.115:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_id": "org.ulysses.noc.fortigate-health-check/1.0.0",
    "parameters": {"target_ip": "192.168.209.62"}
  }'
```

**Output includes:** hostname, serial, firmware, CPU%, memory%, session count

### Interface Status

List all interfaces and their status:

```bash
curl -X POST http://192.168.209.115:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_id": "org.ulysses.noc.fortigate-interface-status/1.0.0",
    "parameters": {"target_ip": "192.168.209.62"}
  }'
```

### Routing Table

View routing entries:

```bash
curl -X POST http://192.168.209.115:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_id": "org.ulysses.noc.fortigate-routing-table/1.0.0",
    "parameters": {"target_ip": "192.168.209.62"}
  }'
```

### Full Triage Runbook

Execute sequential diagnostics:

```bash
curl -X POST http://192.168.209.115:8000/runbooks/execute \
  -H "Content-Type: application/json" \
  -d '{
    "runbook_id": "org.ulysses.sop.fortigate-triage/1.0.0",
    "device": "192.168.209.62"
  }'
```

---

## Lab Devices

| Device ID | Model | IP | API Token Status |
|-----------|-------|-----|------------------|
| lab-71f | FortiGate 71F | 192.168.209.62 | Configured |
| fw-50g | FortiGate 50G | 192.168.209.30 | Configured |

---

## Troubleshooting

### Connection Refused

**Cause:** Cannot reach FortiGate management IP

**Fix:**
1. Verify IP address is correct
2. Check network connectivity: `ping 192.168.x.x`
3. Verify HTTPS admin access is enabled on FortiGate
4. Check trusted hosts in FortiGate admin settings

### 401 Unauthorized

**Cause:** Invalid or expired API token

**Fix:**
1. Generate new API token on FortiGate
2. Update `config/fortigate_credentials.yaml`
3. Restart any cached connections

### 403 Forbidden

**Cause:** API admin lacks permissions

**Fix:**
1. Check administrator profile on FortiGate
2. Ensure profile has read access to required APIs
3. For monitoring, `read` permission is sufficient

### SSL Certificate Error

**Cause:** Self-signed certificate

**Fix:**
Set `verify_ssl: false` in credentials or parameters

### Timeout

**Cause:** Device slow to respond

**Fix:**
1. Increase timeout parameter: `"timeout": 60`
2. Check device CPU/memory - may be overloaded
3. Verify no firewall blocking between Trust Anchor and FortiGate

---

## File Locations

| File | Purpose |
|------|---------|
| `solution-pack.yaml` | Pack manifest and configuration |
| `SKILLS.md` | AI routing guide |
| `docs/pilot-guide.html` | Browser-viewable guide |
| `docs/train-your-human.md` | This file |
| `config/fortigate_credentials.yaml` | Device credentials (DO NOT COMMIT) |
| `tests/qa_fortigate_ops_tests.py` | QA test suite |

---

## API Reference

### FortiGate REST API Endpoints Used

| Endpoint | Method | Tool |
|----------|--------|------|
| `/api/v2/monitor/system/status` | GET | health-check |
| `/api/v2/monitor/system/interface` | GET | interface-status |
| `/api/v2/monitor/router/ipv4` | GET | routing-table |
| `/api/v2/monitor/firewall/session` | GET | session-table |
| `/api/v2/monitor/network/arp` | GET | arp-table |
| `/api/v2/monitor/system/resource/usage` | GET | performance-status |

### Authentication

All tools use Bearer token authentication:
```
Authorization: Bearer {api_token}
```

---

## Support

- **SKILLS.md** - AI agent routing information
- **pilot-guide.html** - Comprehensive browser guide
- **solution-pack.yaml** - Full manifest
- **Trust Anchor Health** - `GET /health`

---

## Roadmap

- **v1.1.0** - SOC security tools (threat logs, policies)
- **v1.2.0** - Provisioning (onboarding, FortiFlex, SDWAN)
- **v1.3.0** - Response tools and agentic workflows
