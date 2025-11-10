# FortiFlex MSSP Use Case Scripts - Complete Guide

**7 Production-Ready Scripts for FortiFlex MSSP Automation**

**Last Updated**: November 9, 2025
**Status**: ✅ All Scripts Tested and Working
**Bug Fixes Applied**: 5 critical patches (see [BUGFIX_USE_CASES.md](../BUGFIX_USE_CASES.md))

All scripts follow the same pattern:
- ✅ Use your existing `fortiflex_client.py` library
- ✅ Load credentials from `testing/config/credentials.json`
- ✅ Simple, well-documented code
- ✅ Error handling and confirmations
- ✅ Ready to run immediately
- ✅ **November 2025**: All compatibility issues resolved

---

## 🔧 Recent Updates (November 2025)

**All use case scripts have been updated and tested**:
- ✅ **Use Case 1** - Fixed points calculation response format handling
- ✅ **Use Case 3** - Added FortiGate VM (ID 1) support alongside Hardware (ID 101)
- ✅ **Use Case 5** - Replaced non-existent `list_entitlements()` with consumption-based approach
- ✅ **Use Case 7** - Removed `list_programs()` method, added account_id parameter
- ✅ **Consumption Report v2** - Primary tool for all billing/consumption reports

See [EXAMPLES_SUMMARY.md](../examples/EXAMPLES_SUMMARY.md) for complete testing report.

---

## 📋 Quick Reference

| Use Case | Script | When to Use | Modifies Data? |
|----------|--------|-------------|----------------|
| **1. Onboarding** | `use_case_1_customer_onboarding.py` | New customer setup | ✅ Yes |
| **2. Expansion** | `use_case_2_service_expansion.py` | Add more devices | ✅ Yes |
| **3. Modification** | `use_case_3_service_modification.py` | Change services | ✅ Yes |
| **4. Billing** | `use_case_4_daily_consumption.py` | Daily billing data | ❌ No (read-only) |
| **5. Suspension** | `use_case_5_customer_suspension.py` | Suspend/reactivate | ✅ Yes |
| **6. Multi-Tenant** | `use_case_6_multi_tenant_operations.py` | View all customers | ❌ No (read-only) |
| **7. Monitoring** | `use_case_7_program_balance_monitoring.py` | Track consumption | ❌ No (read-only) |

---

## 🚀 Prerequisites

### 1. Credentials Configured

Ensure your `testing/config/credentials.json` is set up:

```json
{
  "fortiflex": {
    "api_username": "YOUR_API_USERNAME",
    "api_password": "YOUR_API_PASSWORD",
    "program_serial_number": "ELAVMSXXXXXXXX",
    "account_id": YOUR_ACCOUNT_ID
  }
}
```

**Run this if not configured:**
```bash
python testing/discover_program.py
```

### 2. Dependencies Installed

```bash
pip install -r requirements.txt
```

### 3. Directory Structure

Scripts expect this structure:
```
your-project/
├── src/
│   └── fortiflex_client.py        # Your existing client library
├── testing/
│   └── config/
│       └── credentials.json        # Your credentials
└── examples/
    ├── use_case_1_customer_onboarding.py
    ├── use_case_2_service_expansion.py
    ├── use_case_3_service_modification.py
    ├── use_case_4_daily_consumption.py
    ├── use_case_5_customer_suspension.py
    ├── use_case_6_multi_tenant_operations.py
    └── use_case_7_program_balance_monitoring.py
```

---

## Use Case 1: Customer Onboarding

**Purpose:** Provision complete infrastructure for new customer

**What it does:**
1. Calculates estimated costs
2. Creates configurations for each product type
3. Creates hardware entitlements (FortiGate, FortiSwitch, FortiAP)
4. Creates cloud service entitlements (FortiEDR)
5. Generates onboarding summary

**Usage:**

```bash
# Dry run - calculate costs only
python examples/use_case_1_customer_onboarding.py --dry-run

# Full onboarding (with confirmation)
python examples/use_case_1_customer_onboarding.py
```

**Before Running:**
- Edit script to update customer profile (lines 80-160)
- Replace placeholder account_id with real FortiCloud account
- Replace placeholder serial numbers with real device serials

