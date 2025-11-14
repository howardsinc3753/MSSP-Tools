# FortiFlex Toolkit - Credentials Setup

## ⚠️ CRITICAL: Where to Put Your Credentials

**ALL scripts in this toolkit load credentials from ONE central file:**

```
testing/config/credentials.json
```

**Relative Path:**
```
fortiflex-mssp-toolkit/testing/config/credentials.json
```

---

## 📋 Understanding the Config Files

**You'll see TWO example files in `testing/config/`. Here's what they're for:**

| File | What It's For | Action Needed |
|------|---------------|---------------|
| **credentials.example.json** | ✅ Simple credentials template | **Copy this to `credentials.json` and edit** |
| **config.example.json** | 🔧 Advanced production config (database, SMTP, alerts) | **Ignore this - it's for advanced users** |

**Important:** You ONLY need `credentials.example.json` for basic usage!

The `config.example.json` file is for advanced production deployments with PostgreSQL databases, email alerts, and Slack notifications. Unless you're setting up enterprise infrastructure, you can completely ignore it.

---

## 📁 How It Works

```
fortiflex-mssp-toolkit/
├── testing/
│   ├── config/
│   │   └── credentials.json  ← PUT YOUR CREDENTIALS HERE!
│   ├── test_authentication.py  ← Loads from credentials.json
│   └── discover_program.py     ← Loads from credentials.json
│
├── examples/
│   ├── use_case_1_customer_onboarding.py  ← Loads from credentials.json
│   ├── use_case_2_service_expansion.py    ← Loads from credentials.json
│   ├── use_case_3_service_modification.py ← Loads from credentials.json
│   ├── use_case_4_daily_consumption.py    ← Loads from credentials.json
│   ├── use_case_5_customer_suspension.py  ← Loads from credentials.json
│   ├── use_case_6_multi_tenant_operations.py ← Loads from credentials.json
│   └── use_case_7_program_balance_monitoring.py ← Loads from credentials.json
│
└── src/
    └── fortiflex_client.py  ← Core library (no credentials needed)
```

**Key Points:**
- ✅ **Configure ONCE:** Edit `testing/config/credentials.json`
- ✅ **Use EVERYWHERE:** All scripts automatically load from this file
- ✅ **No script editing:** You never need to edit individual use case files
- ❌ **Don't commit:** This file is in `.gitignore` to protect your credentials

---

## 🔧 Setup Instructions

### Step 1: Open the Credentials File

**Option A - File Explorer:**
1. Navigate to: `testing\config\`
2. Right-click `credentials.json`
3. Select "Edit with Notepad"

**Option B - Command Line:**
```bash
notepad testing\config\credentials.json
```

### Step 2: Add Your Credentials

Replace the placeholder values with YOUR actual credentials:

```json
{
  "fortiflex": {
    "api_username": "217CD4CB-742D-439A-xxxxx-xxxxxxxxxx",  ← Your API username
    "api_password": "261284a4dbfad754cxxxxxxxxxxxxxxxx",  ← Your API password
    "client_id": "flexvm",                                    ← Leave as-is
    "program_serial_number": "ELAVMS00000xxxxx"               ← Auto-filled by discover_program.py
  }
}
```

**Where to get these values:**
- **api_username** and **api_password**: From FortiCloud IAM portal when you create an API user
- **client_id**: Always `"flexvm"` for FortiFlex operations (don't change)
- **program_serial_number**: Run `python testing\discover_program.py` to auto-fill this

### Step 3: Save the File

Press `Ctrl + S` to save and close Notepad.

### Step 4: Verify Setup

Run the discovery script to verify credentials and auto-fill your program serial number:

```bash
# Navigate to the toolkit directory
cd path/to/fortiflex-mssp-toolkit
python testing\discover_program.py
```

**Expected output:**
```
======================================================================
FORTIFLEX PROGRAM DISCOVERY
======================================================================

[1/2] Authenticating...
[SUCCESS] Authentication successful!

[2/2] Retrieving your programs...
[SUCCESS] Found 1 program(s)!

======================================================================
YOUR FORTIFLEX PROGRAMS
======================================================================

Program 1:
  Serial Number: ELAVMS000xxxxx
  Billing Type: MSSP POSTPAID (monthly billing, 50K points/year minimum)
  Start Date: 2025-08-07
  End Date: 2027-05-29
```

### Step 5: Test Authentication

```bash
python testing\test_authentication.py
```

**Expected output:**
```
======================================================================
TEST SUMMARY
======================================================================

[PASS] Authentication: PASSED
[PASS] API Connectivity: PASSED
[PASS] Program Access: PASSED
```

---

## ✅ You're Done!

Now all scripts will automatically use your credentials:

```bash
# All of these now work without editing individual files!
python examples\use_case_6_multi_tenant_operations.py
python examples\use_case_4_daily_consumption.py
python examples\use_case_7_program_balance_monitoring.py
```

---

## 🔒 Security Best Practices

**DO:**
- ✅ Keep `credentials.json` secure and private
- ✅ Use a strong API password
- ✅ Rotate credentials periodically
- ✅ Verify `.gitignore` includes `credentials.json`

**DON'T:**
- ❌ Commit `credentials.json` to GitHub
- ❌ Share `credentials.json` with anyone
- ❌ Email or Slack your credentials
- ❌ Store credentials in plain text elsewhere

---

## 🆘 Troubleshooting

### Error: "credentials.json not found!"

**Problem:** The file doesn't exist or is in the wrong location.

**Solution:**
```bash
# Verify the file exists:
dir testing\config\credentials.json

# If missing, check if there's a template:
dir testing\config\credentials.example.json
```

### Error: "400 Bad Request"

**Problem:** Invalid API credentials or wrong format.

**Solution:**
1. Double-check your API username and password
2. Verify no extra spaces in the JSON file
3. Ensure JSON syntax is valid (commas, quotes)

### Error: "401 Unauthorized"

**Problem:** API user doesn't have FortiFlex permissions.

**Solution:**
1. Log into FortiCloud IAM
2. Check your API user has "FortiFlex: ReadWrite" permission
3. Verify credentials are correct

---

## 📚 Additional Resources

- **[START_HERE.md](START_HERE.md)** - Complete onboarding guide
- **[GETTING_STARTED.md](GETTING_STARTED.md)** - Quick start for developers
- **[README.md](README.md)** - Main project documentation

---

**Last Updated:** November 9, 2025
