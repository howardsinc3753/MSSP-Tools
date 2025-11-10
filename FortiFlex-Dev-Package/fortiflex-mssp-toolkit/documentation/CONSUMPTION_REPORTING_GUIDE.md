# FortiFlex Consumption Reporting - Partner Walkthrough

**Last Updated**: November 9, 2025
**Purpose**: Guide partners through pulling consumption reports for FortiFlex entitlements

---

## Overview

The consumption reporting feature allows you to:
- View point consumption for **all active entitlements** or **specific devices**
- Pull historical data for any date range (1 day, 7 days, 30 days, custom)
- Export data to JSON for further analysis
- Track daily/monthly/annual consumption trends

**Key Concept**: The consumption API only returns data for entitlements that are:
1. ✅ **ACTIVE** status (not PENDING)
2. ✅ **Checked in** with FortiCloud
3. ✅ **Consuming points** (deployed and running)

---

## Prerequisites

### 1. Credentials Must Be Configured

Your `testing/config/credentials.json` must have these fields:

```json
{
  "fortiflex": {
    "api_username": "YOUR_USERNAME",
    "api_password": "YOUR_PASSWORD",
    "program_serial_number": "ELAVMS0000xxxxx",
    "account_id": 232xxxx
  }
}
```

**Important**: The `account_id` field is **REQUIRED** for consumption reporting. If you don't have it:

```bash
# Run discovery to find your account ID
python testing\discover_program.py
```

### 2. Navigate to Toolkit Directory

```bash
cd C:\Users\howar\Documents\Projects\MSSP-SE-Tools\FortiFlex-Dev-Package\fortiflex-mssp-toolkit
```

---

## Report Types

### Report Type 1: All Entitlements (Recommended for Monthly Reports)

**Use Case**: Get consumption for all active devices in your program

**Command**:
```bash
python examples\consumption_report_v2.py --days 7
```

**What This Does**:
- Retrieves consumption for **ALL entitlements** consuming points
- Date range: Last 7 days from today
- Sorted by highest consumption first
- Shows grand total across all devices

**Example Output**:
```
================================================================================
CONSUMPTION REPORT - ALL ENTITLEMENTS - LAST 7 DAYS
================================================================================

Date Range: 2025-11-02 to 2025-11-09
Account ID: YOUR_ACCOUNT_ID

Retrieving consumption data...

[SUCCESS] Retrieved consumption data for 13 entitlement(s)

================================================================================
CONSUMPTION SUMMARY
================================================================================

Serial Number             Config ID    Account ID      Total Points
--------------------------------------------------------------------------------
FMVMMLTMxxxxx582          N/A          YOUR_ACCOUNT_ID               750.40
FMVMMLTMxxxxx663          N/A          YOUR_ACCOUNT_ID               638.40
FGVMMLTMxxxxx993          N/A          YOUR_ACCOUNT_ID               151.62
FGVMMLTMxxxxx994          N/A          YOUR_ACCOUNT_ID               151.62
FGVMMLTMxxxxx995          N/A          YOUR_ACCOUNT_ID               151.62
FGVMMLTMxxxxx996          N/A          YOUR_ACCOUNT_ID               151.62
FGVMMLTMxxxxx997          N/A          YOUR_ACCOUNT_ID               151.62
FGVMMLTMxxxxx998          N/A          YOUR_ACCOUNT_ID               151.62
FGVMMLTMxxxxx999          N/A          YOUR_ACCOUNT_ID               151.62
FGT71FTK2xxxxx          N/A          YOUR_ACCOUNT_ID               135.03
FEMSPO88xxxxx387          N/A          YOUR_ACCOUNT_ID                98.07
FZVMMLTMxxxxx689          N/A          YOUR_ACCOUNT_ID                89.95
FEMSPO88xxxxx320          N/A          YOUR_ACCOUNT_ID                22.75
--------------------------------------------------------------------------------
GRAND TOTAL                                                 2795.94

================================================================================

[SUCCESS] Report saved to: consumption_all_7days_20251109_140600.json
```

**Key Metrics**:
- **13 active entitlements** consuming points
- **2,795.94 total points** in 7 days
- **~399.42 points/day** average consumption

---

### Report Type 2: Specific Device

**Use Case**: Track consumption for a single customer device

**Command**:
```bash
python examples\consumption_report_v2.py --serial FGT71FTK2xxxxx --days 7
```

**What This Does**:
- Filters to **ONE specific serial number**
- Shows only that device's consumption
- Useful for customer-specific billing/troubleshooting

**Example Output**:
```
================================================================================
CONSUMPTION REPORT - FGT71FTK2xxxxx - LAST 7 DAYS
================================================================================

Date Range: 2025-11-02 to 2025-11-09
Account ID: YOUR_ACCOUNT_ID
Serial Number Filter: FGT71FTK2xxxxx

Retrieving consumption data...

[SUCCESS] Retrieved consumption data for 1 entitlement(s)

================================================================================
CONSUMPTION SUMMARY
================================================================================

Serial Number             Config ID    Account ID      Total Points
--------------------------------------------------------------------------------
FGT71FTK2xxxxx          N/A          YOUR_ACCOUNT_ID               135.03
--------------------------------------------------------------------------------
GRAND TOTAL                                                  135.03

================================================================================

[SUCCESS] Report saved to: consumption_FGT71FTK2xxxxx_7days_20251109_140046.json
```

