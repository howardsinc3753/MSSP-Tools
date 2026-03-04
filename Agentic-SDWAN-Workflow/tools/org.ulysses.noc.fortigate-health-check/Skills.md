# FortiGate Health Check Skills

## How to Call

Use this tool when:
- User asks about FortiGate device health
- User wants to check firewall performance
- User mentions CPU, memory, or session count on FortiGate
- Troubleshooting FortiGate connectivity or performance issues

**Example prompts:**
- "Is my FortiGate healthy?"
- "Check CPU on firewall 192.168.1.1"
- "How many sessions are on the FortiGate?"
- "What firmware is running on 10.0.0.1?"

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `target_ip` | string | Yes | FortiGate management IP address |
| `timeout` | integer | No | Request timeout in seconds (default: 30) |
| `verify_ssl` | boolean | No | Verify SSL certificate (default: false) |

## Interpreting Results

### CPU Percent
- `< 50%`: Normal operation
- `50-80%`: Moderate load, monitor trend
- `> 80%`: High load, investigate traffic patterns

### Memory Percent
- `< 70%`: Normal operation
- `70-90%`: Memory pressure, check session table
- `> 90%`: Critical, consider clearing sessions or upgrade

### Session Count
- Compare against device model limits
- FG-100F: ~1.5M sessions max
- High session count + high memory = potential issue

### Uptime
- Recent reboot may indicate crash or maintenance
- Very long uptime (>1 year) may indicate missed patches

### Firmware Version
- Check against FortiGuard recommended version
- EOL versions should be flagged for upgrade

## Good Use Cases

- "Is my FortiGate healthy?"
- "Check CPU on firewall 192.168.1.1"
- "Get health status of 10.0.0.1"
- "What's the memory usage on the firewall?"
- "How long has the FortiGate been up?"

## Bad Use Cases

- Don't use for configuration changes (use different tool)
- Don't use for traffic analysis (use FortiAnalyzer)
- Don't use for log retrieval (use log tools)
- Don't use for backup/restore operations

## Example

**User:** Check health of FortiGate at 10.0.0.1

**Tool Call:**
```python
fortigate_health_check(target_ip="10.0.0.1")
```

**Response:**
```json
{
  "success": true,
  "cpu_percent": 42.5,
  "memory_percent": 60.2,
  "session_count": 1000,
  "uptime_seconds": 864000,
  "firmware_version": "7.4.1",
  "hostname": "FW-10-0-0-1",
  "serial_number": "FG100F0000000001"
}
```

**Interpretation:**
"The FortiGate at 10.0.0.1 is healthy. CPU is at 42.5% (normal), memory at 60.2% (normal), with 1000 active sessions. The device has been up for 10 days running FortiOS 7.4.1."

## Error Handling

| Error | Meaning | Suggestion |
|-------|---------|------------|
| `target_ip is required` | Missing IP | Ask user for FortiGate IP |
| `Connection timeout` | Network issue | Check network connectivity |
| `401 Unauthorized` | Bad API key | Verify credentials in vault |
| `SSL certificate error` | Cert issue | Try with verify_ssl=false |

## Related Tools

- `fortigate-interface-status` - Check interface status
- `fortigate-routing-table` - View routing table
- `fortigate-session-list` - List active sessions
- `fortigate-backup` - Backup configuration
