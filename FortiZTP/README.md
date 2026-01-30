# FortiZTP Python SDK

A Python SDK for Fortinet Zero Touch Provisioning (ZTP) API. Automate device provisioning, manage bootstrap scripts, and streamline MSSP operations.

## Features

- **Device Management**: List, query, and provision devices
- **Script Management**: Create and manage bootstrap CLI scripts
- **FortiManager Integration**: List and assign FortiManagers
- **Multiple Auth Methods**: Credentials file, environment variables, or direct

---

## Getting Started (5 Minutes)

### Step 1: Install Dependencies

```bash
cd FortiZTP
pip install -r requirements.txt
```

### Step 2: Get Your API Credentials

See [Getting Your API Credentials](#getting-your-api-credentials) below for detailed steps.

**Quick version:**
1. Log into [FortiCloud](https://support.fortinet.com) > **IAM** > **API Users** > **Add New**
2. Select **"Local"** as User Type (REQUIRED - ORG type won't work!)
3. Save your **API User ID** and **Password** (shown only once!)
4. Add **FortiZTP** permission with **read/write** access

### Step 3: Configure Credentials

Copy the template and add your credentials:

**macOS/Linux:**
```bash
cp credentials.yaml.template credentials.yaml
```

**Windows (PowerShell):**
```powershell
Copy-Item credentials.yaml.template credentials.yaml
```

**Windows (Command Prompt):**
```cmd
copy credentials.yaml.template credentials.yaml
```

Edit `credentials.yaml`:
```yaml
api_username: "YOUR-API-USER-ID-HERE"
api_password: "YOUR-API-PASSWORD-HERE"
```

### Step 4: Test Your Setup

```bash
python examples/list_devices.py --creds credentials.yaml
```

**Expected output:** Your FortiZTP device inventory. If you see "0 devices" that's OK - it means authentication worked but you don't have devices registered yet.

### Step 5: Start Automating

```python
from fortiztp import FortiZTPClient

client = FortiZTPClient.from_credential_file("credentials.yaml")

# List your devices
devices = client.list_devices()
print(f"Found {len(devices)} devices")

# List your scripts
scripts = client.list_scripts()
print(f"Found {len(scripts)} scripts")
```

---

## Quick Start (Code Examples)

### Basic Usage

```python
from fortiztp import FortiZTPClient

# Create client
client = FortiZTPClient(
    username="your-api-user-id",
    password="your-api-password"
)

# List all devices
devices = client.list_devices()
print(f"Found {len(devices)} devices")

# List unprovisioned FortiGates
unprovisioned = client.list_devices(
    device_type="FortiGate",
    provision_status="unprovisioned"
)

# Create a bootstrap script
result = client.create_script(
    name="Branch-Bootstrap",
    content="""
config system global
    set hostname "Branch-FGT"
end
"""
)
# IMPORTANT: Check if content upload succeeded
if result.get('content_upload_failed'):
    print(f"Script created but content failed - add via portal")
else:
    print(f"Created script OID: {result['script']['oid']}")
```

---

## Getting Your API Credentials

### Step 1: Log into FortiCloud

1. Go to [https://support.fortinet.com](https://support.fortinet.com)
2. Log in with your FortiCloud account

### Step 2: Navigate to IAM

1. Click on your account name (top right)
2. Select **IAM** from the dropdown
3. Or go directly to: [https://support.fortinet.com/iam](https://support.fortinet.com/iam)

### Step 3: Create API User

1. Click **API Users** in the left menu
2. Click **Add New**
3. **IMPORTANT**: Select **Local** as the User Type
   - ORG type users do NOT work with FortiZTP API
   - Only LOCAL IAM users are supported
4. Fill in the details:
   - **User Name**: Descriptive name (e.g., "ZTP-Automation")
   - **Description**: Optional description
5. Click **Save**

### Step 4: Get Your Credentials

After creating the user, you'll see:
- **API User ID**: This is your `username` (looks like a GUID)
- **API Password**: This is your `password`

**Save these immediately** - the password is only shown once!

### Step 5: Configure Permissions

1. Select your new API user
2. Click **Permissions**
3. Add the **FortiZTP** permission with read/write access

---

## Authentication Methods

### Method 1: Direct Credentials

```python
from fortiztp import FortiZTPClient

client = FortiZTPClient(
    username="91BAEC72-FAD0-4DB6-BA53-37B390C5423F",
    password="your-api-password"
)
```

### Method 2: Credential File

Create `credentials.yaml`:

```yaml
api_username: "91BAEC72-FAD0-4DB6-BA53-37B390C5423F"
api_password: "your-api-password"
account_email: "your@email.com"  # Optional, for advanced features
```

```python
from fortiztp import FortiZTPClient

client = FortiZTPClient.from_credential_file("credentials.yaml")
```

### Method 3: Environment Variables

```bash
export FORTIZTP_USERNAME="91BAEC72-FAD0-4DB6-BA53-37B390C5423F"
export FORTIZTP_PASSWORD="your-api-password"
export FORTIZTP_ACCOUNT_EMAIL="your@email.com"  # Optional
```

```python
from fortiztp import FortiZTPClient

client = FortiZTPClient.from_env()
```

---

## CLI Tools (Ready to Use)

The `examples/` folder contains ready-to-use command-line tools:

### List Devices
```bash
python examples/list_devices.py --creds credentials.yaml
python examples/list_devices.py --status unprovisioned  # Filter by status
python examples/list_devices.py --device-type FortiGate  # Filter by type
```

### Provision a Device
```bash
python examples/provision_device.py FGT60F1234567890 \
    --fmg-oid 123 \
    --fmg-ip 192.168.1.100 \
    --script-oid 456 \
    --creds credentials.yaml
```

### Create Bootstrap Scripts
```bash
# List existing scripts
python examples/create_script.py --list --creds credentials.yaml

# Create from built-in template
python examples/create_script.py --name "My-Script" --template basic --creds credentials.yaml

# Create from file
python examples/create_script.py --name "My-Script" --file my_config.txt --creds credentials.yaml
```

Available templates: `basic`, `fmg-registration`, `ipsec-vpn`, `sdwan`

### Bulk Provisioning
```bash
# Provision all unprovisioned devices
python examples/bulk_provision.py \
    --fmg-oid 123 \
    --fmg-ip 192.168.1.100 \
    --script-oid 456 \
    --creds credentials.yaml

# Provision from CSV file
python examples/bulk_provision.py \
    --csv devices.csv \
    --fmg-oid 123 \
    --fmg-ip 192.168.1.100 \
    --creds credentials.yaml

# Dry run (show what would happen)
python examples/bulk_provision.py --dry-run --fmg-oid 123 --fmg-ip 192.168.1.100
```

---

## Use Cases (Python API)

### Use Case 1: Inventory Audit

List all devices and their provisioning status:

```python
from fortiztp import FortiZTPClient

client = FortiZTPClient.from_credential_file("credentials.yaml")

# Get all devices
devices = client.list_devices()

# Summarize by status
from collections import Counter
status_counts = Counter(d['provision_status'] for d in devices)

print("Device Inventory:")
for status, count in status_counts.items():
    print(f"  {status}: {count}")
```

### Use Case 2: Bulk Provisioning

Provision multiple devices to FortiManager:

```python
from fortiztp import FortiZTPClient
from fortiztp.devices import DeviceManager

client = FortiZTPClient.from_credential_file("credentials.yaml")
devices = DeviceManager(client)

# List of devices to provision
serial_numbers = [
    "FGT60F0000000001",
    "FGT60F0000000002",
    "FGT60F0000000003"
]

# FortiManager details
fmg_oid = 123
fmg_ip = "192.168.1.100"
script_oid = 456  # Bootstrap script

for sn in serial_numbers:
    try:
        result = devices.provision(
            serial_number=sn,
            device_type="FortiGate",
            provision_target="FortiManager",
            fortimanager_oid=fmg_oid,
            external_controller_ip=fmg_ip,
            script_oid=script_oid
        )
        print(f"[OK] {sn}: {result['message']}")
    except Exception as e:
        print(f"[ERROR] {sn}: {e}")
```

### Use Case 3: Site Bootstrap Script

Create a comprehensive bootstrap script for branch sites:

```python
from fortiztp import FortiZTPClient
from fortiztp.scripts import ScriptManager

client = FortiZTPClient.from_credential_file("credentials.yaml")
scripts = ScriptManager(client)

branch_script = """
# Basic system configuration
config system global
    set hostname "Branch-FGT"
    set timezone America/New_York
end

# WAN interface with DHCP
config system interface
    edit "wan1"
        set mode dhcp
        set allowaccess ping https ssh snmp fgfm
    next
end

# DNS servers
config system dns
    set primary 8.8.8.8
    set secondary 8.8.4.4
end

# FortiManager registration
config system central-management
    set type fortimanager
    set fmg "192.168.1.100"
end

# Basic admin settings
config system admin
    edit "admin"
        set accprofile "super_admin"
        set vdom "root"
    next
end
"""

result = scripts.create(
    name="Branch-Site-Bootstrap",
    content=branch_script
)

print(f"Created script: {result['script']['name']}")
print(f"Script OID: {result['script']['oid']}")
print(f"Use this OID when provisioning devices")
```

### Use Case 4: IPSEC VPN Bootstrap

Bootstrap script for site-to-site VPN:

```python
vpn_script = """
# WAN Interface
config system interface
    edit "wan1"
        set mode dhcp
        set allowaccess ping https ssh fgfm
    next
end

# IPsec Phase 1
config vpn ipsec phase1-interface
    edit "HQ-VPN"
        set interface "wan1"
        set ike-version 2
        set peertype any
        set net-device enable
        set proposal aes256-sha256
        set remote-gw 203.0.113.1
        set psksecret "your-psk-here"
    next
end

# IPsec Phase 2
config vpn ipsec phase2-interface
    edit "HQ-VPN"
        set phase1name "HQ-VPN"
        set proposal aes256-sha256
        set auto-negotiate enable
    next
end

# Route to HQ
config router static
    edit 0
        set dst 10.0.0.0/8
        set device "HQ-VPN"
    next
end

# Firewall Policy
config firewall policy
    edit 0
        set name "LAN-to-HQ"
        set srcintf "internal"
        set dstintf "HQ-VPN"
        set srcaddr "all"
        set dstaddr "all"
        set action accept
        set schedule "always"
        set service "ALL"
    next
end
"""

result = scripts.create(name="IPSEC-VPN-Bootstrap", content=vpn_script)
```

### Use Case 5: FortiManager Discovery

Find FortiManagers and their assigned scripts:

```python
from fortiztp import FortiZTPClient

client = FortiZTPClient.from_credential_file("credentials.yaml")

# List FortiManagers
fmgs = client.list_fortimanagers()

print("Registered FortiManagers:")
for fmg in fmgs:
    print(f"  OID: {fmg['oid']}")
    print(f"  Serial: {fmg['serial_number']}")
    print(f"  IP: {fmg['ip_address']}")
    print(f"  Script OID: {fmg.get('script_oid', 'None')}")
    print()
```

---

## API Reference

### FortiZTPClient

Main client class for API operations.

| Method | Description |
|--------|-------------|
| `list_devices(device_type=None, provision_status=None, provision_target=None)` | List all devices with optional filters |
| `get_device(serial_number)` | Get detailed device status |
| `provision_device(serial_number, device_type, **kwargs)` | Provision or unprovision a device |
| `list_scripts(include_content=False)` | List all scripts |
| `create_script(name, content)` | Create a new script |
| `list_fortimanagers()` | List registered FortiManagers |

### DeviceManager

Device operations manager.

| Method | Description |
|--------|-------------|
| `list(device_type=None, provision_status=None, provision_target=None)` | List devices |
| `get(serial_number)` | Get device details |
| `provision(serial_number, device_type, **kwargs)` | Provision device |

**Device Types**: `FortiGate`, `FortiAP`, `FortiSwitch`, `FortiExtender`

**Provision Status**: `provisioned`, `unprovisioned`, `hidden`, `incomplete`

**Provision Targets**: `FortiManager`, `FortiGateCloud`, `FortiEdgeCloud`, `ExternalController`

### ScriptManager

Script operations manager.

| Method | Description |
|--------|-------------|
| `list(include_content=False)` | List all scripts |
| `get(script_oid, include_content=True)` | Get script by OID |
| `create(name, content)` | Create new script |
| `delete(script_oid)` | Delete script |

---

## Troubleshooting

### Authentication Failed (401)

- Verify you're using a **LOCAL** IAM user, not ORG type
- Check that your API User has FortiZTP permissions
- Verify credentials are correct

### Device Not Found (404)

- Verify the serial number is correct
- Ensure the device is registered in your FortiCloud account

### Permission Denied (403)

- Check IAM permissions for the API user
- Ensure FortiZTP permission is assigned with read/write

### Script Content Not Uploaded

- This is a known API limitation in some cases
- The script metadata is created; add content via FortiCloud portal
- Portal URL: https://fortiztp.forticloud.com

---

## Project Structure

```
FortiZTP/
├── README.md
├── requirements.txt
├── credentials.yaml.template
├── fortiztp/
│   ├── __init__.py
│   ├── client.py
│   ├── devices.py
│   └── scripts.py
├── examples/
│   ├── list_devices.py
│   ├── provision_device.py
│   ├── create_script.py
│   └── bulk_provision.py
└── docs/
    └── api_reference.md
```

---

## License

MIT License - See LICENSE file for details.

## Support

For issues or feature requests, please open a GitHub issue.

## Contributing

Contributions welcome! Please read CONTRIBUTING.md first.