**Key Metrics**:
- **135.03 points** in 7 days
- **~19.29 points/day** for this device
- **~578.70 points/month** projected

---

## Common Report Scenarios

### Scenario 1: Daily Report (Last 24 Hours)

```bash
python examples\consumption_report_v2.py --days 1
```

**Use Case**: Quick daily check on active consumption

---

### Scenario 2: Monthly Report (Last 30 Days)

```bash
python examples\consumption_report_v2.py --days 30
```

**Use Case**: Monthly billing reconciliation, matches most accounting cycles

---

### Scenario 3: Annual Projection

```bash
python examples\consumption_report_v2.py --days 365
```

**Use Case**: Year-end analysis, budget planning for next year

---

### Scenario 4: Custom Date Range

For custom ranges, you can modify the `--days` parameter:

```bash
# Last 14 days (bi-weekly)
python examples\consumption_report_v2.py --days 14

# Last 90 days (quarterly)
python examples\consumption_report_v2.py --days 90
```

---

## Understanding the Output

### Console Output

The script prints a formatted report to the console showing:

1. **Header**: Date range, account ID, filter info
2. **Summary Table**: All entitlements sorted by consumption
3. **Grand Total**: Sum of all points consumed
4. **File Location**: Where the JSON report was saved

### JSON Output File

Each report generates a JSON file with complete data:

**Filename Format**: `consumption_{serial}_{days}days_{timestamp}.json`

**Examples**:
- `consumption_all_7days_20251109_140600.json` (all devices)
- `consumption_FGT71FTK2xxxxx_7days_20251109_140046.json` (single device)

**JSON Structure**:
```json
{
  "generated_at": "2025-11-09T14:00:46.678828",
  "days_back": 7,
  "serial_filter": null,
  "program_serial": "ELAVMS0000XXXXXX",
  "consumption": {
    "entitlements": [
      {
        "points": 750.40,
        "serialNumber": "FMVMMLTMxxxxx582",
        "accountId": YOUR_ACCOUNT_ID
      }
    ],
    "error": null,
    "message": "Request processed successfully.",
    "status": 0
  }
}
```

---

## Troubleshooting

### Issue 1: "No consumption data found"

**Message**:
```
[INFO] API 200 OK but no consumption for 2025-11-02 to 2025-11-09.
       This means entitlements exist but have not consumed any points yet.
```

**Possible Reasons**:
1. Entitlements are in **PENDING** status (not activated yet)
2. Devices haven't **checked in** with FortiCloud
3. Devices are powered off or not consuming services
4. Date range is before devices were activated

**Solution**:
- Check FortiFlex portal to verify entitlement status
- Ensure devices are powered on and connected
- Try a longer date range (e.g., `--days 30`)
- Verify the serial number is correct (if filtering)

---

### Issue 2: Missing account_id Error

**Message**:
```
[ERROR] Missing required field 'account_id' in credentials.json
```

**Solution**:
```bash
# Run discovery to get your account ID
python testing\discover_program.py

# Or manually add to credentials.json:
{
  "fortiflex": {
    ...
    "account_id": YOUR_ACCOUNT_ID
  }
}
```

---

### Issue 3: Serial Number Not Found

**Message**:
```
[INFO] No consumption data found for serial number: FGT71FTK2xxxxx
       Either this device hasn't consumed points, or the serial number is incorrect.
```

**Solution**:
- Run without `--serial` filter to see all active devices
- Check FortiFlex portal for correct serial number
- Verify device is ACTIVE (not PENDING or STOPPED)

---

## Best Practices for Partners

### 1. Regular Reporting Schedule

**Recommended**:
- **Daily**: Run `--days 1` to monitor new activations
- **Weekly**: Run `--days 7` for weekly status updates
- **Monthly**: Run `--days 30` for billing reconciliation

### 2. Archive Reports

Save JSON files for historical tracking:

```bash
# Create reports directory
mkdir reports

# Move reports to archive
move consumption_*.json reports\
```

### 3. Compare with FortiFlex GUI

**Validation Steps**:
1. Run consumption report via script
2. Log into FortiFlex portal: https://support.fortinet.com/flexvm/
3. Navigate to **Program > Consumption**
4. Verify numbers match between script and GUI

**Example**:
- Script shows: `FGT71FTK2xxxxx - 135.03 points (7 days)`
- GUI should show: `~19.29 points/day` for that device

### 4. Monitor Top Consumers

Identify devices consuming the most points:

```bash
# The script automatically sorts by highest consumption
python examples\consumption_report_v2.py --days 30
```

