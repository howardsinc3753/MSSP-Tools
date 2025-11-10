# FortiFlex MSSP Toolkit - Bug Fixes & Patches

**Last Updated**: November 9, 2025
**Status**: ✅ All Patches Applied and Tested

---

## Overview

This document tracks all bug fixes and patches applied to the FortiFlex MSSP Toolkit in November 2025. These patches address critical API compatibility issues discovered during production testing.

---

## Patch Summary

| Patch | Use Case | Issue | Status | Date Applied |
|-------|----------|-------|--------|--------------|
| **PATCH 1** | Use Case 7 | Removed deprecated `list_programs()` | ✅ Applied | Nov 9, 2025 |
| **PATCH 2** | Use Case 1 | Fixed points calculation response format | ✅ Applied | Nov 9, 2025 |
| **PATCH 3** | Use Case 3 | Added FortiGate VM (ID 1) support | ✅ Applied | Nov 9, 2025 |
| **PATCH 4** | Use Case 7 | Added required `account_id` parameter | ✅ Applied | Nov 9, 2025 |
| **PATCH 5** | Use Case 5 | Replaced `list_entitlements()` with consumption API | ✅ Applied | Nov 9, 2025 |

---

## PATCH 1: Use Case 7 - Removed list_programs()

**File**: `examples/use_case_7_program_balance_monitoring.py`

**Issue**: The `list_programs()` API endpoint is deprecated and no longer returns program information reliably for MSSP postpaid programs.

**Symptoms**:
```
Error: Programs list is empty
Unable to determine program type
```

**Root Cause**: FortiFlex API v2 deprecated the `/programs/list` endpoint for MSSP programs.

**Solution**: Removed `list_programs()` call. Program serial number is now provided via credentials configuration.

**Code Changes**:
```python
# BEFORE (BROKEN):
def get_program_info(client):
    programs = client.list_programs()  # Returns empty list!
    program = programs['programs'][0]
    return program

# AFTER (FIXED):
def get_program_info(program_sn):
    # Program serial provided via credentials
    # MSSP programs always have 50,000 points/year minimum
    return {
        'serialNumber': program_sn,
        'programType': 'MSSP (Postpaid)',
        'minimumCommitment': 50000
    }
```

**Testing**: ✅ Verified script runs successfully with consumption tracking

---

## PATCH 2: Use Case 1 - Fixed Points Calculation Response Format

**File**: `examples/use_case_1_customer_onboarding.py`

**Issue**: The `/tools/calc` API response format changed. Points are now nested under `points.current` instead of top-level `points`.

**Symptoms**:
```python
KeyError: 'points' is not a float, it's a dict
TypeError: unsupported operand type(s) for *: 'dict' and 'int'
```

**Root Cause**: API response format updated in FortiFlex 25.1.0:
```json
// OLD FORMAT:
{"status": 0, "points": 12.5}

// NEW FORMAT:
{"status": 0, "points": {"current": 12.5, "latest": 12.5, "latestEffectiveDate": "2025-11-01"}}
```

**Solution**: Updated code to extract `points['current']` from nested response.

**Code Changes**:
```python
# BEFORE (BROKEN):
result = client.calculate_points(product_type_id=101, count=1, parameters=params)
daily_cost = result['points'] * quantity  # ERROR: 'points' is a dict!

# AFTER (FIXED):
result = client.calculate_points(product_type_id=101, count=1, parameters=params)
daily_cost = result['points']['current'] * quantity  # Correct
```

**Testing**: ✅ Cost estimation now calculates correctly for all product types

---

## PATCH 3: Use Case 3 - Added FortiGate VM Support

**File**: `examples/use_case_3_service_modification.py`

**Issue**: Script only supported FortiGate Hardware (Product Type ID 101), not FortiGate VM (Product Type ID 1).

**Symptoms**:
```
Error: Unsupported product type: FortiGate-VM (1)
This script only supports FortiGate Hardware
```

**Root Cause**: Original implementation assumed only hardware would need service modifications. However, FortiGate VM is commonly used and has identical parameter structure.