**Example Output:**
```
============================================================
STEP 1: COST ESTIMATION
============================================================

FGT-60F-UTP-FAZ:
  Quantity: 3
  Cost per device: 15.50 points/day
  Monthly total: 1,395.00 points

... (other products)

ESTIMATED MONTHLY TOTAL: 2,850.00 points
============================================================

Proceed with onboarding? (yes/no):
```

---

## Use Case 2: Service Expansion

**Purpose:** Add more devices to existing customer deployment

**What it does:**
1. Lists customer's existing configurations
2. Prompts for config ID to add devices to
3. Adds new hardware entitlements
4. Billing starts same day

**Usage:**

```bash
# Interactive mode (prompts for config ID and serials)
python examples/use_case_2_service_expansion.py

# With arguments
python examples/use_case_2_service_expansion.py \
  --config-id 12345 \
  --serials FGT60FTK20001237 FGT60FTK20001238
```

**Example Output:**
```
============================================================
CUSTOMER CONFIGURATIONS - Account ID: 12345
============================================================

Config ID  Name                          Product Type
-------------------------------------------------------------
12345      Acme-Corp-FGT-60F-UTP-FAZ     FortiGate Hardware

Enter Config ID to add devices to: 12345

About to add 2 device(s) to config 12345
Proceed? (yes/no): yes

[SUCCESS] Created 2 new entitlements
```

---

## Use Case 3: Service Modification

**Purpose:** Add or remove service addons (SOCaaS, FortiAnalyzer Cloud, etc.)

**What it does:**
1. Shows current configuration parameters
2. Calculates cost difference before/after
3. Updates configuration (affects ALL devices using it)

**⚠️ WARNING:** This affects ALL entitlements using the config!

**Usage:**

```bash
python examples/use_case_3_service_modification.py --config-id 12345
```

**Example Output:**
```
============================================================
CONFIGURATION DETAILS - ID: 12345
============================================================

Name: Acme-Corp-FGT-60F-UTP-FAZ
Product: FortiGate Hardware
Status: ACTIVE

Current Parameters:
  PRODUCTMODEL: FGT60F
  SERVICEPACK: FGHWUTP
  SERVICEPACK: FGHWFAZC

============================================================
COST COMPARISON
============================================================

Current Cost: 15.50 points/day per device
New Cost: 18.75 points/day per device
Difference: +3.25 points/day per device (+21.0%)

This will affect ALL devices using config 12345
Adding SOCaaS? (yes/no):
```

---

## Use Case 4: Daily Consumption Data Pull

**Purpose:** ⚠️ **CRITICAL FOR MSSP BILLING** - Pull daily consumption

**What it does:**
1. Pulls yesterday's point consumption
2. Stores data to file (simulate database)
3. Generates monthly summary reports
4. **Portal only keeps 3 months - YOU MUST RUN THIS DAILY!**

**Usage:**

```bash
# Daily consumption pull (run this DAILY at 6:00 AM!)
python examples/use_case_4_daily_consumption.py

# Generate monthly summary from stored data
python examples/use_case_4_daily_consumption.py \
  --monthly-summary --year 2025 --month 11
```

**Automated Scheduling:**

**Windows (Task Scheduler):**
1. Open Task Scheduler
2. Create Basic Task
3. Name: "FortiFlex Daily Consumption"
4. Trigger: Daily at 6:00 AM
5. Action: `python path\to\use_case_4_daily_consumption.py`

**Linux (cron):**
```bash
# Run daily at 6:00 AM PST
0 6 * * * cd /path/to/project && python examples/use_case_4_daily_consumption.py
```

**Example Output:**
```
============================================================
DAILY CONSUMPTION REPORT - 2025-11-08
============================================================

[SUCCESS] Retrieved consumption for 13 entitlement(s)

============================================================
CONSUMPTION SUMMARY
============================================================

Serial Number                  Points
--------------------------------------------
FMVMMLTMxxxxx582              107.20
FMVMMLTMxxxxx663               91.20
FGVMMLTMxxxxx993               21.66
...
--------------------------------------------
TOTAL                         399.42

[SUCCESS] Data stored to: ../data/consumption/consumption_2025-11-08.json

[REMINDER] Run this daily at 6:00 AM PST!
           Portal only keeps 3 months of history!
```

