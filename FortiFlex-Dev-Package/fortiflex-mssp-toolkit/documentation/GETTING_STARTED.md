# Getting Started - FortiFlex MSSP Toolkit

**Welcome!** This guide walks you through using the FortiFlex MSSP Toolkit from scratch.

---

## 📋 Before You Start - Understanding Config Files

**You'll see TWO example files in `testing/config/`. Here's what they're for:**

| File | Purpose | Do You Need It? |
|------|---------|-----------------|
| **credentials.example.json** | ✅ Simple template for API credentials | **YES - Use this one!** |
| **config.example.json** | 🔧 Advanced config (database, alerts, SMTP) | **NO - Ignore for now** |

**For this guide, you ONLY need `credentials.example.json`!**

The advanced `config.example.json` is for future production deployments with databases and alerting. You can ignore it completely for now.

---

## What You're About to Do

You're going to:
1. Configure your API credentials **(5 minutes)**
2. Install Python dependencies **(optional - 2 minutes)**
3. Discover your FortiFlex programs automatically **(2 minutes)**
4. Test API connectivity **(1 minute)**
5. Run your first automation **(1 minute)**

**Total Time:** 10-15 minutes

---

## Step 1: Configure Your API Credentials

**IMPORTANT:** This is the most critical step! All scripts load credentials from ONE central location.

### **Credential File Location:**
```
testing/config/credentials.json
```

**Relative Path:**
```
fortiflex-mssp-toolkit/testing/config/credentials.json
```

### **How to Configure:**

1. **Open the credentials file:**
   - Navigate to: `testing/config/credentials.json`
   - Right-click → "Edit with Notepad"

2. **Update with YOUR API credentials:**

```json
{
  "fortiflex": {
    "api_username": "YOUR_API_USERNAME_HERE",
    "api_password": "YOUR_API_PASSWORD_HERE",
    "client_id": "flexvm",
    "program_serial_number": "ELAVMSXXXXXXXX"
  }
}
```

