# FortiFlex MSSP Toolkit

A comprehensive Python toolkit for managing Fortinet FortiFlex MSSP operations through the FortiFlex API. Built for MSSP partners managing multi-tenant customer deployments.

## Disclaimer

**This toolkit is provided for partner use and development purposes.**

- **NOT an official Fortinet product** - Not endorsed, tested, or maintained by Fortinet, Inc.
- **Use at your own risk** - Test in development environments before production deployment
- **No warranties** - Provided "AS IS" without warranties of any kind
- **No liability** - Neither the author nor Fortinet, Inc. shall be held liable for any damages, outages, or issues resulting from use of this code

By using this toolkit, you agree to validate all outputs independently and assume full responsibility for its operation.

---

## Features

- **Complete API Client** - Fully-featured FortiFlexClient class with all MSSP operations
- **7 Use Case Examples** - Production-ready scripts for common MSSP workflows
- **Database Schema** - PostgreSQL schema for storing consumption data (>3 months required!)
- **Rate Limiting** - Built-in rate limiting (100/min, 1000/hour)
- **Error Handling** - Retry logic with exponential backoff
- **Multi-Tenant** - Manage multiple customer accounts from one program

## What is FortiFlex MSSP?

FortiFlex MSSP is Fortinet's flexible licensing program for Managed Security Service Providers:

- **Postpaid billing** - Monthly invoicing based on actual usage
- **Daily point consumption** - Resources charged per day (PST/PDT timezone)
- **Minimum commitment** - 50,000 points/year required
- **Multi-tenant** - Manage multiple customers from one program
- **Flexible** - Scale up/down/in/out without procurement delays

## 🚀 Quick Start

### **👉 New User? START HERE!**

**[Getting Started Guide](documentation/GETTING_STARTED.md)** - Complete onboarding guide

The Getting Started guide walks you through:
1. ✅ Getting your FortiFlex API credentials
2. ✅ Configuring the toolkit (most important step!)
3. ✅ Discovering your program serial number automatically
4. ✅ Testing your setup
5. ✅ Running your first automation

---

### **⚡ Quick Setup (3 Steps)**

> **📋 Note:** You'll see two example files in `testing/config/`:
> - `credentials.example.json` ✅ **Use this one** - Simple API credentials template
> - `config.example.json` 🔧 **Ignore this** - Advanced config for enterprise deployments (database, alerts, etc.)

**Step 1: Configure Credentials** (REQUIRED - Do this first!)
```bash
# Copy the example file and edit with YOUR API credentials:
copy testing\config\credentials.example.json testing\config\credentials.json
notepad testing\config\credentials.json
```

**All scripts load credentials from this ONE file:**
- Location: `testing/config/credentials.json`
- Required fields: `api_username`, `api_password`, `program_serial_number`
- **See [CREDENTIALS_SETUP.md](documentation/CREDENTIALS_SETUP.md) for detailed setup instructions**

**Step 2: Discover Your Program**
```bash
python testing\discover_program.py
```
This automatically updates `testing/config/credentials.json` with your program serial number.

**Step 3: Test & Run**
```bash
# Test authentication
python testing\test_authentication.py

# Run safe read-only examples
python examples\use_case_6_multi_tenant_operations.py
```

---

### **For Developers:**

All scripts automatically load credentials from `testing/config/credentials.json`. No need to edit individual scripts!

```bash
# Install dependencies (optional - try skipping this first)
pip install -r requirements.txt

# Copy and configure credentials (ONCE)
copy testing\config\credentials.example.json testing\config\credentials.json
notepad testing\config\credentials.json

# Discover your program (auto-updates credentials.json)
python testing\discover_program.py

# Test authentication
python testing\test_authentication.py

# Run examples (all use credentials.json automatically)
python examples\use_case_6_multi_tenant_operations.py
python examples\use_case_4_daily_consumption.py
```

**Note:** Most Python installations already include the `requests` library, so you can usually skip the `pip install` step unless you get a `ModuleNotFoundError`.

---

## 📍 Important: Credential Location

**ALL scripts in this toolkit load credentials from:**
```
testing/config/credentials.json
```

**You do NOT need to edit individual script files!**