**Solution**: Added support for Product Type ID 1 (FortiGate-VM) alongside Product Type ID 101 (FortiGate-Hardware).

**Code Changes**:
```python
# BEFORE (LIMITED):
SUPPORTED_PRODUCTS = {
    101: 'FortiGate-Hardware'
}

if product_type_id not in SUPPORTED_PRODUCTS:
    raise ValueError("Only FortiGate Hardware supported")

# AFTER (EXPANDED):
SUPPORTED_PRODUCTS = {
    1: 'FortiGate-VM',
    101: 'FortiGate-Hardware'
}

if product_type_id not in SUPPORTED_PRODUCTS:
    raise ValueError("Only FortiGate VM and Hardware supported")
```

**Parameter Mapping**:
Both product types use the same parameters:
- Parameter 27: CPU/Model (e.g., "2C4G" for VM, "FGT60F" for Hardware)
- Parameter 28: Service Package (e.g., "FC247", "UTP", "ATP", "ENT")
- Parameter 29: Addons (e.g., "FGHWSOCA", "FGHWFAZC")

**Testing**: ✅ Service modifications now work for both VM and Hardware FortiGates

---

## PATCH 4: Use Case 7 - Added account_id Parameter

**File**: `examples/use_case_7_program_balance_monitoring.py`

**Issue**: The `get_entitlement_points()` API call requires `account_id` parameter for consumption data retrieval.

**Symptoms**:
```
Error: Missing required parameter: accountId
Unable to retrieve consumption data
```

**Root Cause**: FortiFlex API v2 requires `account_id` when querying consumption data at the program level.

**Solution**: Added `account_id` parameter to consumption API calls, loaded from credentials.

**Code Changes**:
```python
# BEFORE (BROKEN):
consumption = client.get_entitlement_points(
    start_date=start_date,
    end_date=end_date
)  # ERROR: Missing account_id

# AFTER (FIXED):
ACCOUNT_ID = creds['fortiflex'].get('account_id')

consumption = client.get_entitlement_points(
    account_id=ACCOUNT_ID,  # Required parameter
    start_date=start_date,
    end_date=end_date
)
```

**Credentials Update**:
```json
{
  "fortiflex": {
    "api_username": "user@company.com",
    "api_password": "password",
    "program_serial_number": "ELAVMS0000XXXXXX",
    "account_id": 12345  // ADDED
  }
}
```

**Testing**: ✅ Consumption data now retrieves correctly for trend analysis

---

## PATCH 5: Use Case 5 - Consumption-Based Entitlement Discovery

**File**: `examples/use_case_5_entitlement_suspension_v2.py`

**Issue**: The `list_entitlements()` API endpoint doesn't exist. No direct way to list entitlements by configuration.

**Symptoms**:
```
Error: Endpoint not found: /entitlements/list
Cannot find which devices use this configuration
```

**Root Cause**: FortiFlex API v2 does not provide an endpoint to list entitlements by configuration ID. The only way to discover entitlements is through consumption data.

**Solution**: Replaced non-existent `list_entitlements()` with consumption-based discovery using `get_entitlement_points()` API.

**Approach**:
1. Query consumption data for last 90 days
2. Filter by `config_id` (if provided) or `serial_number` (if provided)
3. Extract unique serial numbers from consumption records
4. Only active devices (consuming points) will appear

**Code Changes**:
```python
# BEFORE (BROKEN):
def list_entitlements_by_config(client, config_id):
    result = client.list_entitlements(config_id=config_id)  # DOESN'T EXIST!
    return result['entitlements']

# AFTER (FIXED):
def list_entitlements_by_config(client, config_id, account_id):
    """
    List entitlements using consumption data (last 90 days).
    NOTE: Only devices that have consumed points will appear.
    """
    from datetime import datetime, timedelta

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=90)

    # Get consumption data
    result = client.get_entitlement_points(
        config_id=config_id,
        account_id=account_id,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d")
    )

    # Extract unique serial numbers
    serials_found = {}
    for item in result.get('entitlements', []):
        serial = item.get('serialNumber')
        if serial and serial not in serials_found:
            serials_found[serial] = {
                'serialNumber': serial,
                'accountId': item.get('accountId'),
                'status': 'ACTIVE'
            }

    return list(serials_found.values())
```