Look at the top 3-5 devices - these drive most of your costs.

---

## Understanding Point Consumption

### What Affects Point Consumption?

**FortiGate VM**:
- CPU cores (2, 4, 8, 16, etc.)
- Bundle type (ATP, UTP, ENT)
- VDOMs (virtual domains)
- Additional services (FortiGuard, FortiCare)

**FortiManager/FortiAnalyzer VM**:
- Managed devices count
- Storage capacity
- Additional features (FortiGuard, SOC)

### Example Consumption Rates (from your data)

| Device | Type | Daily Points | Monthly (30d) | Annual (365d) |
|--------|------|--------------|---------------|---------------|
| FMVMMLTMxxxxx582 | FortiManager VM | 107.20 | 3,216 | 39,128 |
| FMVMMLTMxxxxx663 | FortiManager VM | 91.20 | 2,736 | 33,288 |
| FGVMMLTMxxxxx993 | FortiGate VM | 21.66 | 650 | 7,906 |
| FGT71FTK2xxxxx | FortiGate HW | 19.29 | 579 | 7,041 |
| FEMSPO88xxxxx320 | FortiEMS | 3.25 | 97.5 | 1,186 |

**Total Program**: ~399.42 points/day = ~11,982 points/month = ~145,788 points/year

---

## Partner Demo Script

Use this script when walking through with partners:

### Step 1: Show All Active Devices

```bash
python examples\consumption_report_v2.py --days 7
```

**Say**: "This shows all 13 devices currently consuming points in your program. The grand total is 2,795.94 points over the last 7 days."

### Step 2: Show Specific Device Detail

```bash
python examples\consumption_report_v2.py --serial FMVMMLTMxxxxx582 --days 7
```

**Say**: "Here's your top consumer - FortiManager VM consuming 750.40 points in 7 days. That's about 107 points per day."

### Step 3: Show Monthly Projection

```bash
python examples\consumption_report_v2.py --days 30
```

**Say**: "Looking at the last 30 days, we can project your monthly consumption and compare it to your 50,000 annual commitment (4,166 points/month average)."

### Step 4: Show JSON Export

```bash
notepad consumption_all_7days_{timestamp}.json
```

**Say**: "All data is saved to JSON files that you can import into Excel, your billing system, or use for automated reporting."

---

## Integration with Billing Systems

The JSON output can be easily integrated:

### Excel/CSV Import

```python
# Example: Convert JSON to CSV
import json
import csv

with open('consumption_all_7days_20251109_140600.json', 'r') as f:
    data = json.load(f)

with open('consumption_report.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Serial Number', 'Points', 'Account ID'])

    for ent in data['consumption']['entitlements']:
        writer.writerow([
            ent['serialNumber'],
            ent['points'],
            ent['accountId']
        ])
```

### Automated Reporting

You can schedule the script to run automatically:

**Windows Task Scheduler**:
```bash
# Create a batch file: daily_report.bat
cd C:\Users\howar\Documents\Projects\MSSP-SE-Tools\FortiFlex-Dev-Package\fortiflex-mssp-toolkit
python examples\consumption_report_v2.py --days 1 > logs\daily_%date%.log
```

Schedule to run daily at 8:00 AM.

---

## API Details (For Technical Partners)

### Endpoint
```
POST /entitlements/points
```

### Required Fields
- `programSerialNumber`: Your FortiFlex program ID
- `accountId`: Your account ID (REQUIRED as of Nov 2025)
- `startDate`: YYYY-MM-DD format
- `endDate`: YYYY-MM-DD format

### Optional Fields
- `serialNumber`: Filter to specific device
- `configId`: Filter by configuration template

### Response Structure
```json
{
  "entitlements": [
    {
      "points": 135.03,
      "serialNumber": "FGT71FTK2xxxxx",
      "accountId": YOUR_ACCOUNT_ID
    }
  ],
  "status": 0,
  "error": null,
  "message": "Request processed successfully."
}
```

---

## Quick Reference

| Task | Command |
|------|---------|
| All devices, last 7 days | `python examples\consumption_report_v2.py --days 7` |
| Single device, last 7 days | `python examples\consumption_report_v2.py --serial SERIAL --days 7` |
| Daily report (last 24h) | `python examples\consumption_report_v2.py --days 1` |
| Monthly report (30 days) | `python examples\consumption_report_v2.py --days 30` |
| List configurations | `python examples\consumption_report_v2.py --list-configs` |

---

## Support

**Documentation**:
- [Getting Started](GETTING_STARTED.md)
- [Credentials Setup](CREDENTIALS_SETUP.md)
- [Testing Guide](documentation/TESTING_GUIDE.md)

**Issues**:
- Check credentials: `testing/config/credentials.json`
- Verify program access: `python testing\discover_program.py`
- Test authentication: `python testing\test_authentication.py`

---

**Questions?** Contact your FortiFlex representative or refer to the [FortiFlex API Documentation](https://docs.fortinet.com/document/fortiflex/latest/api-guide/983945/introduction).