Configure credentials ONCE in that file, and all scripts will automatically use it.

---

## 🔧 Library Structure

### Core Library: `src/fortiflex_client.py`

**All example scripts import from this single library file.** You don't need to redefine functions - they're all in the `FortiFlexClient` class.

**Available Methods:**

| Method | Purpose | Use Case |
|--------|---------|----------|
| `create_config()` | Create product configuration | Use Cases 1, 3 |
| `update_config()` | Modify existing configuration | Use Case 3 |
| `list_configs()` | List all configurations | Use Cases 2, 5, 6 |
| `create_hardware_entitlements()` | Provision hardware devices | Use Case 1 |
| `create_cloud_entitlements()` | Provision cloud services | Use Case 1 |
| `update_entitlement()` | Change device configuration | Use Case 2 |
| `stop_entitlement()` | Suspend device (reversible) | Use Case 5 |
| `reactivate_entitlement()` | Reactivate suspended device | Use Case 5 |
| `get_entitlement_points()` | Get consumption data | Use Cases 4, 5, 6 |
| `get_program_points()` | Check program balance | Use Case 7 |
| `calculate_points()` | Estimate costs | Use Cases 1, 3 |
| `get_multi_tenant_view()` | View all customers | Use Case 6 |

**Usage Example:**
```python
from src.fortiflex_client import FortiFlexClient, get_oauth_token

# Authenticate
token = get_oauth_token(username, password, client_id="flexvm")

# Initialize client
client = FortiFlexClient(token, program_serial_number)

# Use any method
configs = client.list_configs(account_id=12345)
consumption = client.get_entitlement_points(account_id=12345, start_date="2025-11-01")
```

**Why this structure?**
- ✅ **Single source of truth** - All logic in one library file
- ✅ **No code duplication** - Examples import, don't redefine
- ✅ **Easy updates** - Fix bugs in one place
- ✅ **Type hints included** - Better IDE autocomplete
- ✅ **Built-in rate limiting** - Automatic compliance with API limits

---

## 📚 Documentation

**New Partners - Start Here**:
- **[EXAMPLES_SUMMARY.md](examples/EXAMPLES_SUMMARY.md)** - Complete testing report & quick start guide
- **[PRODUCT_TYPE_REFERENCE.md](examples/PRODUCT_TYPE_REFERENCE.md)** - Full FortiFlex product catalog
- **[USE_CASES_GUIDE.md](documentation/USE_CASES_GUIDE.md)** - Detailed use case documentation
- **[BUGFIX_USE_CASES.md](BUGFIX_USE_CASES.md)** - Complete list of all patches applied (Nov 2025)

---

## Use Cases

This toolkit includes complete examples for all 7 critical MSSP operations:

**Status**: ✅ All examples tested and working (November 9, 2025)

### [Use Case 1: Customer Onboarding](examples/use_case_1_customer_onboarding.py)

Provision initial infrastructure for new customers:
- Create configurations for FortiGate, FortiSwitch, FortiAP, FortiEDR
- Generate hardware and cloud entitlements
- Calculate expected costs
- Organize assets in FortiCloud

**Example:**
```python
from fortiflex_client import FortiFlexClient, get_oauth_token

token = get_oauth_token(API_USERNAME, API_PASSWORD, client_id="flexvm")
client = FortiFlexClient(token, PROGRAM_SN)

# Create FortiGate configuration
config = client.create_config(
    name="Customer-A-FGT60F-UTP",
    product_type_id=101,
    account_id=12345,
    parameters=[
        {"id": 27, "value": "FGT60F"},
        {"id": 28, "value": "FGHWUTP"},
        {"id": 29, "value": "FGHWFAZC"}
    ]
)

# Create entitlements
entitlements = client.create_hardware_entitlements(
    config_id=config['configs']['id'],
    serial_numbers=["FGT60FTK20001234", "FGT60FTK20001235"]
)
```

### [Use Case 2: Service Expansion](examples/use_case_2_service_expansion.py)

Add more devices to existing customer deployments:
- Find existing configuration
- Add new entitlements
- Billing starts same day

### [Use Case 3: Service Modification](examples/use_case_3_service_modification.py)

