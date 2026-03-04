# FortiGate Onboard - Skills Guide

## Tool Identity
- **Canonical ID:** `org.ulysses.noc.fortigate-onboard/1.0.1`
- **Domain:** noc
- **Intent:** configure
- **Vendor:** fortinet

## When to Use This Tool

### Primary Use Case
New FortiGate device setup when you have:
- Admin SSH access (admin/password)
- Network connectivity to the device
- Need to establish API automation access

### Trigger Phrases
- "onboard new fortigate"
- "set up fortigate for automation"
- "provision fortigate api access"
- "add new fortigate device"
- "configure fortigate api token"

## Workflow Steps

```
1. SSH Connect        → Establish SSH session with admin credentials
2. Enable API Settings → Set rest-api-key-url-query enable (fixes 401 errors)
3. Create API User    → Create REST API admin via CLI
4. Generate Key       → Execute api-user generate-key command
5. Test API           → Verify Bearer token authentication works
6. Register Device    → Store credentials in local config file
```

## Required Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| target_ip | string | FortiGate management IP |
| admin_password | string | Admin password (sensitive) |
| device_id | string | Unique identifier (e.g., "lab-vm02") |

## Optional Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| admin_user | "admin" | SSH username |
| api_username | "ulysses-api" | Name for API admin |
| accprofile | "super_admin" | Admin profile |
| trusthosts | auto | Allowed source networks |
| ssh_port | 22 | SSH port |
| timeout | 60 | Operation timeout |
| verify_ssl | false | Verify SSL certs |

## Example Usage

### Basic Onboarding
```json
{
  "target_ip": "10.0.1.1",
  "admin_password": "your-password",
  "device_id": "lab-vm02"
}
```

### Custom Configuration
```json
{
  "target_ip": "10.0.1.1",
  "admin_password": "your-password",
  "device_id": "branch-fw01",
  "api_username": "automation-api",
  "accprofile": "prof_admin",
  "trusthosts": [
    ["192.168.1.0", "255.255.255.0"],
    ["10.0.0.0", "255.0.0.0"]
  ]
}
```

## Output

### Success Response
```json
{
  "success": true,
  "target_ip": "10.0.1.1",
  "device_id": "lab-vm02",
  "api_token": "abc123xyz...",
  "device_info": {
    "hostname": "FGVM-LAB",
    "serial": "FGVMMLTMXXXXXXXXX",
    "version": "v7.6.5",
    "model": "FortiGate"
  },
  "steps_completed": [
    "ssh_connect",
    "create_api_user",
    "generate_api_key",
    "test_api",
    "register_device"
  ],
  "credentials_file": "/path/to/fortigate_credentials.yaml",
  "message": "Device 'lab-vm02' onboarded successfully"
}
```

### Error Response
```json
{
  "success": false,
  "error": "SSH authentication failed for admin@10.0.1.1",
  "steps_completed": []
}
```

## Default Trusthosts

If not specified, these networks are allowed:
- 192.168.0.0/16
- 10.0.0.0/8
- 172.16.0.0/12

## FortiOS 7.6+ Notes

- Uses Bearer token authentication (required for 7.6+)
- Query parameter auth (`access_token=`) is deprecated
- Password prompts handled automatically during CLI operations

## Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| SSH auth failed | Wrong password | Verify admin credentials |
| API test failed | Trusthost blocking | Add your source IP to trusthosts |
| Key generation failed | CLI error | Check FortiGate CLI manually |

## Related Tools

- `fortigate-api-token-create` - Just create API token (no registration)
- `fortigate-device-register` - Just register existing token
- `fortigate-health-check` - Verify device connectivity