**Replace:**
- `YOUR_API_USERNAME_HERE` → Your actual FortiCloud IAM API username (looks like: `217CD4CB-742D-439A-B907-460AF16D894C`)
- `YOUR_API_PASSWORD_HERE` → Your actual FortiCloud IAM API password
- Leave `client_id` as `"flexvm"` (don't change this!)
- Leave `program_serial_number` as is for now (we'll auto-fill this in Step 3)

3. **Save the file:** Press `Ctrl + S`

**Security Note:** Never commit this file to GitHub! It contains your passwords!

---

## Step 2: Install Dependencies (Optional)

**Do I need this step?**

✅ **Probably NO** - If you already have Python and pip installed, you likely already have the required `requests` library.

❓ **Try skipping to Step 3.** If you get a `ModuleNotFoundError`, come back and run this step.

**To install dependencies:**

Open Command Prompt or PowerShell and run:

```bash
# Navigate to the toolkit directory
cd path/to/fortiflex-mssp-toolkit

pip install -r requirements.txt
```

**Expected Output:**
```
Successfully installed requests-2.31.0 urllib3-2.0.0
```

**What this installs:**
- `requests` - For making API calls (required)
- `urllib3` - HTTP library (usually already installed)
- `psycopg2-binary` - PostgreSQL database support (optional)
- Testing tools (optional)

**Most users already have `requests` installed**, so this step often isn't necessary!

---

## Step 3: Discover Your Programs

The toolkit can automatically find your FortiFlex program serial number. Run:

```bash
python testing\discover_program.py
```

**What This Does:**
1. Reads your API credentials from `testing/config/credentials.json`
2. Authenticates with FortiFlex API
3. Lists ALL FortiFlex programs in your account
4. Shows program serial numbers, billing types, and dates
5. Automatically updates `testing/config/credentials.json` with your program serial number

**Example Output:**
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
  Serial Number: ELAVMS1234567890
  Program Type: MSSP
  Start Date: 2025-01-01
  End Date: 2026-01-01
  Type: MSSP (Postpaid) Program

======================================================================
UPDATE CREDENTIALS FILE
======================================================================

Would you like to update your credentials.json with:
  Program SN: ELAVMS1234567890
  Program Type: MSSP

Update credentials.json? (y/n):
```

**Answer:** Type `y` and press Enter

---

## Step 4: Test Authentication

Now verify everything works:

```bash
python testing\test_authentication.py
```

**Expected Output:**
```
======================================================================
FORTIFLEX MSSP TOOLKIT - AUTHENTICATION TEST
======================================================================

======================================================================
TEST 1: OAuth Authentication
======================================================================

Attempting authentication...
Username: 217CD4CB-742D-439A-B907-460AF16D894C
Client ID: flexvm

[SUCCESS] Authentication successful!
Token (first 20 chars): 0yeCpSz4pHatZdnfM70o...
Token length: 30 characters

======================================================================
TEST 2: Program Information
======================================================================

Program Serial Number: ELAVMS1234567890
Attempting to list configurations...

[SUCCESS] Retrieved program information
Total Configurations: 5

Sample Configuration:
  ID: 12345
  Name: Customer-A-FGT60F
  Product Type: FortiGate Hardware
  Status: ACTIVE

======================================================================
TEST 3: Multi-Tenant View
======================================================================

Retrieving multi-tenant view...

[SUCCESS] Retrieved multi-tenant data
Total Accounts: 2

  Account 10001:
    Configurations: 3
      - FortiGate Hardware: 2
      - FortiSwitch Hardware: 1

======================================================================
TEST SUMMARY
======================================================================

[PASS] Authentication: PASSED
[PASS] API Connectivity: PASSED
[PASS] Program Access: PASSED

You can now proceed to test the use case examples!
======================================================================
```

✅ **Success!** If you see this, you're ready to go!

---

## Step 5: Run Your First Automation

Let's try a **safe** read-only operation - viewing all your customers:

```bash
python examples\use_case_6_multi_tenant_operations.py
```

When prompted for which option, type `1` and press Enter.

**What This Shows:**
- All customer accounts in your program
- Number of configurations per customer
- Product types being used

**This is SAFE** - it only reads data, doesn't change anything!

---

## What's Next?

Now that you're set up, you can:

### 📊 **Safe Operations (Read-Only)**
These are safe to run - they only read data:

```bash
# View all customers
python examples\use_case_6_multi_tenant_operations.py

# Check yesterday's consumption
python examples\use_case_4_daily_consumption.py

# Monitor program balance
python examples\use_case_7_program_balance_monitoring.py
```

### 🔧 **Create Operations (Test Carefully)**
These create new resources - use test data first:

```bash
# Onboard new customer
python examples\use_case_1_customer_onboarding.py

# Add devices to existing customer
python examples\use_case_2_service_expansion.py
```

### ⚠️ **Modify Operations (Use with Caution)**
These change existing resources:

```bash
# Add/remove service addons
python examples\use_case_3_service_modification.py

# Suspend customer
python examples\use_case_5_entitlement_suspension.py
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'requests'"
**Fix:** Run `pip install -r requirements.txt`

### "Authentication failed"
**Fix:** Check `testing/config/credentials.json` has correct API username/password

### "400 Bad Request"
**Fix:** Run `python testing\discover_program.py` to get correct program serial number

### "No programs found"
**Fix:**
- Verify you have FortiFlex programs in your account
- Check your API user has FortiFlex permissions in IAM

---

## File Locations

| What | Where |
|------|-------|
| **Discover programs** | `python testing\discover_program.py` |
| **Test auth** | `python testing\test_authentication.py` |
| **Your credentials** | `testing\config\credentials.json` |
| **Use case examples** | `examples\use_case_*.py` |
| **Documentation** | `documentation\` folder |

---

## Need Help?

1. **API Reference:** See `docs/MSSP_Integration_Guide_Part1 (2).md`
2. **Use Cases Guide:** See `documentation/USE_CASES_GUIDE.md`
3. **Product Reference:** See `examples/PRODUCT_TYPE_REFERENCE.md`

---

## Summary

You just:
✅ Installed dependencies
✅ Discovered your FortiFlex programs
✅ Tested API connectivity
✅ Ready to automate!

**Next:** Try the safe read-only operations, then work your way up to creating resources.

---

**Happy Automating!** 🚀