**Limitations**:
- ⚠️ Only shows devices that consumed points in last 90 days
- ⚠️ Devices in PENDING status (never activated) won't appear
- ⚠️ Idle devices (no consumption) won't appear
- ✅ Suspension still works even if device not found in consumption data

**User Notifications**:
Script now provides clear messaging:
```
[NOTE] Searching consumption data (last 90 days) to find active entitlements...
       Only devices that have consumed points will appear.

[INFO] No consumption data found for this configuration.
       This means either:
       1. No entitlements exist for this config
       2. Entitlements exist but haven't consumed points in 90 days
       3. Entitlements are in PENDING status (not activated yet)
```

**Testing**: ✅ Successfully lists and suspends active entitlements

---

## Impact Summary

### Before Patches (Broken):
- ❌ Use Case 1: Cost estimation failing
- ❌ Use Case 3: Only Hardware FortiGates supported
- ❌ Use Case 5: Cannot list entitlements
- ❌ Use Case 7: Cannot retrieve program info or consumption data

### After Patches (Fixed):
- ✅ Use Case 1: Cost estimation accurate
- ✅ Use Case 3: VM and Hardware FortiGates supported
- ✅ Use Case 5: Consumption-based discovery working
- ✅ Use Case 7: Program monitoring with trend analysis working

---

## Testing Results

All 7 use cases tested on **November 9, 2025**:

| Use Case | Status | Notes |
|----------|--------|-------|
| Use Case 1 - Onboarding | ✅ Pass | Cost calculation correct |
| Use Case 2 - Expansion | ✅ Pass | No changes needed |
| Use Case 3 - Modification | ✅ Pass | VM + Hardware support |
| Use Case 4 - Consumption (v2) | ✅ Pass | No changes needed |
| Use Case 5 - Suspension | ✅ Pass | Consumption-based discovery |
| Use Case 6 - Multi-tenant | ✅ Pass | No changes needed |
| Use Case 7 - Monitoring | ✅ Pass | Consumption tracking working |

---

## API Version Compatibility

These patches ensure compatibility with:
- **FortiFlex API**: v2
- **FortiFlex Release**: 25.1.0
- **API Documentation**: https://fndn.fortinet.net (November 2025)

---

## Migration Guide

If you're using an older version of this toolkit:

1. **Update credentials** to include `account_id`:
   ```json
   {
     "fortiflex": {
       "account_id": YOUR_ACCOUNT_ID
     }
   }
   ```

2. **Replace old scripts** with patched versions from `/examples`

3. **Update any custom integrations**:
   - Use `points['current']` instead of `points`
   - Add `account_id` to consumption API calls
   - Remove any `list_programs()` calls
   - Use consumption data instead of `list_entitlements()`

4. **Test thoroughly** in non-production environment first

---

## Rollback Procedure

If issues occur after applying patches:

1. **Revert to previous version** (if committed to git)
2. **Check API documentation** for latest endpoint changes
3. **Report issues** to Fortinet Support with API error logs
4. **Document workarounds** in this file for team reference

---

## Future Maintenance

**Watch for API Changes**:
- Monitor https://fndn.fortinet.net for API updates
- Subscribe to Fortinet Developer Network notifications
- Test toolkit quarterly against latest FortiFlex release

**Known API Limitations** (as of Nov 2025):
- No direct entitlement listing endpoint (use consumption data)
- No program listing for MSSP programs (use credentials)
- Consumption data only available for 3 months in portal (store locally!)
- 90-day window for consumption-based discovery

---

**Questions or Issues?**

Contact: Fortinet Support (https://support.fortinet.com)
Documentation: https://docs.fortinet.com/document/flex-vm/
