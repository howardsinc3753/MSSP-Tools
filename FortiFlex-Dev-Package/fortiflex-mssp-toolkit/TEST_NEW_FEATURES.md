# Testing Guide - New Export Features

## Quick Test Checklist

Run these tests in order to verify all new features:

### ✅ Test 1: Basic Functionality (No New Dependencies)
**Purpose:** Verify script still works without optional packages

```bash
cd C:\Users\howar\Documents\Projects\MSSP-SE-Tools\FortiFlex-Dev-Package\fortiflex-mssp-toolkit

# Should work with just 'requests' library
python examples\consumption_report_v2.py --days 7
```

**Expected:**
- Console output showing consumption data
- JSON file created: `consumption_all_7days_YYYYMMDD_HHMMSS.json`

**If Error:** Check credentials.json has `account_id` field

---

### ✅ Test 2: Excel Export
**Purpose:** Verify Excel workbook generation

```bash
# Install dependencies if not already installed
pip install openpyxl pandas

# Run with Excel output
python examples\consumption_report_v2.py --days 7 --output excel
```

**Expected Output:**
```
[SUCCESS] Excel report saved to: consumption_all_7days_YYYYMMDD_HHMMSS.xlsx
```

**Verification Steps:**
1. Open the .xlsx file in Excel
2. Check **Sheet 1 (Summary)**:
   - Blue header row with white text
   - Device serial numbers in column A
   - Account IDs in column B
   - Total points in column C
   - Days in column D
   - GRAND TOTAL row at bottom
3. Check **Sheet 2 (Daily Details)**:
   - Daily breakdown for each device
   - Columns: Serial Number, Date, Points, Account ID

**If Error "Excel export requires: pip install openpyxl pandas":**
- Run: `pip install openpyxl pandas`

---

### ✅ Test 3: CSV Export
**Purpose:** Verify CSV file generation

```bash
python examples\consumption_report_v2.py --days 7 --output csv
```

**Expected Output:**
```
[SUCCESS] CSV report saved to: consumption_all_7days_YYYYMMDD_HHMMSS.csv
```

**Verification Steps:**
1. Open the .csv file in Excel or text editor
2. Should have columns: Serial Number, Account ID, Date, Points, Total Points
3. Each device should have multiple rows (one per day)

---

### ✅ Test 4: Specific Device Export
**Purpose:** Test filtering by serial number

```bash
# Replace FMVMMLTMXXXXXX with actual serial from your account
python examples\consumption_report_v2.py --serial FMVMMLTMXXXXXX --days 7 --output excel
```

**Expected:**
- Excel file with only that specific device's data
- Filename includes serial number

---

### ✅ Test 5: Database Integration (Advanced)
**Purpose:** Test PostgreSQL integration

**Prerequisites:**
```bash
# Install PostgreSQL adapter
pip install psycopg2-binary

# Verify PostgreSQL is installed and running
psql --version
```

**Setup Database:**
```bash
# Create database (Windows command prompt)
psql -U postgres -c "CREATE DATABASE fortiflex;"

# Create schema
psql -U postgres -d fortiflex -f database\schema.sql
```

**Configure credentials.json:**
Add this section to your credentials.json:
```json
{
  "fortiflex": {
    ...existing fields...
  },
  "database": {
    "host": "localhost",
    "port": 5432,
    "database": "fortiflex",
    "username": "postgres",
    "password": "YOUR_POSTGRES_PASSWORD"
  }
}
```

**Run Test:**
```bash
python examples\consumption_report_v2.py --days 1 --save-to-db
```

**Expected Output:**
```
[INFO] Saving to database...
[SUCCESS] Saved XX records to database
```

**Verify Database:**
```bash
psql -U postgres -d fortiflex

-- Check records were inserted
SELECT COUNT(*) FROM consumption_daily;

-- View recent records
SELECT serial_number, date, points FROM consumption_daily ORDER BY date DESC LIMIT 10;

-- Exit psql
\q
```

---

## 🐛 Troubleshooting