Add or remove addons (e.g., SOCaaS):
- **Option A:** Update existing config (affects ALL devices)
- **Option B:** Create premium config (selective upgrade)

### [Use Case 4: Daily Consumption Pull](examples/use_case_4_daily_consumption.py)

**CRITICAL:** Pull daily point consumption for billing.

Portal only keeps **3 months** of history - you **MUST** store this data!

- Automated daily job (run at 6 AM PST/PDT)
- Store to database or JSON files
- Generate daily reports
- Monthly invoice generation

**Example:**
```python
# Run daily to collect consumption
consumption = client.get_entitlement_points(
    start_date="2025-11-08",
    end_date="2025-11-08"
)

# Store to database
store_daily_consumption(db_conn, consumption, "2025-11-08")
```

### [Use Case 5: Customer Suspension/Offboarding](examples/use_case_5_entitlement_suspension.py)

Manage customer lifecycle:
- **Scenario A:** Temporary suspension (payment late, reversible)
- **Scenario B:** Disable configuration (all devices)
- **Scenario C:** Permanent offboarding (customer churned)

### [Use Case 6: Multi-Tenant Operations](examples/use_case_6_multi_tenant_operations.py)

MSSP operations dashboard:
- View all customer configurations
- Cross-customer consumption reports
- Real-time metrics (active customers, devices, points)

### [Use Case 7: Program Balance Monitoring](examples/use_case_7_program_balance_monitoring.py)

Monitor commitments:
- **Prepaid:** Alert when balance low
- **MSSP Postpaid:** Track vs. 50,000 point/year minimum

---

## Core API Client

The `FortiFlexClient` class provides methods for all FortiFlex operations:

### Configuration Management

```python
# Create configuration
config = client.create_config(name, product_type_id, parameters, account_id)

# Update configuration (WARNING: affects all entitlements!)
client.update_config(config_id, name, parameters)

# List configurations
configs = client.list_configs(account_id)

# Enable/disable
client.disable_config(config_id)
client.enable_config(config_id)
```

### Entitlement Management

```python
# Hardware entitlements
client.create_hardware_entitlements(config_id, serial_numbers, end_date)

# Cloud entitlements
client.create_cloud_entitlements(config_id, end_date)

# Update entitlement
client.update_entitlement(serial_number, config_id, description, end_date)

# Stop/reactivate
client.stop_entitlement(serial_number)
client.reactivate_entitlement(serial_number)
```

### Point Consumption & Billing

```python
# Get consumption data
consumption = client.get_entitlement_points(
    config_id, serial_number, start_date, end_date
)

# Calculate expected cost
cost = client.calculate_points(product_type_id, count, parameters)

# Check balance (prepaid)
balance = client.get_program_points()
```

### Multi-Tenant Operations

```python
# Get all customers
all_customers = client.get_multi_tenant_view()

# Returns: {account_id: [configs...], ...}
```

---

## Database Setup

**CRITICAL:** FortiFlex portal only keeps 3 months of consumption data. You **MUST** store historical data for billing!

### PostgreSQL Setup

```bash
# Create database
createdb fortiflex

# Load schema
psql fortiflex < database/schema.sql

# Configure connection in examples
DB_CONFIG = {
    'dbname': 'fortiflex',
    'user': 'app',
    'password': 'YOUR_PASSWORD',
    'host': 'localhost'
}
```

### Schema Features

- **Customers** - Account information
- **Configurations** - FortiFlex configs
- **Entitlements** - Active and historical entitlements
- **Daily Consumption** - Point usage (CRITICAL - store >3 months!)
- **Monthly Invoices** - Generated invoices
- **API Audit Log** - API call history
- **Alert History** - System alerts

**Views:**
- `v_active_entitlements` - Summary of active devices
- `v_monthly_consumption` - Monthly totals by customer
- `v_top_consumers_30d` - Top consumers last 30 days

---

## Configuration

### Product Type Parameters

#### FortiGate Hardware (productTypeId: 101)

```python
parameters = [
    {"id": 27, "value": "FGT60F"},        # Model
    {"id": 28, "value": "FGHWUTP"},       # Service Bundle
    {"id": 29, "value": "FGHWFAZC"}       # Addon
]
```