---

## Use Case 5: Customer Suspension/Offboarding

**Purpose:** Suspend or reactivate customer services

**What it does:**
1. Lists all customer entitlements
2. Suspends (stops) - billing stops next day
3. Reactivates (resumes) - billing resumes same day

**Usage:**

```bash
# List customer entitlements
python examples/use_case_5_customer_suspension.py \
  --account-id 12345 \
  --action list

# Suspend all customer devices
python examples/use_case_5_customer_suspension.py \
  --account-id 12345 \
  --action suspend

# Reactivate after payment received
python examples/use_case_5_customer_suspension.py \
  --account-id 12345 \
  --action reactivate
```

**Example Output:**
```
============================================================
CUSTOMER ENTITLEMENTS - Account ID: 12345
============================================================

Serial Number                  Status          Start Date
----------------------------------------------------------------
FGT60FTK20001234              ACTIVE          2025-01-15
FGT60FTK20001235              ACTIVE          2025-01-15
FGT60FTK20001236              ACTIVE          2025-01-15

About to suspend 3 entitlement(s)
Proceed with suspension? (yes/no): yes

============================================================
SUSPENSION SUMMARY
============================================================
Account ID: 12345
Suspended: 3
Status: [COMPLETE]
```

---

## Use Case 6: Multi-Tenant Operations View

**Purpose:** View all customers and configurations across program

**What it does:**
1. Lists all customer accounts
2. Shows configuration counts by customer
3. Optional: Consumption analysis across customers

**Usage:**

```bash
# View all customers
python examples/use_case_6_multi_tenant_operations.py

# View specific customer details
python examples/use_case_6_multi_tenant_operations.py --account-id 12345

# Include consumption analysis
python examples/use_case_6_multi_tenant_operations.py --consumption --days 7
```

**Example Output:**
```
============================================================
MULTI-TENANT OPERATIONS VIEW
============================================================

[SUCCESS] Found 25 configurations across 5 customer account(s)

============================================================
CUSTOMER SUMMARY
============================================================

Account ID      Configs    Product Types
----------------------------------------------------------------------------
12345           5          FortiGate Hardware(3), FortiSwitch(2)
67890           3          FortiGate Hardware(2), FortiEDR(1)
11111           4          FortiGate Hardware(1), FortiAP(3)
...

============================================================
CROSS-CUSTOMER CONSUMPTION - LAST 7 DAYS
============================================================

Account ID      Devices    Total Points    Avg/Day
------------------------------------------------------------
12345           8          1,250.50        178.64
67890           5            875.20        125.03
...
```

---

## Use Case 7: Program Balance Monitoring

**Purpose:** Track consumption vs. commitments

**What it does:**
1. Checks program type (prepaid vs MSSP postpaid)
2. For prepaid: Shows point balance
3. For MSSP: Tracks vs. 50,000 points/year minimum
4. Analyzes consumption trends

**Usage:**

```bash
# Monitor current year
python examples/use_case_7_program_balance_monitoring.py

# Check specific year (for past years)
python examples/use_case_7_program_balance_monitoring.py --year 2024

# Custom trend analysis period
python examples/use_case_7_program_balance_monitoring.py --trends-days 90
```

**Example Output:**
```
============================================================
PROGRAM INFORMATION
============================================================

Serial Number: ELAVMS0000XXXXXX
Start Date: 2025-08-07T00:00:00
End Date: 2027-05-29T00:00:00
Program Type: MSSP (Postpaid)

============================================================
MSSP ANNUAL COMMITMENT STATUS - 2025
============================================================

[INFO] MSSP programs require minimum 50,000 points/year

Metric                         Value
-------------------------------------------------------
YTD Consumption              28,450.75 points
Days Elapsed                       312 days
Daily Average                    91.19 points
Projected Annual              33,284.35 points
Minimum Commitment            50,000.00 points

[WARNING] BELOW TARGET for annual commitment
          Projected shortfall: 16,715.65 points
          Need to increase consumption or true-up at year-end

============================================================
CONSUMPTION TRENDS - LAST 30 DAYS
============================================================

Period: 30 days (2025-10-10 to 2025-11-09)

Total Consumption: 2,735.70 points
Active Devices: 13
Daily Average: 91.19 points/day
Projected Monthly: 2,735.70 points
Projected Annual: 33,284.35 points
```

