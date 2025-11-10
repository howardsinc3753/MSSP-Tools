# Use Case 5: Entitlement Suspension - Naming Clarification

## ✅ **NEW NAME (Correct & Clear)**

**File:** `use_case_5_entitlement_suspension.py`

**What it does:** Suspends/reactivates **ENTITLEMENTS** (device licenses)

**Why this name:** Clear, accurate, no confusion about what gets suspended

---

## ❌ **OLD NAME (Misleading)**

**File:** `use_case_5_customer_suspension.py`

**Problems with old name:**
- ❌ Implies it suspends "customers" (but there's only one root account!)
- ❌ Implies it suspends at customer level (but it's per-entitlement!)
- ❌ Confusing about what actually gets suspended

---

## 🎯 **What Actually Happens**

### **Visual Hierarchy:**

```
┌─────────────────────────────────────────────────────────┐
│ Account: YOUR_ACCOUNT_ID                                        │
│ Status: ALWAYS ACTIVE                                   │
│ ❌ NEVER SUSPENDED BY THIS SCRIPT                       │
└─────────────────────────────────────────────────────────┘
           │
           ├─────────────────────────────────────────┐
           │                                         │
┌──────────▼──────────────┐              ┌──────────▼──────────────┐
│ Configuration: 47456     │              │ Configuration: 47457     │
│ Name: Customer-A-FGT60F  │              │ Name: Customer-B-FSW     │
│ Status: ACTIVE           │              │ Status: ACTIVE           │
│ ❌ STAYS ACTIVE          │              │ ❌ STAYS ACTIVE          │
│ (just a template)        │              │ (just a template)        │
└─────────┬────────────────┘              └─────────┬────────────────┘
          │                                         │
          ├─────────────┬──────────────┐           ├──────────────┐
          │             │              │           │              │
    ┌─────▼─────┐ ┌────▼─────┐  ┌────▼─────┐ ┌───▼──────┐ ┌────▼─────┐
    │Entitlement│ │Entitlement│  │Entitlement│ │Entitlement│ │Entitlement│
    │FGT60F...34│ │FGT60F...35│  │FGT60F...36│ │S124F...01│ │S124F...02│
    │  ACTIVE   │ │  ACTIVE   │  │  ACTIVE   │ │  ACTIVE  │ │  ACTIVE  │
    │✅ SUSPEND │ │✅ SUSPEND │  │✅ SUSPEND │ │✅ SUSPEND│ │✅ SUSPEND│
    └───────────┘ └───────────┘  └───────────┘ └──────────┘ └──────────┘
         ▲              ▲               ▲            ▲            ▲
         │              │               │            │            │
    THIS SCRIPT SUSPENDS THESE (device licenses with serial numbers)
```

---

## 📋 **What Each Action Actually Does**

| Action | What It Suspends | What Stays Active | Billing Impact |
|--------|------------------|-------------------|----------------|
| `--action suspend` | **Entitlements** (licenses) | Configs, Account | Stops tomorrow |
| `--action reactivate` | Nothing (reactivates stopped) | Everything | Resumes today |
| `--action disable-config` | Nothing | All entitlements | No change |
| `--action list` | Nothing (read-only) | Everything | No change |

---

## 🎓 **Clear Terminology Guide**

### **Account** (YOUR_ACCOUNT_ID)
- **What:** Your root FortiFlex account
- **Contains:** All configs and entitlements
- **Can be suspended?** ❌ No
- **Example:** Your MSSP company's main account

### **Configuration** (47456)
- **What:** Template/blueprint for service package
- **Defines:** CPU, bundles, features, addons
- **Can be suspended?** ❌ No (but can be disabled)
- **Example:** "Customer-A-FGT60F" config with 4 CPU, UTP bundle
- **When disabled:** Can't create NEW entitlements, existing ones keep running

### **Entitlement** (FGT60FTK20001234)
- **What:** Actual device license
- **Has:** Serial number, start/end date, status
- **Can be suspended?** ✅ YES - THIS IS WHAT THE SCRIPT DOES
- **Example:** License for one FortiGate firewall
- **When suspended:** Device loses FortiGuard, billing stops tomorrow

---

## 🚀 **Usage Examples with Clear Language**

### **Example 1: Suspend All Customer A's Licenses**

```bash
# Find Customer A's configuration
python list_configs.py --filter "Customer-A"
# Output: 47456    Customer-A-FGT60F    FortiGate-Hardware    ACTIVE

# List their entitlements (licenses)
python use_case_5_entitlement_suspension.py --config-id 47456 --action list
# Shows 3 entitlements: FGT60F...234, FGT60F...235, FGT60F...236

# Suspend all their entitlements
python use_case_5_entitlement_suspension.py --config-id 47456 --action suspend
# Result: All 3 FortiGate licenses suspended
# Config 47456 stays active (still a template)
# Account YOUR_ACCOUNT_ID stays active
```

**What happened:**
- ✅ 3 entitlements suspended (devices lose service)
- ❌ Configuration NOT suspended (still exists as template)
- ❌ Account NOT suspended (still active)

---

### **Example 2: Suspend One Specific License**

```bash
# Suspend just one entitlement
python use_case_5_entitlement_suspension.py \
  --serial FGT60FTK20001234 \
  --action suspend

# Result: Only that ONE license suspended
# Other entitlements keep running!
```

---

### **Example 3: Disable Config (Different from Suspending!)**

```bash
# Disable the configuration template
python use_case_5_entitlement_suspension.py \
  --config-id 47456 \
  --action disable-config

# Result:
# ❌ Can't create NEW entitlements from this config
# ✅ Existing entitlements keep running!
# ✅ Billing continues for existing entitlements
```

**This is NOT suspension!**
- Configuration is disabled (can't create new licenses)
- Entitlements stay active (existing licenses keep running)
- Use case: Contract ending, no new devices but existing ones run until expire

---

## 🆚 **Key Differences**

### **Suspend Entitlement** vs **Disable Configuration**

| Aspect | Suspend Entitlement | Disable Configuration |
|--------|---------------------|----------------------|
| **What changes** | License status → STOPPED | Config status → DISABLED |
| **Existing devices** | Lose service immediately | Keep running |
| **Billing** | Stops tomorrow | Continues |
| **New devices** | Can still create (if config active) | Can't create new |
| **Reversible** | Yes (reactivate) | Yes (enable config) |
| **Use case** | Non-payment, RMA | Contract ending |

---

## 📊 **Real-World Scenarios**

### **Scenario 1: Customer Non-Payment**
**Action:** Suspend their entitlements
```bash
python use_case_5_entitlement_suspension.py --config-id 47456 --action suspend
```
**Result:** All their devices stop working, billing stops tomorrow

---

### **Scenario 2: Device RMA**
**Action:** Suspend one entitlement
```bash
python use_case_5_entitlement_suspension.py --serial FGT60F...234 --action suspend
```
**Result:** That device returns to depot, customer's other devices keep running

---

### **Scenario 3: Contract Ending in 30 Days**
**Action:** Disable configuration NOW, suspend entitlements in 30 days
```bash
# Today: Disable config (no new devices)
python use_case_5_entitlement_suspension.py --config-id 47456 --action disable-config

# In 30 days: Suspend existing entitlements
python use_case_5_entitlement_suspension.py --config-id 47456 --action suspend
```
**Result:** Graceful shutdown - no new services, existing run until contract ends

---

## 🎯 **Quick Reference Card**

### **What This Script Can Do:**
1. ✅ **Suspend entitlements** (stop device licenses)
2. ✅ **Reactivate entitlements** (restart stopped licenses)
3. ✅ **Disable configurations** (prevent new licenses)
4. ✅ **List entitlements** (view before taking action)

### **What This Script CANNOT Do:**
1. ❌ Suspend accounts
2. ❌ Suspend configurations (only disable them)
3. ❌ Delete entitlements (only stop them)
4. ❌ Delete configurations

---

## 🔄 **Command Reference**

```bash
# List entitlements using a config
python use_case_5_entitlement_suspension.py --config-id 47456 --action list

# Suspend all entitlements using a config
python use_case_5_entitlement_suspension.py --config-id 47456 --action suspend

# Suspend one specific entitlement
python use_case_5_entitlement_suspension.py --serial FGT60F...234 --action suspend

# Reactivate entitlements
python use_case_5_entitlement_suspension.py --config-id 47456 --action reactivate

# Disable config (prevent NEW entitlements only)
python use_case_5_entitlement_suspension.py --config-id 47456 --action disable-config
```

---

## 💡 **Pro Tip: Always List First!**

```bash
# GOOD PRACTICE ✅
# Step 1: List what will be affected
python use_case_5_entitlement_suspension.py --config-id 47456 --action list

# Review the output...

# Step 2: Take action
python use_case_5_entitlement_suspension.py --config-id 47456 --action suspend

# BAD PRACTICE ❌
# Don't suspend blindly without knowing what you're affecting!
python use_case_5_entitlement_suspension.py --config-id 47456 --action suspend
```

---

## 📚 **Glossary for Clarity**

| Term | What It Means | Can Script Suspend It? |
|------|---------------|------------------------|
| **Account** | Your root FortiFlex account | ❌ No |
| **Configuration** | Template/blueprint for services | ❌ No (can disable) |
| **Entitlement** | Device license with serial number | ✅ YES |
| **Serial Number** | Unique ID for one entitlement | Identifies what to suspend |
| **Suspend** | Stop entitlement, billing ends | What this script does |
| **Disable** | Turn off config template | Different action |

---

## ✅ **Naming Benefits**

### **Old Name Problems:**
```bash
python use_case_5_customer_suspension.py --config-id 47456 --action suspend
# Question: Am I suspending the customer? The customer's account? 
# What actually happens?
```

### **New Name Clarity:**
```bash
python use_case_5_entitlement_suspension.py --config-id 47456 --action suspend
# Clear: I'm suspending entitlements (device licenses)
# I know exactly what gets affected!
```

---

## 🎓 **For Your Team**

When explaining to others:

**OLD (Confusing):**
> "Run the customer suspension script to suspend them"

**NEW (Clear):**
> "Run the entitlement suspension script to stop their device licenses"

**Even Clearer:**
> "This script suspends individual device licenses (entitlements). The configuration template and account stay active."

---

## 📥 **Download Renamed Script**

**New file:** [use_case_5_entitlement_suspension.py](computer:///mnt/user-data/outputs/use_case_5_entitlement_suspension.py)

**Changes from old version:**
- ✅ Renamed for clarity
- ✅ Updated docstring to emphasize entitlements
- ✅ Updated help text
- ✅ Same functionality, better name

---

## 🔄 **Migration Guide**

If you have the old script:

```bash
# Rename your old script
mv use_case_5_customer_suspension.py use_case_5_customer_suspension.OLD

# Download and use new name
# use_case_5_entitlement_suspension.py

# Update any documentation/scripts that reference the old name
```

**Search and replace in docs:**
- `customer_suspension` → `entitlement_suspension`
- `Suspend customer` → `Suspend entitlements`
- `Customer suspension` → `Entitlement suspension`

---

**Bottom line:** The new name makes it crystal clear - this script suspends ENTITLEMENTS (device licenses), not customers or configurations! 🎯
