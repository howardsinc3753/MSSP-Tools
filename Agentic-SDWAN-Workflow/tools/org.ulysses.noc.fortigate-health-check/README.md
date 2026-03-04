# FortiGate Health Check Tool

**Canonical ID:** `org.ulysses.noc.fortigate-health-check/1.0.0`
**Version:** 1.0.0
**Shelf:** noc/fortigate
**Status:** Draft

## Overview

This tool retrieves health metrics from a FortiGate firewall device via REST API. It returns CPU utilization, memory usage, session count, uptime, and firmware version.

## Files

| File | Purpose |
|------|---------|
| `manifest.yaml` | Tool manifest with metadata, parameters, capabilities |
| `tool.py` | Python implementation |
| `requirements.txt` | Python dependencies |
| `Skills.md` | AI agent guidance for using this tool |
| `README.md` | This file |

## Usage

### Parameters

```json
{
  "target_ip": "192.168.1.1",
  "timeout": 30,
  "verify_ssl": false
}
```

### Output

```json
{
  "success": true,
  "target_ip": "192.168.1.1",
  "cpu_percent": 42.5,
  "memory_percent": 60.2,
  "session_count": 1000,
  "uptime_seconds": 864000,
  "firmware_version": "7.4.1",
  "hostname": "FW-192-168-1-1",
  "serial_number": "FG100F0000000001"
}
```

## Credentials

Requires FortiGate API key with read access:
- Vault reference: `vault://fortigate/admin`
- Type: API key
- Scope: read

## Registration

To register this tool in the MCP Trust Anchor:

```bash
cd ~/projects/ulysses-mcp-master
source .venv/bin/activate
python scripts/load_sample_tool.py
```

## Development Notes

Current implementation is a stub that returns mock data. Production version would:
1. Retrieve API key from credential vault
2. Call FortiGate REST API endpoints
3. Parse and return actual metrics

## Related Tools

- FortiGate Interface Status
- FortiGate Routing Table
- FortiGate Session List
- FortiGate Backup
