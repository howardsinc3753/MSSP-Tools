# FortiFlex MSSP API Integration Guide
## Complete Use Cases & Implementation Guide

**Version:** 1.1
**Date:** November 2025
**Status:** ✅ Updated for FortiFlex 25.1.0 with November 2025 bug fixes
**Target Audience:** Partner Development Teams, DevOps Engineers, MSSP Technical Teams

> **📌 Important**: This guide reflects November 2025 API updates. See [BUGFIX_USE_CASES.md](../BUGFIX_USE_CASES.md) for recent compatibility patches.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Prerequisites & Authentication](#prerequisites--authentication)
3. [Product Type Parameter Reference](#product-type-parameter-reference)
4. [Use Case 1: Customer Onboarding](#use-case-1-customer-onboarding)
5. [Use Case 2: Service Expansion - Adding New Devices](#use-case-2-service-expansion---adding-new-devices)
6. [Use Case 3: Service Modification - Adding/Removing Addons](#use-case-3-service-modification---addingremoving-addons)
7. [Use Case 4: Daily Consumption Data Pull (Billing)](#use-case-4-daily-consumption-data-pull-billing)
8. [Use Case 5: Customer Suspension/Offboarding](#use-case-5-customer-suspensionoffboarding)
9. [Use Case 6: Multi-Tenant Operations View](#use-case-6-multi-tenant-operations-view)
10. [Use Case 7: Program Balance Monitoring](#use-case-7-program-balance-monitoring)
11. [Error Handling Reference](#error-handling-reference)
12. [Data Warehouse Schema](#data-warehouse-schema)

---

## Executive Summary

This guide provides complete implementation patterns for integrating FortiFlex MSSP (postpaid) programs with partner systems. It covers the seven most critical operational use cases for managing multi-tenant customer deployments.

### What is FortiFlex MSSP?

- **Postpaid billing model** - Monthly invoicing based on actual usage
- **Daily point consumption** - Resources charged per day (PST/PDT timezone)
- **Minimum commitment** - 50,000 points/year required
- **Multi-tenant by design** - Manage multiple customer accounts from one program
- **Flexible consumption** - Scale up/down/in/out without procurement delays

### Key API Capabilities

✅ Automate customer onboarding  
✅ Provision hardware & cloud services on-demand  
✅ Track daily consumption for billing  
✅ Manage service lifecycle (suspend/reactivate)  
✅ Multi-tenant operations view  
✅ Cost estimation & planning  

---

## Prerequisites & Authentication

### 1. API User Setup

**Create API user in FortiCloud IAM:**

1. Log into https://support.fortinet.com
2. Navigate to **IAM (Identity & Access Management)**
3. Click **Add API User**
4. Save the generated `username` and `password`
5. Assign permissions:
   - **FortiFlex:** ReadWrite or Admin
   - **Asset Management:** ReadWrite or Admin (optional)

### 2. OAuth Token Generation

**Endpoint:** `https://customerapiauth.fortinet.com/api/v1/oauth/token/`

**Request:**
```bash
curl -X POST https://customerapiauth.fortinet.com/api/v1/oauth/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "YOUR_API_USERNAME",
    "password": "YOUR_API_PASSWORD",
    "client_id": "flexvm",
    "grant_type": "password"
  }'
```

**Response:**
```json
{
  "access_token": "YOUR_TOKEN_HERE",
  "expires_in": 3660,
  "token_type": "Bearer",
  "scope": "read write",
  "message": "successfully authenticated",
  "status": "success"
}
```

**Token Lifetime:** 1 hour (3660 seconds)

### 3. API Base URLs

- **FortiFlex API:** `https://support.fortinet.com/ES/api/fortiflex/v2`
- **Asset Management API:** `https://support.fortinet.com/ES/api/registration/v3`

### 4. Rate Limits

- **100 requests per minute**
- **1,000 requests per hour**
- **Max 10 errors per hour** (for config/entitlement creation)

---

## Product Type Parameter Reference

> **📚 Complete Reference**: See [PRODUCT_TYPE_REFERENCE.md](../examples/PRODUCT_TYPE_REFERENCE.md) for the full FortiFlex 25.1.0 product catalog.

### FortiGate Hardware (productTypeId: 101)

| Parameter ID | Name | Purpose | Values |
|--------------|------|---------|--------|
| **27** | PRODUCTMODEL | Device model | FGT40F, FGT60F, FGT70F, FGT80F, FG100F, FG200F, FG201F, FG4H0F, FG6H0F, FG1K0F, FG18KF, FG36KF |
| **28** | SERVICEPACK | Service bundle | FGHWFC247, FGHWUTP, FGHWATP, FGHWENT, FGHWFCEL |
| **29** | SERVICEPACK | Addons (multi) | See addon table below |

**FortiGate Hardware Addons (Parameter 29):**
```
NONE             - No addons
FGHWFCELU        - FortiCare Elite Upgrade
FGHWFAMS         - FortiGate Cloud Management
FGHWFAIS         - AI-Based In-line Sandbox
FGHWSWNM         - SD-WAN Underlay
FGHWDLDB         - FortiGuard DLP
FGHWFAZC         - FortiAnalyzer Cloud
FGHWSOCA         - SOCaaS
FGHWMGAS         - Managed FortiGate Service
FGHWSPAL         - SD-WAN Connector for FortiSASE
FGHWISSS         - FortiGuard OT Security Service
FGHWSWOS         - SD-WAN Overlay-as-a-Service
FGHWAVDB         - Advanced Malware Protection
FGHWNIDS         - Intrusion Prevention
FGHWFGSA         - Attack Surface Security Service
FGHWFURL         - Web, DNS & Video Filtering
FGHWFSFG         - FortiSASE Subscription
```

### FortiAP Hardware (productTypeId: 102)

| Parameter ID | Name | Purpose | Values |
|--------------|------|---------|--------|
| **55** | PRODUCTMODEL | Device model | FP231F, FP431F, FP433F, FP831F, PU231F, PU431F, etc. |
| **56** | SERVICEPACK | Service bundle | FAPHWFC247, FAPHWFCEL |
| **57** | SERVICEPACK | Addons | FAPHWFSFG (FortiSASE Cloud Managed AP), NONE |

### FortiSwitch Hardware (productTypeId: 103)

| Parameter ID | Name | Purpose | Values |
|--------------|------|---------|--------|
| **53** | PRODUCTMODEL | Device model | S124FP, S248FF, S648FN, S624FN, etc. |
| **54** | SERVICEPACK | Service bundle | FSWHWFC247, FSWHWFCEL |

### FortiEDR MSSP (productTypeId: 206)

| Parameter ID | Name | Purpose | Values |
|--------------|------|---------|--------|
| **46** | SERVICEPACK | Service type | FEDRPDR (Prevent/Detect/Respond) |
| **47** | ENDPOINT | Endpoint count | 0, 100, 500, 1000, 5000, etc. |
| **52** | SERVICEPACK | Addons | FEDRXDR, FEDRMDR, NONE |
| **76** | STORAGE | Repository GB | 512, 1024, 2048, 3072, etc. (512 increments, scales up only) |

---

## Use Case 1: Customer Onboarding

**Business Scenario:** New customer signs MSSP contract. Provision initial infrastructure with FortiGate hardware, FortiSwitch, FortiAP, and FortiEDR endpoint protection.

**Customer Profile:**
- 3x FortiGate-60F (UTP bundle + FortiAnalyzer Cloud)
- 12x FortiSwitch 124F-POE (Premium support)
- 8x FortiAP-231F (Premium support)
- 250x FortiEDR endpoints (PDR service)

### Step 1: Validate Program Balance

**MSSP Note:** For postpaid programs, this check isn't required (monthly billing). Include it for prepaid programs only.

```bash
# Check available points (prepaid only)
curl -X POST https://support.fortinet.com/ES/api/fortiflex/v2/programs/points \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "programSerialNumber": "ELAVMSXXXXXXXX"
  }'
```

### Step 2: Calculate Expected Cost

```bash
# Estimate points for FortiGate-60F with UTP + FAZ Cloud
curl -X POST https://support.fortinet.com/ES/api/fortiflex/v2/tools/calc \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "programSerialNumber": "ELAVMSXXXXXXXX",
    "productTypeId": 101,
    "count": 3,
    "parameters": [
      {"id": 27, "value": "FGT60F"},
      {"id": 28, "value": "FGHWUTP"},
      {"id": 29, "value": "FGHWFAZC"}
    ]
  }'
```

**Response** (FortiFlex 25.1.0 format):
```json
{
  "status": 0,
  "message": "Request processed successfully",
  "points": {
    "current": 12.5,
    "latest": 12.5,
    "latestEffectiveDate": "2025-11-01"
  }
}
```

> **⚠️ API Change (Nov 2025)**: Points are now nested under `points.current`. Use `result['points']['current']` instead of `result['points']`. See [BUGFIX_USE_CASES.md - PATCH 2](../BUGFIX_USE_CASES.md#patch-2-use-case-1---fixed-points-calculation-response-format).

**Calculation:** 12.5 points/day × 3 devices = **37.5 points/day** = **1,125 points/month**

### Step 3: Create Configurations

**Python Example:**
```python
import requests
import json

class FortiFlex Client:
    def __init__(self, token, program_sn):
        self.token = token
        self.program_sn = program_sn
        self.base_url = "https://support.fortinet.com/ES/api/fortiflex/v2"
        
    def create_config(self, name, product_type_id, parameters, account_id=None):
        """Create a new configuration"""
        url = f"{self.base_url}/configs/create"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "programSerialNumber": self.program_sn,
            "name": name,
            "productTypeId": product_type_id,
            "parameters": parameters
        }
        
        if account_id:
            payload["accountId"] = account_id
            
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()

# Initialize client
client = FortiFlexClient(
    token="YOUR_TOKEN_HERE",
    program_sn="ELAVMS0000XXXXXX"
)

# Create FortiGate Hardware config
fgt_config = client.create_config(
    name="Customer-Acme-FGT-60F-UTP-FAZ",
    product_type_id=101,
    account_id=YOUR_ACCOUNT_ID,  # Customer's account ID
    parameters=[
        {"id": 27, "value": "FGT60F"},
        {"id": 28, "value": "FGHWUTP"},
        {"id": 29, "value": "FGHWFAZC"}
    ]
)

print(f"FortiGate Config ID: {fgt_config['configs']['id']}")

# Create FortiSwitch config
fsw_config = client.create_config(
    name="Customer-Acme-FSW-124F",
    product_type_id=103,
    account_id=YOUR_ACCOUNT_ID,
    parameters=[
        {"id": 53, "value": "S124FP"},
        {"id": 54, "value": "FSWHWFC247"}
    ]
)

print(f"FortiSwitch Config ID: {fsw_config['configs']['id']}")

# Create FortiAP config
fap_config = client.create_config(
    name="Customer-Acme-FAP-231F",
    product_type_id=102,
    account_id=YOUR_ACCOUNT_ID,
    parameters=[
        {"id": 55, "value": "FP231F"},
        {"id": 56, "value": "FAPHWFC247"},
        {"id": 57, "value": "NONE"}
    ]
)

print(f"FortiAP Config ID: {fap_config['configs']['id']}")

# Create FortiEDR config
edr_config = client.create_config(
    name="Customer-Acme-EDR-250-Users",
    product_type_id=206,
    account_id=YOUR_ACCOUNT_ID,
    parameters=[
        {"id": 46, "value": "FEDRPDR"},
        {"id": 47, "value": "250"},
        {"id": 52, "value": "NONE"},
        {"id": 76, "value": "1024"}
    ]
)

print(f"FortiEDR Config ID: {edr_config['configs']['id']}")
```

### Step 4: Create Hardware Entitlements

```python
def create_hardware_entitlements(self, config_id, serial_numbers, end_date=None):
    """Create hardware entitlements"""
    url = f"{self.base_url}/entitlements/hardware/create"
    headers = {
        "Authorization": f"Bearer {self.token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "configId": config_id,
        "serialNumbers": serial_numbers,
        "endDate": end_date  # null = use program end date
    }
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

# Create FortiGate entitlements
fgt_entitlements = client.create_hardware_entitlements(
    config_id=fgt_config['configs']['id'],
    serial_numbers=[
        "FGT60FTK20001234",
        "FGT60FTK20001235",
        "FGT60FTK20001236"
    ]
)

print(f"Created {len(fgt_entitlements['entitlements'])} FortiGate entitlements")

# Create FortiSwitch entitlements
fsw_entitlements = client.create_hardware_entitlements(
    config_id=fsw_config['configs']['id'],
    serial_numbers=[
        "S124FPTK20001001", "S124FPTK20001002", "S124FPTK20001003",
        "S124FPTK20001004", "S124FPTK20001005", "S124FPTK20001006",
        "S124FPTK20001007", "S124FPTK20001008", "S124FPTK20001009",
        "S124FPTK20001010", "S124FPTK20001011", "S124FPTK20001012"
    ]
)

print(f"Created {len(fsw_entitlements['entitlements'])} FortiSwitch entitlements")

# Create FortiAP entitlements
fap_entitlements = client.create_hardware_entitlements(
    config_id=fap_config['configs']['id'],
    serial_numbers=[
        "FP231FTK20002001", "FP231FTK20002002", "FP231FTK20002003",
        "FP231FTK20002004", "FP231FTK20002005", "FP231FTK20002006",
        "FP231FTK20002007", "FP231FTK20002008"
    ]
)

print(f"Created {len(fap_entitlements['entitlements'])} FortiAP entitlements")
```

### Step 5: Create Cloud Service Entitlements

```python
def create_cloud_entitlements(self, config_id, end_date=None):
    """Create cloud service entitlements"""
    url = f"{self.base_url}/entitlements/cloud/create"
    headers = {
        "Authorization": f"Bearer {self.token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "configId": config_id,
        "endDate": end_date
    }
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

# Create FortiEDR cloud entitlement
edr_entitlement = client.create_cloud_entitlements(
    config_id=edr_config['configs']['id']
)

print(f"FortiEDR Serial: {edr_entitlement['entitlements'][0]['serialNumber']}")
```

### Step 6: Organize Assets in FortiCloud (Optional)

**Use Asset Management API to organize products into customer folder:**

```python
def move_to_folder(self, serial_numbers, folder_id, asset_token):
    """Move products to specific folder"""
    url = "https://support.fortinet.com/ES/api/registration/v3/products/folder"
    headers = {
        "Authorization": f"Bearer {asset_token}",
        "Content-Type": "application/json"
    }
    
    for serial in serial_numbers:
        payload = {
            "serialNumber": serial,
            "folderId": folder_id  # null = My Assets root
        }
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()

# Organize all devices into customer folder
all_serials = (
    [e['serialNumber'] for e in fgt_entitlements['entitlements']] +
    [e['serialNumber'] for e in fsw_entitlements['entitlements']] +
    [e['serialNumber'] for e in fap_entitlements['entitlements']] +
    [edr_entitlement['entitlements'][0]['serialNumber']]
)

client.move_to_folder(
    serial_numbers=all_serials,
    folder_id=67890,  # Customer's folder ID
    asset_token="ASSET_MGMT_TOKEN_HERE"
)
```

### Complete Onboarding Summary

**Created:**
- ✅ 4 configurations (FGT, FSW, FAP, EDR)
- ✅ 3 FortiGate entitlements
- ✅ 12 FortiSwitch entitlements
- ✅ 8 FortiAP entitlements
- ✅ 1 FortiEDR entitlement (250 users)
- ✅ All assets organized in customer folder

**Billing Started:**
- **Hardware:** Billing starts immediately upon entitlement creation
- **Cloud:** Billing starts immediately upon entitlement creation

**Expected Monthly Cost:** Calculate using `/tools/calc` for each config × count

---

## Use Case 2: Service Expansion - Adding New Devices

**Business Scenario:** Customer needs to add more devices to existing deployment. Add 5 more FortiGates to their existing configuration.

**Workflow:** Use existing configuration → Create new entitlements → Billing starts same day

### Step 1: Find Customer's Configuration

```python
def list_configs(self, account_id=None):
    """List configurations for account or all accounts"""
    url = f"{self.base_url}/configs/list"
    headers = {
        "Authorization": f"Bearer {self.token}",
        "Content-Type": "application/json"
    }
    
    payload = {"programSerialNumber": self.program_sn}
    if account_id:
        payload["accountId"] = account_id
        
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

# Find customer's FortiGate config
configs = client.list_configs(account_id=YOUR_ACCOUNT_ID)

fgt_config_id = None
for config in configs['configs']:
    if config['productType']['id'] == 101 and 'FGT-60F' in config['name']:
        fgt_config_id = config['id']
        print(f"Found config: {config['name']} (ID: {fgt_config_id})")
        break
```

### Step 2: Add New Entitlements to Existing Config

```python
# Add 5 more FortiGate-60Fs
new_serials = [
    "FGT60FTK20001237",
    "FGT60FTK20001238",
    "FGT60FTK20001239",
    "FGT60FTK20001240",
    "FGT60FTK20001241"
]

new_entitlements = client.create_hardware_entitlements(
    config_id=fgt_config_id,
    serial_numbers=new_serials
)

print(f"✅ Added {len(new_entitlements['entitlements'])} FortiGates")
print(f"   Billing starts: {new_entitlements['entitlements'][0]['startDate']}")
```

### cURL Alternative

```bash
# Add devices to existing config
curl -X POST https://support.fortinet.com/ES/api/fortiflex/v2/entitlements/hardware/create \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "configId": 12345,
    "serialNumbers": [
      "FGT60FTK20001237",
      "FGT60FTK20001238",
      "FGT60FTK20001239",
      "FGT60FTK20001240",
      "FGT60FTK20001241"
    ],
    "endDate": null
  }'
```

**Result:** 5 new devices inherit all settings from the existing configuration (UTP + FortiAnalyzer Cloud). Billing starts same day.

---

## Use Case 3: Service Modification - Adding/Removing Addons

**Business Scenario:** Customer wants to add SOCaaS to their existing FortiGate deployment.

> **✅ Updated (Nov 2025)**: Now supports both FortiGate VM (Product Type ID 1) and FortiGate Hardware (Product Type ID 101). See [BUGFIX_USE_CASES.md - PATCH 3](../BUGFIX_USE_CASES.md#patch-3-use-case-3---added-fortigate-vm-support).

**⚠️ CRITICAL:** Updating a configuration affects **ALL** entitlements using that config!

### Option A: Update Existing Config (Affects All Devices)

**Use when:** All devices should get the new addon

```python
def update_config(self, config_id, name=None, parameters=None):
    """Update configuration name and/or parameters"""
    url = f"{self.base_url}/configs/update"
    headers = {
        "Authorization": f"Bearer {self.token}",
        "Content-Type": "application/json"
    }
    
    payload = {"id": config_id}
    if name:
        payload["name"] = name
    if parameters:
        payload["parameters"] = parameters
        
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

# Add SOCaaS to existing FortiGate config
updated_config = client.update_config(
    config_id=fgt_config_id,
    parameters=[
        {"id": 27, "value": "FGT60F"},
        {"id": 28, "value": "FGHWUTP"},
        {"id": 29, "value": "FGHWFAZC"},  # Existing addon
        {"id": 29, "value": "FGHWSOCA"}   # NEW: SOCaaS
    ]
)

print("✅ Configuration updated")
print("⚠️  All 8 FortiGates now have SOCaaS enabled")
```

### Option B: Create New Config (Selective Upgrade)

**Use when:** Only some devices should get the new addon

```python
# Create new "Premium" config with SOCaaS
fgt_premium_config = client.create_config(
    name="Customer-Acme-FGT-60F-UTP-FAZ-SOC",
    product_type_id=101,
    account_id=YOUR_ACCOUNT_ID,
    parameters=[
        {"id": 27, "value": "FGT60F"},
        {"id": 28, "value": "FGHWUTP"},
        {"id": 29, "value": "FGHWFAZC"},
        {"id": 29, "value": "FGHWSOCA"}
    ]
)

premium_config_id = fgt_premium_config['configs']['id']

# Move specific devices to new config
def update_entitlement(self, serial_number, config_id, description=None, end_date=None):
    """Update entitlement to use different config"""
    url = f"{self.base_url}/entitlements/update"
    headers = {
        "Authorization": f"Bearer {self.token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "serialNumber": serial_number,
        "configId": config_id
    }
    if description:
        payload["description"] = description
    if end_date:
        payload["endDate"] = end_date
        
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

# Move 3 specific FortiGates to premium config
devices_to_upgrade = [
    "FGT60FTK20001234",
    "FGT60FTK20001235",
    "FGT60FTK20001236"
]

for serial in devices_to_upgrade:
    result = client.update_entitlement(
        serial_number=serial,
        config_id=premium_config_id
    )
    print(f"✅ Upgraded {serial} to SOCaaS")
```

### Cost Impact Analysis

```python
# Calculate cost difference
old_cost = client.calculate_points(
    product_type_id=101,
    count=1,
    parameters=[
        {"id": 27, "value": "FGT60F"},
        {"id": 28, "value": "FGHWUTP"},
        {"id": 29, "value": "FGHWFAZC"}
    ]
)

new_cost = client.calculate_points(
    product_type_id=101,
    count=1,
    parameters=[
        {"id": 27, "value": "FGT60F"},
        {"id": 28, "value": "FGHWUTP"},
        {"id": 29, "value": "FGHWFAZC"},
        {"id": 29, "value": "FGHWSOCA"}
    ]
)

increase = new_cost['points']['current'] - old_cost['points']['current']
print(f"Cost increase: +{increase} points/day per device")
print(f"Monthly increase for 3 devices: +{increase * 3 * 30} points")
```

---

## Production-Ready Scripts

> **📦 Reference Implementation**: For production-ready, tested scripts implementing all use cases, see the `/examples` directory:
> - [EXAMPLES_SUMMARY.md](../examples/EXAMPLES_SUMMARY.md) - Complete guide with sample outputs
> - All scripts tested with FortiFlex 25.1.0 (November 2025)
> - Includes error handling, rate limiting, and retry logic

---

**[Continue to Part 2 with Use Cases 4-7...]**
