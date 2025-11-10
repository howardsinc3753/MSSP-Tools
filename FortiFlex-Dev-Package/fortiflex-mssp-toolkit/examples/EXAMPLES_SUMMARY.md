# FortiFlex MSSP Toolkit - Examples Summary

**Last Updated**: November 9, 2025
**Status**: ✅ All Examples Tested and Working
**Partner Demo Ready**: Yes

---

## 🎯 Quick Reference

| Example | Purpose | Status | Complexity |
|---------|---------|--------|------------|
| [Consumption Report v2](#consumption-report-v2) | Daily/monthly billing reports | ✅ Ready | ⭐ Easy |
| [Use Case 1](#use-case-1-customer-onboarding) | Customer onboarding | ✅ Ready | ⭐⭐ Medium |
| [Use Case 2](#use-case-2-service-expansion) | Add devices to existing customer | ✅ Ready | ⭐⭐ Medium |
| [Use Case 3](#use-case-3-service-modification) | Modify service packages | ✅ Ready | ⭐⭐ Medium |
| [Use Case 5](#use-case-5-entitlement-suspension) | Suspend/reactivate licenses | ✅ Ready | ⭐⭐ Medium |
| [Use Case 6](#use-case-6-multi-tenant-operations) | View all customers | ✅ Ready | ⭐ Easy |
| [Use Case 7](#use-case-7-program-balance-monitoring) | Monitor MSSP commitment | ✅ Ready | ⭐⭐ Medium |

---

## 📋 Prerequisites

Before running any examples:

1. **Configure Credentials** - Edit `testing/config/credentials.json`:
   ```json
   {
     "fortiflex": {
       "api_username": "your_username@company.com",
       "api_password": "your_password",
       "program_serial_number": "ELAVMS0000XXXXXX",
       "account_id": 12345
     }
   }
   ```

2. **Discover Your Program** (Optional - auto-fills credentials):
   ```bash
   python testing/discover_program.py
   ```

3. **Test Authentication**:
   ```bash
   python testing/test_authentication.py
   ```

---

## 📊 Consumption Report v2

**File**: `consumption_report_v2.py`
**Purpose**: Generate daily/monthly consumption reports for billing
**Read-Only**: Yes ✅
**Safe to Run**: Yes

### Quick Start
```bash
# Last 30 days (all entitlements)
python examples/consumption_report_v2.py

# Last 7 days
python examples/consumption_report_v2.py --days 7

# Specific device
python examples/consumption_report_v2.py --serial FGVMMLTMXXXXXXXX

# List all configurations
python examples/consumption_report_v2.py --list-configs
```

### What It Does
- Retrieves consumption data from FortiFlex API
- Calculates total points consumed per device
- Generates daily breakdown
- Exports to JSON for record-keeping

### Sample Output
```
================================================================================
CONSUMPTION REPORT - ALL ENTITLEMENTS - LAST 30 DAYS
================================================================================

Date Range: 2025-10-10 to 2025-11-09
Account ID: 12345

[SUCCESS] Retrieved consumption data for 5 entitlement(s)

Serial Number                  Account ID      Total Points
---------------------------------------------------------------
FMVMMLTMXXXXXXXX              12345                   9648.00
FGVMMLTMXXXXXXXX              12345                   4548.60
FGT60FTKXXXXXXXX              12345                   4050.90

GRAND TOTAL                                          18247.50
```

### Use Cases
- ✅ Monthly billing reports
- ✅ Customer invoicing
- ✅ Cost tracking
- ✅ Audit trail

---

## 🚀 Use Case 1: Customer Onboarding

**File**: `use_case_1_customer_onboarding.py`
**Purpose**: Provision new customer infrastructure
**Read-Only**: No ⚠️
**Creates**: Configurations + Entitlements

### Quick Start
```bash
# Dry run (cost estimation only)
python examples/use_case_1_customer_onboarding.py --dry-run

# Full onboarding (creates resources)
python examples/use_case_1_customer_onboarding.py
```

### What It Does
1. **Cost Estimation** - Calculate expected monthly consumption
2. **Create Configurations** - FortiGate, FortiSwitch, FortiAP, FortiEDR templates
3. **Create Entitlements** - Hardware licenses (with serial numbers) or cloud licenses
4. **Summary Report** - JSON output with all created resources

### Important Notes
- ⚠️ Edit the script to add YOUR device serial numbers before running
- ⚠️ This creates REAL resources and starts billing
- ✅ Uses rollback if any step fails
- ✅ Always run `--dry-run` first

### Sample Configuration
```python
customer_profile = {
    'name': 'Acme-Corp',
    'account_id': 12345,
    'products': [
        {
            'name': 'FGT-60F-UTP-FAZ',
            'product_type_id': 101,  # FortiGate Hardware
            'quantity': 3,
            'parameters': [
                {"id": 27, "value": "FGT60F"},
                {"id": 28, "value": "FGHWUTP"},
                {"id": 29, "value": "FGHWFAZC"}
            ],
            'serial_numbers': [
                "FGT60FTKXXXXXXXX",  # Replace with REAL serial numbers
                "FGT60FTKXXXXXXXX",
                "FGT60FTKXXXXXXXX"
            ]
        }
    ]
}
```

---

## 📈 Use Case 2: Service Expansion

**File**: `use_case_2_service_expansion.py`
**Purpose**: Add devices to existing customer
**Read-Only**: No ⚠️
**Creates**: Entitlements only

### Quick Start
```bash
# Add devices to existing configuration
python examples/use_case_2_service_expansion.py \
  --config-id 47456 \
  --serials FGT60FTKXXXXXXXX,FGT60FTKXXXXXXXX
```

### What It Does
1. Validates configuration exists
2. Creates new entitlements using that configuration
3. Optionally moves devices to FortiCloud folder

### When to Use
- ✅ Customer adds more devices
- ✅ Expanding existing deployment
- ✅ Replacement devices (RMA)

---

## 🔧 Use Case 3: Service Modification

**File**: `use_case_3_service_modification.py`
**Purpose**: Modify service packages (add/remove features)
**Read-Only**: No ⚠️
**Modifies**: Existing configurations

### Quick Start
```bash
# View current configuration
python examples/use_case_3_service_modification.py \
  --config-id 47456

# Make modifications (script will prompt for confirmation)
python examples/use_case_3_service_modification.py \
  --config-id 47456 \
  --confirm
```

### What It Does
1. Retrieves current configuration
2. Shows cost comparison (before/after)
3. Updates configuration parameters
4. Applies changes (affects future entitlements only)

### Supported Products
- ✅ FortiGate VM (Product Type ID: 1)
- ✅ FortiGate Hardware (Product Type ID: 101)

### Example: Add/Remove SOCaaS
```
Current Configuration:
  CPU: 2 cores
  Bundle: UTP (Unified Threat Protection)

Modification: Adding SOCaaS addon

Cost Comparison:
  Current: 12.50 points/day
  New: 15.75 points/day
  Difference: +3.25 points/day (+26.0%)

[CONFIRM] Apply changes? (yes/no):
```

---

## ⏸️ Use Case 5: Entitlement Suspension

**File**: `use_case_5_entitlement_suspension_v2.py`
**Purpose**: Suspend/reactivate device licenses
**Read-Only**: No ⚠️
**Modifies**: Entitlement status

### Quick Start
```bash
# List entitlements for a configuration
python examples/use_case_5_entitlement_suspension_v2.py \
  --config-id 47456 \
  --action list

# Suspend all devices in a configuration (customer non-payment)
python examples/use_case_5_entitlement_suspension_v2.py \
  --config-id 47456 \
  --action suspend

# Suspend one specific device
python examples/use_case_5_entitlement_suspension_v2.py \
  --serial FGT60FTKXXXXXXXX \
  --action suspend

# Reactivate after payment received
python examples/use_case_5_entitlement_suspension_v2.py \
  --config-id 47456 \
  --action reactivate

# Disable configuration (prevent NEW entitlements)
python examples/use_case_5_entitlement_suspension_v2.py \
  --config-id 47456 \
  --action disable-config
```

### What It Does
1. **List** - Show all entitlements using consumption data (last 90 days)
2. **Suspend** - Stop entitlement, billing ends TOMORROW
3. **Reactivate** - Restart entitlement, billing resumes TODAY
4. **Disable-config** - Prevent new entitlements, existing ones unchanged

### Important Notes
- ⚠️ Only shows devices that consumed points in last 90 days
- ⚠️ Devices in PENDING status won't appear
- ✅ Suspension still works even if device not found
- ✅ Always prompts for confirmation

### Billing Impact
| Action | Billing Stops | Billing Resumes | Reversible |
|--------|---------------|-----------------|------------|
| Suspend | Next day | - | ✅ Yes |
| Reactivate | - | Same day | ✅ Yes |
| Disable Config | N/A (affects new only) | N/A | ✅ Yes |

---

## 👥 Use Case 6: Multi-Tenant Operations

**File**: `use_case_6_multi_tenant_operations.py`
**Purpose**: View all customers and configurations
**Read-Only**: Yes ✅
**Safe to Run**: Yes

### Quick Start
```bash
# View all customers and configurations
python examples/use_case_6_multi_tenant_operations.py
```

### What It Does
- Lists all configurations across all customer accounts
- Groups by account ID
- Shows product types and status
- Helps find configuration IDs for other scripts

### Sample Output
```
================================================================================
CUSTOMER SUMMARY
================================================================================

Account ID      Configs    Product Types
--------------------------------------------------------------------------------
12345           24         FortiManager-VM(2), FortiGate-VM(10),
                          FortiGate-Hardware(4), FortiEDR-MSSP(1)

================================================================================
ACCOUNT ID: 12345
================================================================================

Config ID  Name                    Product                   Status
--------------------------------------------------------------------------------
41149      FMG-VM-04              FortiManager-VM           ACTIVE
42169      FortiPortal_lab1       FortiPortal-VM            ACTIVE
47456      Customer-A-FGT         FortiGate-VM              ACTIVE
```

### Use Cases
- ✅ Find configuration IDs
- ✅ Audit customer resources
- ✅ Inventory management
- ✅ Quick status overview

---

## 📊 Use Case 7: Program Balance Monitoring

**File**: `use_case_7_program_balance_monitoring.py`
**Purpose**: Monitor MSSP annual commitment (50,000 points/year)
**Read-Only**: Yes ✅
**Safe to Run**: Yes

### Quick Start
```bash
# Check current year commitment
python examples/use_case_7_program_balance_monitoring.py

# Check specific year
python examples/use_case_7_program_balance_monitoring.py --year 2024

# Custom trend analysis (last 60 days)
python examples/use_case_7_program_balance_monitoring.py --trends-days 60
```

### What It Does
1. **Program Info** - Identifies MSSP vs Prepaid program type
2. **Annual Commitment** - Tracks consumption vs 50,000 points/year minimum
3. **Trend Analysis** - Projects annual consumption based on recent usage

### Sample Output
```
================================================================================
MSSP ANNUAL COMMITMENT STATUS - 2025
================================================================================

[INFO] MSSP programs require minimum 50,000 points/year

Date Range: 2025-01-01 to 2025-11-09

Metric                         Value
-------------------------------------------------------
YTD Consumption                28,450.75 points
Days Elapsed                   313 days
Daily Average                  90.87 points
Projected Annual               33,167.55 points
Minimum Commitment             50,000.00 points

[WARNING] BELOW TARGET for annual commitment
          Projected shortfall: 16,832.45 points
          Need to increase consumption or true-up at year-end
```

### Use Cases
- ✅ Monthly commitment tracking
- ✅ Budget planning
- ✅ True-up forecasting
- ✅ Consumption trending

---

## 🔄 Common Workflows

### Workflow 1: New Customer Onboarding
```bash
# Step 1: Estimate costs
python examples/use_case_1_customer_onboarding.py --dry-run

# Step 2: Review output, edit serial numbers in script

# Step 3: Create resources
python examples/use_case_1_customer_onboarding.py

# Step 4: Verify in multi-tenant view
python examples/use_case_6_multi_tenant_operations.py
```

### Workflow 2: Customer Non-Payment Suspension
```bash
# Step 1: Find customer's config ID
python examples/use_case_6_multi_tenant_operations.py

# Step 2: List what will be suspended
python examples/use_case_5_entitlement_suspension_v2.py \
  --config-id 47456 --action list

# Step 3: Suspend all devices
python examples/use_case_5_entitlement_suspension_v2.py \
  --config-id 47456 --action suspend

# Step 4: Customer pays, reactivate
python examples/use_case_5_entitlement_suspension_v2.py \
  --config-id 47456 --action reactivate
```

### Workflow 3: Monthly Billing Report
```bash
# Generate last 30 days report
python examples/consumption_report_v2.py

# Output saved to: consumption_all_30days_YYYYMMDD_HHMMSS.json

# Import JSON into billing system
```

---

## ⚠️ Important Notes

### Before Running Scripts

1. **Always test authentication first**:
   ```bash
   python testing/test_authentication.py
   ```

2. **Use --dry-run when available**:
   ```bash
   python examples/use_case_1_customer_onboarding.py --dry-run
   ```

3. **Find config IDs first**:
   ```bash
   python examples/use_case_6_multi_tenant_operations.py
   ```

### Read-Only vs Write Operations

| Script | Read-Only | Safe to Run |
|--------|-----------|-------------|
| consumption_report_v2 | ✅ Yes | ✅ Safe |
| use_case_6 (multi-tenant) | ✅ Yes | ✅ Safe |
| use_case_7 (monitoring) | ✅ Yes | ✅ Safe |
| use_case_1 (onboarding) | ❌ No | ⚠️ Creates resources |
| use_case_2 (expansion) | ❌ No | ⚠️ Creates resources |
| use_case_3 (modification) | ❌ No | ⚠️ Modifies configs |
| use_case_5 (suspension) | ❌ No | ⚠️ Affects billing |

### Configuration IDs

All use cases except #1 require a **Configuration ID**. Find yours:
```bash
python examples/use_case_6_multi_tenant_operations.py
```

Output shows:
```
Config ID  Name                    Product
----------------------------------------
47456      Customer-A-FGT         FortiGate-VM
```

Use that Config ID in other scripts:
```bash
python examples/use_case_3_service_modification.py --config-id 47456
```

---

## 🐛 Troubleshooting

### "credentials.json not found"
```bash
# Make sure you're in the right directory
cd C:\path\to\fortiflex-mssp-toolkit

# Create credentials file
notepad testing\config\credentials.json
```

### "Authentication failed"
```bash
# Test credentials
python testing\test_authentication.py

# Verify program serial number
python testing\discover_program.py
```

### "Configuration not found"
```bash
# List all configs to find correct ID
python examples\use_case_6_multi_tenant_operations.py
```

### "No consumption data found"
This is normal if:
- Configuration was just created (no entitlements yet)
- Entitlements exist but haven't consumed points in 90 days
- Devices are in PENDING status (not activated)

---

## 📚 Additional Resources

- **[BUGFIX_USE_CASES.md](../BUGFIX_USE_CASES.md)** - Complete list of all patches applied
- **[PRODUCT_TYPE_REFERENCE.md](PRODUCT_TYPE_REFERENCE.md)** - Full FortiFlex product catalog
- **[CREDENTIALS_SETUP.md](../documentation/CREDENTIALS_SETUP.md)** - Detailed credential setup
- **[USE_CASES_GUIDE.md](../documentation/USE_CASES_GUIDE.md)** - Detailed use case documentation

---

## ✅ Pre-Demo Checklist

Before presenting to partners/customers:

- [ ] Credentials configured in `testing/config/credentials.json`
- [ ] Authentication tested: `python testing/test_authentication.py`
- [ ] Program discovered: `python testing/discover_program.py`
- [ ] Multi-tenant view works: `python examples/use_case_6_multi_tenant_operations.py`
- [ ] Consumption report works: `python examples/consumption_report_v2.py`
- [ ] Have example config IDs ready from use_case_6 output

---

**Last Tested**: November 9, 2025
**Status**: ✅ All examples working correctly
**Partner Demo Ready**: Yes
