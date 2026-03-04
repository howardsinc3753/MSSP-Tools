# FortiFlex Token Create Skills

## Overview

Create FortiFlex license tokens for VM provisioning. These tokens can be applied to FortiGate VMs, FortiManager VMs, and FortiAnalyzer VMs.

**IMPORTANT**: This tool uses the `entitlements/vm/create` endpoint for virtual appliances.

### API Endpoint Reference

| Product Type | API Endpoint | Notes |
|--------------|--------------|-------|
| Virtual appliances (FortiGate-VM, FMG-VM, FAZ-VM) | `entitlements/vm/create` | Generates serial + token |
| Physical hardware (FortiGate HW, FortiSwitch, FortiAP) | `entitlements/hardware/create` | Requires existing serial numbers |
| Cloud services (FortiEDR, FortiSASE) | `entitlements/cloud/create` | For cloud SaaS products |

## When to Use

Use this tool when:
- Provisioning a new FortiGate VM that needs licensing
- Deploying FortiManager-VM or FortiAnalyzer-VM
- Automating VM deployment with pre-generated licenses
- Creating tokens for SD-WAN site deployments

**Example prompts:**
- "Create a FortiFlex token for the new FortiGate VM"
- "Generate 3 license tokens from config 12345"
- "Provision a license for our new cloud deployment"

## Prerequisites

1. **FortiFlex Program** - Active FortiFlex/FlexVM program
2. **Configuration** - Existing FortiFlex configuration (use fortiflex-config-list)
3. **API Credentials** - ReadWrite or Admin access to FlexVM portal
4. **Client ID**: `flexvm`

## Configuration

Add credentials to `C:\ProgramData\Ulysses\config\forticloud_credentials.yaml`:

```yaml
api_username: "YOUR-API-USER-ID"
api_password: "your-api-password"
program_serial_number: "ELAVMS0000003536"  # Your FortiFlex program SN
```

**Warning**: This tool **creates billable entitlements** that consume FortiFlex points. Verify config_id before execution.

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `config_id` | integer | **Yes** | - | FortiFlex configuration ID |
| `count` | integer | No | 1 | Number of tokens (1-10) |
| `end_date` | string | No | program end | End date (YYYY-MM-DD) |
| `description` | string | No | - | Token description |
| `api_username` | string | No | from config | Override credentials |
| `api_password` | string | No | from config | Override credentials |

## Typical Workflow

### 1. Find Configuration ID

```python
# First, list available configurations
result = execute_certified_tool(
    canonical_id="org.ulysses.cloud.fortiflex-config-list/1.0.0",
    parameters={}
)
# Find the config_id for your desired product/bundle
```

### 2. Create Token

```python
execute_certified_tool(
    canonical_id="org.ulysses.cloud.fortiflex-token-create/1.0.0",
    parameters={
        "config_id": 12345,
        "count": 1
    }
)
```

### 3. Apply Token to VM

Use the returned `token` string in the FortiGate VM CLI:
```
execute vm-license install <token>
```

## Example Usage

### Create Single Token

```python
execute_certified_tool(
    canonical_id="org.ulysses.cloud.fortiflex-token-create/1.0.0",
    parameters={
        "config_id": 12345
    }
)
```

### Create Multiple Tokens

```python
execute_certified_tool(
    canonical_id="org.ulysses.cloud.fortiflex-token-create/1.0.0",
    parameters={
        "config_id": 12345,
        "count": 5,
        "end_date": "2026-12-31"
    }
)
```

## Interpreting Results

### Success Response

```json
{
  "success": true,
  "tokens_created": 2,
  "tokens": [
    {
      "serial_number": "FGVMELTM25000001",
      "token": "A1B2C3D4E5F6G7H8I9J0...",
      "config_id": 12345,
      "status": "ACTIVE",
      "end_date": "2026-12-31"
    },
    {
      "serial_number": "FGVMELTM25000002",
      "token": "K1L2M3N4O5P6Q7R8S9T0...",
      "config_id": 12345,
      "status": "ACTIVE",
      "end_date": "2026-12-31"
    }
  ]
}
```

### Field Meanings

| Field | Description |
|-------|-------------|
| `serial_number` | VM serial number (use for tracking) |
| `token` | License token string (apply to VM) |
| `config_id` | Associated configuration |
| `status` | ACTIVE, STOPPED, etc. |
| `end_date` | License expiration |

## Common Configurations

| Product | Description | Typical config_id source |
|---------|-------------|-------------------------|
| FortiGate VM | Virtual firewall | fortiflex-config-list |
| FortiManager VM | Central management | fortiflex-config-list |
| FortiAnalyzer VM | Logging/analytics | fortiflex-config-list |
| FortiADC VM | Application delivery | fortiflex-config-list |

## Error Handling

| Error | Meaning | Suggestion |
|-------|---------|------------|
| `Missing config_id` | No configuration specified | Use fortiflex-config-list first |
| `count must be 1-10` | Invalid count value | Reduce count |
| `Authentication failed` | Invalid credentials | Check API credentials |
| `Insufficient points` | Not enough FortiFlex points | Check program balance |
| `Invalid configuration` | Config ID doesn't exist | Verify config_id |

## Applying Token to FortiGate VM

After getting the token, apply it to your FortiGate VM:

```bash
# SSH to FortiGate VM
ssh admin@fortigate-ip

# Apply license
execute vm-license install <token-string>

# Verify license
get system status
```

## Related Tools

- `fortiflex-config-list` - List available configurations
- `fortiflex-config-create` - Create new configurations
- `fortiflex-entitlement-stop` - Stop/suspend entitlements
- `fortiflex-consumption-report` - Check point consumption

## API Reference

- **Auth Endpoint**: `https://customerapiauth.fortinet.com/api/v1/oauth/token/`
- **API Endpoint**: `https://support.fortinet.com/ES/api/fortiflex/v2/entitlements/vm/create`
- **Method**: POST
- **Client ID**: `flexvm`
- **Required Scope**: ReadWrite or Admin

### Request Payload

```json
{
  "configId": 53713,
  "count": 1,
  "endDate": "2027-05-29"  // optional
}
```

### Response Structure

```json
{
  "entitlements": [
    {
      "serialNumber": "FGVMMLTMWWWWWWWWW",
      "token": "EF0AAE0ADA1B577453E3",
      "configId": 53713,
      "status": "PENDING",
      "startDate": "2026-01-18T07:47:42.257",
      "endDate": "2027-05-29T00:00:00",
      "tokenStatus": "NOTUSED",
      "accountId": 2322674
    }
  ],
  "status": 0,
  "message": "Request processed successfully."
}
```