---

## 🔄 Typical Workflows

### New Customer Setup

```bash
# 1. Onboard customer
python examples/use_case_1_customer_onboarding.py

# 2. Verify in multi-tenant view
python examples/use_case_6_multi_tenant_operations.py
```

### Monthly Billing Cycle

```bash
# Daily (automated via cron/Task Scheduler)
python examples/use_case_4_daily_consumption.py

# End of month
python examples/use_case_4_daily_consumption.py \
  --monthly-summary --year 2025 --month 11

# Check program status
python examples/use_case_7_program_balance_monitoring.py
```

### Customer Expansion

```bash
# 1. Add new devices
python examples/use_case_2_service_expansion.py --config-id 12345

# 2. Or upgrade services
python examples/use_case_3_service_modification.py --config-id 12345
```

### Non-Payment Handling

```bash
# 1. Suspend services
python examples/use_case_5_customer_suspension.py \
  --account-id 12345 --action suspend

# 2. After payment, reactivate
python examples/use_case_5_customer_suspension.py \
  --account-id 12345 --action reactivate
```

---

## ⚠️ Important Notes

### Security
- ✅ Credentials file contains sensitive passwords
- ✅ Never commit `credentials.json` to Git
- ✅ Add to `.gitignore`: `testing/config/credentials.json`

### Data Retention
- ⚠️ **CRITICAL:** Portal only keeps 3 months of consumption history
- ⚠️ **MUST** run Use Case 4 daily to store data
- ⚠️ Recommend database storage for production

### Production Readiness
- ✅ All scripts have error handling
- ✅ Confirmation prompts for destructive operations
- ✅ Dry-run modes where appropriate
- ⚠️ Replace placeholder data before production use

### Placeholder Values
Before production use, replace these in Use Case 1:
- `'account_id': 12345` → Real FortiCloud account ID
- `serial_numbers: ["FGT60FTK20001234"]` → Real device serials

---

## 📊 Script Sizes

| Script | Size | Complexity | Runtime |
|--------|------|------------|---------|
| Use Case 1 | 15KB | High | 2-5 min |
| Use Case 2 | 7KB | Low | 30 sec |
| Use Case 3 | 8KB | Medium | 1 min |
| Use Case 4 | 10KB | Low | 15 sec |
| Use Case 5 | 8KB | Low | 30 sec |
| Use Case 6 | 9KB | Low | 30 sec |
| Use Case 7 | 11KB | Medium | 1 min |

---

## 🐛 Troubleshooting

### "credentials.json not found"
```bash
python testing/discover_program.py
```

### "Authentication failed"
Check credentials in `testing/config/credentials.json`

### "No such module: fortiflex_client"
Ensure you're running from project root and `src/fortiflex_client.py` exists

### "account_id not found"
Add to credentials.json or run discovery script

---

## 📚 Next Steps

1. **Test with dry runs first**
2. **Set up daily consumption collection** (Use Case 4)
3. **Automate with cron/Task Scheduler**
4. **Store consumption data in database**
5. **Integrate with PSA/CRM system**
6. **Build operations dashboard**

---

## 🎓 Learning Path

**Beginner:**
- Start with Use Case 6 (Multi-Tenant View - read-only)
- Try Use Case 7 (Program Monitoring - read-only)
- Practice Use Case 4 (Daily Consumption - read-only)

**Intermediate:**
- Use Case 2 (Service Expansion - safe additions)
- Use Case 5 (Suspension - reversible)

**Advanced:**
- Use Case 1 (Onboarding - complete workflow)
- Use Case 3 (Modification - affects all devices)

---

**All scripts are production-ready and follow your existing code patterns!** 🚀

For questions or issues, refer to the main project documentation or FortiFlex API docs at https://docs.fortinet.com/document/fortiflex/