**Service Bundles:**
- `FGHWFC247` - FortiCare Premium
- `FGHWUTP` - UTP Bundle
- `FGHWATP` - ATP Bundle
- `FGHWENT` - Enterprise Bundle
- `FGHWFCEL` - FortiCare Elite

**Addons (Parameter 29):**
- `FGHWFAZC` - FortiAnalyzer Cloud
- `FGHWSOCA` - SOCaaS
- `FGHWFAMS` - FortiGate Cloud Management
- `FGHWFAIS` - AI-Based Sandbox
- `FGHWSWNM` - SD-WAN Underlay
- And more (see [Product Type Reference](examples/PRODUCT_TYPE_REFERENCE.md))

#### FortiSwitch Hardware (productTypeId: 103)

```python
parameters = [
    {"id": 53, "value": "S124FP"},        # Model
    {"id": 54, "value": "FSWHWFC247"}     # Service Bundle
]
```

#### FortiAP Hardware (productTypeId: 102)

```python
parameters = [
    {"id": 55, "value": "FP231F"},        # Model
    {"id": 56, "value": "FAPHWFC247"},    # Service Bundle
    {"id": 57, "value": "NONE"}           # Addon
]
```

#### FortiEDR MSSP (productTypeId: 206)

```python
parameters = [
    {"id": 46, "value": "FEDRPDR"},       # Service Type
    {"id": 47, "value": "250"},           # Endpoint Count
    {"id": 52, "value": "NONE"},          # Addon
    {"id": 76, "value": "1024"}           # Storage (GB)
]
```

---

## Rate Limiting

The FortiFlex API has strict rate limits:
- **100 requests per minute**
- **1000 requests per hour**
- **Max 10 errors per hour** (for config/entitlement creation)

The `RateLimiter` class handles this automatically:

```python
from fortiflex_client import RateLimiter

rate_limiter = RateLimiter(max_per_minute=90, max_per_hour=900)

# Before each API call
rate_limiter.wait_if_needed()
result = client.create_config(...)
```

---

## Error Handling

Common error codes:

| Code | Message | Solution |
|------|---------|----------|
| **-1** | Invalid security token | Refresh OAuth token |
| **-1** | Authorization denied | Check IAM permissions |
| **-1** | Invalid parameter value | Verify parameter IDs |
| **-10** | Exceed max requests in minute | Reduce request rate |
| **-11** | Exceed max requests in hour | Implement rate limiting |
| **-30** | Exceed max error | Fix validation errors |

**Retry with backoff:**

```python
from fortiflex_client import retry_with_backoff

def create_config_safely():
    return client.create_config(...)

result = retry_with_backoff(create_config_safely, max_retries=3)
```

---

## Production Deployment

### Daily Consumption Job (Cron)

```bash
# Add to crontab (run daily at 6 AM PST)
0 6 * * * /usr/bin/python3 /path/to/examples/use_case_4_daily_consumption.py >> /var/log/fortiflex-daily.log 2>&1
```

### Monthly Invoice Generation

```bash
# Run on 1st of each month
0 8 1 * * /usr/bin/python3 /path/to/generate_monthly_invoices.py >> /var/log/fortiflex-invoices.log 2>&1
```

### Alert Monitoring

```python
# Check MSSP commitment weekly
0 9 * * 1 /usr/bin/python3 /path/to/examples/use_case_7_program_balance_monitoring.py
```

---

## Testing

Before production deployment, test in a development environment:

```bash
# Run with test account
export FORTIFLEX_TEST_MODE=1
export FORTIFLEX_TEST_ACCOUNT=99999

python examples/use_case_1_customer_onboarding.py
```

---

## Project Structure

