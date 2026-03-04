# FortiGate License Apply Skills

## Overview

Apply a FortiFlex license token to a FortiGate VM via SSH. This tool handles the complete license application workflow including waiting for the mandatory reboot.

## When to Use

Use this tool when:
- A newly provisioned FortiGate VM needs licensing
- Applying a FortiFlex token from `fortiflex-token-create`
- Re-licensing a FortiGate VM with a new token
- Part of the SD-WAN spoke deployment workflow (after BLOCK_1 provision)

**Example prompts:**
- "Apply the FortiFlex license to the new FortiGate at 10.0.0.45"
- "License the spoke with token FF439657EDD7113AA4D9"
- "Apply license to Site 7"

## Prerequisites

1. **FortiGate VM** - Provisioned and accessible via SSH
2. **FortiFlex Token** - Valid 20-character hex token from FortiFlex
3. **Network Access** - FortiGate must reach forticare.fortinet.com for validation
4. **Admin Credentials** - SSH access with admin password

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `target_ip` | string | **Yes** | - | FortiGate management IP |
| `fortiflex_token` | string | **Yes** | - | 20-char FortiFlex token |
| `admin_password` | string | No | `FG@dm!n2026!` | Admin password |
| `admin_user` | string | No | `admin` | Admin username |
| `wait_for_reboot` | boolean | No | true | Wait for reboot completion |
| `reboot_timeout` | integer | No | 180 | Reboot wait timeout (seconds) |

## Example Usage

### Basic License Apply

```python
execute_certified_tool(
    canonical_id="org.ulysses.provisioning.fortigate-license-apply/1.0.0",
    parameters={
        "target_ip": "10.0.0.45",
        "fortiflex_token": "FF439657EDD7113AA4D9"
    }
)
```

### With Custom Password

```python
execute_certified_tool(
    canonical_id="org.ulysses.provisioning.fortigate-license-apply/1.0.0",
    parameters={
        "target_ip": "10.0.0.45",
        "fortiflex_token": "FF439657EDD7113AA4D9",
        "admin_password": "MyCustomPassword123!"
    }
)
```

### Skip Reboot Wait (fire and forget)

```python
execute_certified_tool(
    canonical_id="org.ulysses.provisioning.fortigate-license-apply/1.0.0",
    parameters={
        "target_ip": "10.0.0.45",
        "fortiflex_token": "FF439657EDD7113AA4D9",
        "wait_for_reboot": false
    }
)
```

## Interpreting Results

### Success Response

```json
{
  "success": true,
  "license_status": "Valid",
  "serial_number": "FGVMMLTMXXXXXXXXX",
  "license_output": "Your license has been activated...",
  "rebooted": true
}
```

### Field Meanings

| Field | Description |
|-------|-------------|
| `license_status` | Current license state (Valid, Invalid, Expired) |
| `serial_number` | FortiGate serial number |
| `license_output` | Raw output from license install command |
| `rebooted` | Whether device rebooted during process |

## Workflow Integration

### Full SD-WAN Spoke Deployment

```
1. kvm-fortios-provision      -> Create VM, get IP
2. fortigate-license-apply    -> Apply FortiFlex license (THIS TOOL)
3. fortigate-api-token-create -> Create API admin
4. fortigate-sdwan-spoke-template -> Push SD-WAN config
```

### Token Creation + Apply

```python
# Step 1: Create token
token_result = execute_certified_tool(
    canonical_id="org.ulysses.cloud.fortiflex-token-create/1.0.3",
    parameters={"config_id": 54380}
)
token = token_result["result"]["tokens"][0]["token"]

# Step 2: Apply license
execute_certified_tool(
    canonical_id="org.ulysses.provisioning.fortigate-license-apply/1.0.0",
    parameters={
        "target_ip": "10.0.0.45",
        "fortiflex_token": token
    }
)
```

## Error Handling

| Error | Meaning | Suggestion |
|-------|---------|------------|
| `SSH authentication failed` | Wrong password | Verify admin_password |
| `Invalid token format` | Token not 20-char hex | Check token from FortiFlex |
| `curl forticare failed` | No internet from FortiGate | Check WAN/DNS config |
| `Connection timeout` | FortiGate unreachable | Verify IP and network |
| `Timeout waiting for reboot` | Reboot took too long | Increase reboot_timeout |

## Network Requirements

The FortiGate must be able to reach Fortinet servers:
- `forticare.fortinet.com` - License validation
- `update.fortinet.com` - Updates (optional)

If the FortiGate cannot reach these servers, the license will fail with:
```
curl forticare failed, 6
```

**Fix**: Configure DNS and verify WAN gateway:
```
config system dns
    set primary 8.8.8.8
end
```

## Related Tools

- `fortiflex-token-create` - Create FortiFlex tokens
- `fortiflex-config-list` - List FortiFlex configurations
- `kvm-fortios-provision` - Provision FortiGate VMs
- `fortigate-api-token-create` - Create API admin after licensing

## Security Notes

- This tool uses password authentication (required for new VMs)
- Password is passed securely via paramiko (not shell expansion)
- Consider rotating the default password after deployment
- Token format is validated before submission
