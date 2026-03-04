# FortiFlex Entitlements List - Skills Guide

## Overview
List all FortiFlex entitlements (VM licenses and hardware licenses) under a program. Shows serial numbers, config assignments, status, and optionally license tokens.

## When to Use
- To see what licenses/entitlements exist in a FortiFlex program
- To check the status of an entitlement (ACTIVE, STOPPED)
- To find serial numbers for VM or hardware licenses
- To verify entitlement creation succeeded
- To audit license inventory

## Prerequisites
- FortiCloud API credentials with FortiFlex access
- Program serial number (ELAVMSXXXXXXXX)

## Parameters
| Parameter | Required | Description |
|-----------|----------|-------------|
| config_id | No | Filter by configuration ID |
| serial_number | No | Filter by specific serial number |
| account_id | No | Filter by customer account ID (multi-tenant) |
| program_serial_number | No | Override program SN from config |
| api_username | No | Override API username |
| api_password | No | Override API password |

## Example Usage

### List All Entitlements
```json
{}
```

### Filter by Configuration
```json
{
  "config_id": 53713
}
```

### Filter by Serial Number
```json
{
  "serial_number": "FGVMMLTM00000123"
}
```

## Output Fields
| Field | Description |
|-------|-------------|
| serial_number | License serial number (FGVMXXXXXX for VMs) |
| config_id | Associated configuration ID |
| config_name | Configuration name |
| product_type | Product type (FortiGate-VM, FortiEDR, etc.) |
| status | ACTIVE, STOPPED, PENDING |
| start_date | Billing start date |
| end_date | License end date |
| token | License token (if available) |

## Workflow Context

### Typical FortiFlex Workflow:
1. **List Programs** → Get program serial number
2. **List Configs** → See available configurations
3. **Create Config** → Define new product bundle (optional)
4. **Create Entitlement** → Generate license (hardware or cloud)
5. **List Entitlements** ← THIS TOOL - Verify creation
6. **Get Token** → Get license token for VM activation

### Related Tools:
- `fortiflex-programs-list` - List FortiFlex programs
- `fortiflex-config-list` - List configurations
- `fortiflex-config-create` - Create new configuration
- `fortiflex-token-create` - Create cloud entitlements