```
fortiflex-mssp-toolkit/
├── src/
│   └── fortiflex_client.py      # Core API client library
├── examples/
│   ├── use_case_1_customer_onboarding.py
│   ├── use_case_2_service_expansion.py
│   ├── use_case_3_service_modification.py
│   ├── use_case_4_daily_consumption.py
│   ├── use_case_5_entitlement_suspension.py
│   ├── use_case_6_multi_tenant_operations.py
│   ├── use_case_7_program_balance_monitoring.py
│   ├── consumption_report_v2.py # Billing reports with Excel export
│   ├── EXAMPLES_SUMMARY.md
│   └── PRODUCT_TYPE_REFERENCE.md
├── testing/
│   ├── config/
│   │   ├── credentials.example.json  # Template - copy and configure
│   │   └── credentials.json          # Your API credentials (gitignored)
│   ├── discover_program.py      # Auto-discover program serial number
│   └── test_authentication.py   # Verify API connectivity
├── database/
│   └── schema.sql               # PostgreSQL database schema
├── documentation/
│   ├── GETTING_STARTED.md
│   ├── CREDENTIALS_SETUP.md
│   ├── USE_CASES_GUIDE.md
│   └── CONSUMPTION_REPORTING_GUIDE.md
├── docs/
│   └── MSSP_Integration_Guide_*.md  # API integration guides
├── requirements.txt
├── setup.py
├── LICENSE
└── README.md
```

---

## Support

This is a community toolkit for partner use:

1. **Toolkit issues:** Open a [GitHub issue](https://github.com/howardsinc3753/MSSP-Tools/issues)
2. **FortiFlex API:** See [FortiFlex Documentation](https://docs.fortinet.com/document/flex-vm/)
3. **Fortinet product support:** Contact [Fortinet TAC](https://support.fortinet.com)

---

## Contributing

Contributions welcome! Please:
1. Test changes in development environment
2. Follow existing code style
3. Update documentation as needed
4. Submit pull requests with clear descriptions

---

## Bug Reports & Issues

Found a bug or have a feature request? Please help us improve!

### How to Report a Bug

1. **Visit:** https://github.com/howardsinc3753/MSSP-Tools/issues
2. **Click:** "New Issue"
3. **Include in your report:**
   - **Tool:** "FortiFlex MSSP Toolkit"
   - **Description:** Clear description of the issue
   - **Steps to reproduce:** What you did when the error occurred
   - **Expected behavior:** What should have happened
   - **Actual behavior:** What actually happened
   - **Environment:**
     - Python version
     - Operating system
     - FortiFlex API version (if known)
   - **Error messages:** Full error output (⚠️ **remove any credentials!**)
   - **Script/Use case:** Which script you were running (e.g., "use_case_1_customer_onboarding.py")

### Common Issues

Before reporting, check [BUGFIX_USE_CASES.md](BUGFIX_USE_CASES.md) for known issues and patches.

### Feature Requests

Have an idea for improvement? Submit it via [GitHub Issues](https://github.com/howardsinc3753/MSSP-Tools/issues) with the "enhancement" label.

---

## Version History

- **v1.0.0** (2025-11-09) - Initial release
  - Complete API client
  - 7 use case examples
  - Database schema
  - Production-ready toolkit

---

## Author

**Fortinet MSSP SE Team**
*This is a partner development toolkit and not an official Fortinet product*

---

## Additional Documentation

- [Getting Started Guide](documentation/GETTING_STARTED.md) - Complete onboarding instructions
- [Credentials Setup](documentation/CREDENTIALS_SETUP.md) - API credential configuration
- [Use Cases Guide](documentation/USE_CASES_GUIDE.md) - Detailed use case documentation
- [Consumption Reporting Guide](documentation/CONSUMPTION_REPORTING_GUIDE.md) - Billing data collection
- [Bug Fixes (Nov 2025)](BUGFIX_USE_CASES.md) - API compatibility patches
- [API Integration Guide Part 1](docs/MSSP_Integration_Guide_Part1%20(2).md) - API basics and authentication
- [API Integration Guide Part 2](docs/MSSP_Integration_Guide_Part2%20(1).md) - Advanced use cases

---

## License

MIT License - See [LICENSE](LICENSE) file for details

---

## Related Resources

- [FortiFlex Documentation](https://docs.fortinet.com/document/flex-vm/)
- [Fortinet Developer Network](https://fndn.fortinet.net)
- [FortiFlex API Swagger](https://support.fortinet.com/ES/api/fortiflex/v2)
- [Fortinet Support Portal](https://support.fortinet.com)

---

**Happy Automating!**