### Error: "No module named 'openpyxl'"
```bash
pip install openpyxl pandas
```

### Error: "No module named 'pandas'"
```bash
pip install pandas
```

### Error: "No module named 'psycopg2'"
```bash
pip install psycopg2-binary
```

### Error: "ModuleNotFoundError: No module named 'requests'"
```bash
pip install requests
```

### Error: "Missing required field 'account_id' in credentials.json"
**Fix:** Add account_id to your credentials.json:
```json
{
  "fortiflex": {
    "api_username": "YOUR_USERNAME",
    "api_password": "YOUR_PASSWORD",
    "client_id": "flexvm",
    "program_serial_number": "ELAVMSXXXXXXXX",
    "account_id": 12345
  }
}
```

Find your account_id by running:
```bash
python testing\discover_program.py
```

### Database Error: "could not connect to server"
**Fix:**
1. Check PostgreSQL is running: `pg_ctl status`
2. Start if needed: `pg_ctl start`
3. Verify port 5432 is open

### Database Error: "database 'fortiflex' does not exist"
**Fix:**
```bash
psql -U postgres -c "CREATE DATABASE fortiflex;"
psql -U postgres -d fortiflex -f database\schema.sql
```

---

## 📊 What Each Test Validates

| Test | Feature | Pass Criteria |
|------|---------|---------------|
| Test 1 | Basic JSON export | File created, console output correct |
| Test 2 | Excel workbook | .xlsx file with 2 sheets, formatted headers |
| Test 3 | CSV export | .csv file with proper columns |
| Test 4 | Serial filtering | Filtered data in output |
| Test 5 | Database save | Records in PostgreSQL |

---

## ✅ Success Indicators

**All tests passed if:**
1. ✅ JSON file created (Test 1)
2. ✅ Excel file opens with 2 formatted sheets (Test 2)
3. ✅ CSV file has correct columns (Test 3)
4. ✅ Filtered export works (Test 4)
5. ✅ Database has records (Test 5)

---

## 🎯 Real-World Usage Examples

### Monthly Billing Report for Finance
```bash
# Export last 30 days to Excel for billing team
python examples\consumption_report_v2.py --days 30 --output excel
```

### Daily Database Backup (Scheduled Task)
```bash
# Run this daily at 8 AM via Windows Task Scheduler
python examples\consumption_report_v2.py --days 1 --save-to-db --output json
```

### Weekly CSV for Data Analysis
```bash
# Export to CSV for import into Tableau/PowerBI
python examples\consumption_report_v2.py --days 7 --output csv
```

### Customer-Specific Report
```bash
# Generate Excel report for specific customer device
python examples\consumption_report_v2.py --serial FMVMMLTM12345 --days 30 --output excel
```

---

## 📝 Test Results Template

Copy this and fill in your results:

```
Test Date: ___________
Tester: ___________

Test 1 (JSON): [ ] PASS [ ] FAIL
  - File created: [ ] Yes [ ] No
  - Console output: [ ] Correct [ ] Issues
  - Notes: _______________________________

Test 2 (Excel): [ ] PASS [ ] FAIL
  - File created: [ ] Yes [ ] No
  - Sheet 1 formatted: [ ] Yes [ ] No
  - Sheet 2 has data: [ ] Yes [ ] No
  - Notes: _______________________________

Test 3 (CSV): [ ] PASS [ ] FAIL
  - File created: [ ] Yes [ ] No
  - Columns correct: [ ] Yes [ ] No
  - Notes: _______________________________

Test 4 (Filter): [ ] PASS [ ] FAIL
  - Filtered correctly: [ ] Yes [ ] No
  - Notes: _______________________________

Test 5 (Database): [ ] PASS [ ] FAIL [ ] SKIPPED
  - Records saved: [ ] Yes [ ] No
  - Count matches: [ ] Yes [ ] No
  - Notes: _______________________________

Overall Result: [ ] ALL PASS [ ] SOME FAILED
```

---

**Need Help?** Open an issue: https://github.com/howardsinc3753/MSSP-Tools/issues
