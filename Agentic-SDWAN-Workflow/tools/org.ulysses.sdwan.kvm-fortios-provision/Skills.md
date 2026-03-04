# KVM FortiOS Provisioning - Skills Guide

## Purpose

AI-driven tool to provision FortiGate VMs on KVM/Rocky Linux hypervisors. Enables complete greenfield FortiGate deployment without human intervention - from VM creation through initial configuration and FortiFlex license application.

**v1.0.12**: Added `start` and `stop` VM lifecycle actions
- `start`: Start a stopped VM (e.g., after FortiFlex license shutdown). Includes automatic DHCP IP discovery.
- `stop`: Gracefully or forcefully stop a running VM
- Closes GAP-35: AI agents no longer need Bash SSH to hypervisor to restart VMs after license
- QA tested on sdwan-spoke-08: stop → confirmed shut off → start → confirmed running → health-check passed

**v1.0.11**: CRITICAL FIXES for SD-WAN workflow
- Added `set rest-api-key-url-query enable` to bootstrap config (required for REST API config push)
- Added `set admintimeout 480` to bootstrap config (prevents session timeout during config)
- Added `lan_ip` parameter for explicit LAN interface IP (e.g., "10.7.1.1/24")
- Added `site_id` parameter - if provided, derives LAN IP as `10.{site_id}.1.1/24`
- Fixed port2 allowaccess to include `https ssh` (not just ping)

**v1.0.10**: BUGFIX - admin_password now correctly defaults to `FG@dm!n2026!`
- Previous versions (1.0.9 and earlier) incorrectly defaulted to `admin` due to code bug
- If you provisioned with v1.0.9, the password is `admin` NOT `FG@dm!n2026!`

**v1.0.9**: VERIFIED WORKING - Applied Rocky Linux tested ISO procedure:
- ISO structure: `/openstack/content/0000` + `/openstack/latest/user_data`
- Uses `mkisofs -R -r` (no volume label needed)
- Adds `password-policy disable` + `force-password-change disable`
- **BUG**: Default password was `admin` (code bug fixed in v1.0.10)

**v1.0.8**: Changed to OpenStack cloud-init config-drive format.

**v1.0.7**: Fixed ISO creation - removes existing ISO before creating new one.

**v1.0.6**: Fixed fresh disk requirement - FortiOS only reads bootstrap ISO on FIRST boot of FRESH disk. Now removes existing disk before copy. Default password: `FG@dm!n2026!`

**v1.0.5**: Fixed ISO cleanup timing - ISO preserved until confirmed connectivity. Increased boot wait from 30s to 60s.

**v1.0.4**: Fixed NIC ordering - port1=WAN(br0), port2=LAN(VM-Net-X). Bootstrap now configures both interfaces.

## When to Use

- **New SD-WAN spoke/hub deployment**: Spinning up a new FortiGate VM for SD-WAN network
- **Lab environment setup**: Quick provisioning of FortiGate VMs for testing
- **Disaster recovery**: Rapid VM recreation from base image
- **Greenfield deployments**: When user needs a new FortiGate (not existing device)

## Critical Technical Requirements

### Bootstrap ISO - OpenStack Cloud-Init Config-Drive Format (v1.0.8+)

FortiGate 7.6.x on KVM uses the OpenStack cloud-init config-drive format. The VM reads the config on first boot - **NO VNC console interaction required**.

**CRITICAL Requirements (v1.0.9 - Verified Working):**
- ISO structure: `/openstack/content/0000` (empty file) + `/openstack/latest/user_data`
- Created with: `mkisofs -R -r` (no volume label needed)
- Config includes: `password-policy disable` + `force-password-change disable`
- ISO **MUST** exist before VM boots
- ISO **MUST remain available** for 60+ seconds while FortiOS reads config
- Disk **MUST** be a fresh copy (FortiOS only reads config-drive on FIRST boot)

The tool handles all of this automatically using mkisofs.

**ISO Cleanup Policy (v1.0.5+):**
- ISO is **only deleted** after confirmed connectivity (ping success)
- If connectivity pending/failed, ISO is **preserved** for troubleshooting
- Output includes `iso_path` and `iso_cleaned` status for manual cleanup

### SCSI Disk Bus (MANDATORY)

**FortiOS lacks virtio disk drivers at boot.** Using `bus=virtio` results in "No Boot Image Found" error.

The tool automatically uses the correct configuration:
```bash
--disk path=X.qcow2,bus=scsi,format=qcow2 \
--controller type=scsi,model=virtio-scsi
```

### CRITICAL: Static IP vs DHCP Mode

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STATIC IP MODE (RECOMMENDED)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  For PRODUCTION deployments, ALWAYS use static IP mode:                     │
│                                                                              │
│  REQUIRED PARAMETERS:                                                        │
│    - wan_ip: "10.0.0.105/24"    (with CIDR notation)                   │
│    - wan_gateway: "10.0.0.62"    (for default route)                    │
│    - use_dhcp: false (or omit)                                              │
│                                                                              │
│  WHAT GETS CONFIGURED:                                                       │
│    ✓ port1 set to static mode with IP                                       │
│    ✓ Default gateway route (0.0.0.0/0) via wan_gateway                      │
│    ✓ VM immediately reachable at known IP                                   │
│                                                                              │
│  ⚠️ If wan_ip is NOT provided, tool DEFAULTS TO DHCP!                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                    DHCP MODE (LAB/TESTING ONLY)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ⚠️ WARNING: DHCP mode does NOT create a default gateway route!             │
│                                                                              │
│  PARAMETERS:                                                                 │
│    - use_dhcp: true                                                         │
│    - wan_ip: NOT provided (or empty)                                        │
│                                                                              │
│  WHAT HAPPENS:                                                               │
│    ✓ port1 set to DHCP mode                                                 │
│    ✗ NO default gateway route created in bootstrap                          │
│    - Agent must discover IP via MAC-to-ARP correlation                      │
│    - DHCP server must provide default route (not guaranteed)                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### DHCP Mode Discovery

When `use_dhcp=true`, the tool:
1. Configures port1 in DHCP mode via bootstrap ISO
2. Waits for FortiGate to boot and obtain DHCP lease
3. Discovers assigned IP via MAC-to-ARP correlation
4. Returns the discovered IP in the response

### Hub Loopback Routes (IMPORTANT)

**This tool does NOT create static routes to hub loopbacks (172.16.255.x).**

Hub loopback routes (required for BGP) are created in **BLOCK_3** by the `fortigate-sdwan-spoke-template` tool:
- Route to 172.16.255.252/32 via HUB1-VPN1
- Route to 172.16.255.253/32 via HUB1-VPN1

If BGP doesn't establish, ensure BLOCK_3 completes successfully.

## Workflow Phases

```
+---------------------------------------------------------------------+
|                    KVM FORTIOS PROVISIONING WORKFLOW                 |
+---------------------------------------------------------------------+
|  Phase 1: PRE-FLIGHT CHECKS                                          |
|     +-- SSH connectivity to hypervisor                              |
|     +-- libvirtd service running                                    |
|     +-- Base FortiOS image exists                                   |
|     +-- WAN bridge (br0) exists                                     |
|     +-- VM name not already used                                    |
|     +-- Sufficient disk space (>5GB)                                |
|                                                                      |
|  Phase 2: NETWORK CREATION                                          |
|     +-- Create VM-Net-XX for BGP peering                           |
|     +-- Subnet: 10.254.XX.0/24                                     |
|     +-- Gateway: 10.254.XX.1 (on hypervisor)                       |
|                                                                      |
|  Phase 3: BOOTSTRAP ISO CREATION                                    |
|     +-- Generate fgt-vm.conf with admin password + interface config |
|     +-- Create ISO with volume label "config2"                     |
|     +-- Verify ISO file exists                                     |
|                                                                      |
|  Phase 4: VM CREATION                                               |
|     +-- Copy base qcow2 image                                      |
|     +-- Set ownership (qemu:qemu)                                  |
|     +-- virt-install with SCSI disk + virtio NICs + bootstrap ISO  |
|     +-- Verify VM running, get VNC port                            |
|                                                                      |
|  Phase 5: ATTACH BGP NETWORK                                        |
|     +-- Add third interface connected to VM-Net-XX                  |
|                                                                      |
|  Phase 6: BOOTSTRAP APPLY + IP DISCOVERY                            |
|     +-- Wait for FortiGate boot (30-60 seconds)                    |
|     +-- If DHCP: Discover IP via MAC-to-ARP correlation            |
|     +-- If Static: Verify connectivity via ping                    |
|                                                                      |
|  Phase 7: CLEANUP                                                   |
|     +-- Remove bootstrap ISO file                                   |
+---------------------------------------------------------------------+
```

## DHCP IP Discovery

When using DHCP mode, the tool discovers the assigned IP using:

```bash
# Get MAC from VM's br0 interface
MAC=$(virsh domiflist <vm_name> | grep br0 | awk '{print $5}')

# Find IP in ARP table
arp -an | grep -i "$MAC" | awk -F'[()]' '{print $2}'
```

**Notes:**
- KVM VMs use MAC prefix `52:54:00` by default
- `br0` is bridged to physical network 10.0.0.0/24
- VM needs ~10-30 seconds after boot to get DHCP lease
- Tool retries for up to 60 seconds

## Actions

| Action | Description | Required Params |
|--------|-------------|-----------------|
| `provision` | Full provisioning workflow | site_name, subnet_id, (wan_ip OR use_dhcp) |
| `start` | Start a stopped VM (e.g., after license shutdown) | site_name |
| `stop` | Gracefully or forcefully stop a running VM | site_name |
| `status` | Get VM status and interfaces | site_name |
| `destroy` | Remove VM and resources | site_name |
| `list` | List FortiGate VMs on hypervisor | - |

## Parameters

### Required for provision

| Parameter | Type | Description |
|-----------|------|-------------|
| `site_name` | string | Site identifier (becomes VM name: FortiGate-{site_name}) |
| `subnet_id` | integer | Third octet for BGP network (30 = 10.254.30.0/24) |
| `wan_ip` | string | WAN IP with mask (e.g., "192.168.1.100/24") - OR use_dhcp=true |
| `wan_gateway` | string | WAN default gateway - required if static IP |

### Optional

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `use_dhcp` | boolean | false | Use DHCP for port1 instead of static IP |
| `lan_ip` | string | - | LAN interface IP with mask (e.g., "10.7.1.1/24") - FortiGate's gateway on LAN |
| `site_id` | integer | - | Site ID number - if provided, derives lan_ip as `10.{site_id}.1.1/24` |
| `memory_mb` | integer | 4096 | VM RAM in MB |
| `vcpus` | integer | 2 | Number of vCPUs |
| `admin_password` | string | (generated) | Admin password |
| `fortiflex_token` | string | - | FortiFlex license token |
| `hypervisor` | string | (default) | Hypervisor from credentials |
| `site_role` | string | spoke | SD-WAN role (spoke/hub) |

## Usage Examples

### Provision SD-WAN Spoke with site_id (RECOMMENDED)

This is the recommended approach for SD-WAN workflow - derives LAN IP from site_id:

```json
{
  "action": "provision",
  "site_name": "sdwan-spoke-07",
  "site_id": 7,
  "wan_ip": "10.0.0.45/24",
  "wan_gateway": "10.0.0.62",
  "fortiflex_token": "58A7B75F319C5518CD04"
}
```

This generates bootstrap config with:
- `hostname: sdwan-spoke-07`
- `rest-api-key-url-query: enable`
- `port1: 10.0.0.45/24` (static WAN)
- `port2: 10.7.1.1/24` (derived LAN - FortiGate's gateway)
- `default route via 10.0.0.1`

### Provision with Static IP (Legacy)

```json
{
  "action": "provision",
  "site_name": "NYC-01",
  "subnet_id": 30,
  "wan_ip": "10.0.0.100/24",
  "wan_gateway": "10.0.0.62",
  "fortiflex_token": "58A7B75F319C5518CD04"
}
```

### Provision with DHCP

```json
{
  "action": "provision",
  "site_name": "sdwan-spoke-04",
  "subnet_id": 4,
  "use_dhcp": true
}
```

Response will include discovered IP:
```json
{
  "success": true,
  "credentials": {
    "admin_password": "Xk9#mP2$vL7nQ4wR",
    "management_ip": "10.0.0.40"
  },
  "phases": {
    "bootstrap_apply": {
      "status": "success",
      "dhcp_ip": "10.0.0.40",
      "reachable": true
    }
  }
}
```

### Check VM Status

```json
{
  "action": "status",
  "site_name": "NYC-01"
}
```

### List All FortiGate VMs

```json
{
  "action": "list"
}
```

### Start a Stopped VM (after license shutdown)

Primary use case: After FortiFlex license application shuts down the VM.

```json
{
  "action": "start",
  "site_name": "sdwan-spoke-08",
  "hypervisor": "rocky-kvm-lab",
  "wait_for_boot": true,
  "boot_timeout": 120
}
```

Response:
```json
{
  "success": true,
  "vm_name": "FortiGate-sdwan-spoke-08",
  "previous_state": "shut off",
  "state": "running",
  "message": "VM FortiGate-sdwan-spoke-08 started successfully — management IP: 10.0.0.31",
  "management_ip": "10.0.0.31",
  "interfaces": [
    {"fortigate_port": "port1", "source": "br0", "mac_address": "52:54:00:c3:28:40"},
    {"fortigate_port": "port2", "source": "VM-Net-8", "mac_address": "52:54:00:1e:2f:7c"}
  ],
  "hypervisor": "10.0.0.100"
}
```

**Parameters for start:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `site_name` | string | (required) | Site identifier |
| `hypervisor` | string | (default) | Hypervisor from credentials |
| `wait_for_boot` | boolean | true | Wait for FortiOS boot and discover DHCP IP |
| `boot_timeout` | integer | 120 | Seconds to wait for DHCP IP discovery |

### Stop a Running VM

```json
{
  "action": "stop",
  "site_name": "sdwan-spoke-08",
  "hypervisor": "rocky-kvm-lab",
  "force": false
}
```

**Parameters for stop:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `site_name` | string | (required) | Site identifier |
| `hypervisor` | string | (default) | Hypervisor from credentials |
| `force` | boolean | false | Use `virsh destroy` (hard stop) instead of `virsh shutdown` |

### Destroy VM and Disk

```json
{
  "action": "destroy",
  "site_name": "NYC-01",
  "remove_disk": true,
  "remove_network": false
}
```

## Output Examples

### provision Response (Success with DHCP)

```json
{
  "success": true,
  "site_name": "sdwan-spoke-04",
  "hypervisor": {
    "id": "rocky-kvm-lab",
    "host": "10.0.0.100"
  },
  "vm": {
    "name": "FortiGate-sdwan-spoke-04",
    "state": "running",
    "vnc_port": 5903
  },
  "network": {
    "name": "VM-Net-4",
    "bridge": "virbr4",
    "subnet": "10.254.4.0/24",
    "gateway": "10.254.4.1"
  },
  "interfaces": [
    {"fortigate_port": "port1", "source": "br0", "mac_address": "52:54:00:b7:36:6c"},
    {"fortigate_port": "port2", "source": "br0", "mac_address": "52:54:00:6f:1f:3c"},
    {"fortigate_port": "port3", "source": "VM-Net-4", "mac_address": "52:54:00:0b:6a:f1"}
  ],
  "credentials": {
    "admin_password": "Xk9#mP2$vL7nQ4wR",
    "management_ip": "10.0.0.40"
  },
  "phases": {
    "ssh_connect": {"success": true},
    "preflight": {"passed": true},
    "network": {"success": true, "action": "created"},
    "bootstrap_iso": {"success": true},
    "vm_create": {"success": true},
    "attach_network": {"success": true},
    "bootstrap_apply": {"status": "success", "dhcp_ip": "10.0.0.40", "reachable": true}
  },
  "next_steps": [
    "VM booted with DHCP IP: 10.0.0.40",
    "VNC access: 10.0.0.100:5903",
    "Login: admin / Xk9#mP2$vL7nQ4wR",
    "Run sdwan-blueprint-planner for full SD-WAN configuration"
  ]
}
```

## Prerequisites

### Hypervisor Registration

Before provisioning, register the hypervisor:

```json
{
  "tool": "hypervisor-credential-manager",
  "action": "add",
  "hypervisor_id": "rocky-kvm-lab",
  "host": "10.0.0.100",
  "username": "root",
  "password": "your-password"
}
```

### Base FortiOS Image

The hypervisor needs a FortiOS qcow2 image at `/home/libvirt/images/fortios-7.6.5-base.qcow2`:

```
Path:         /home/libvirt/images/fortios-7.6.5-base.qcow2
Format:       qcow2
Virtual Size: 2 GiB
Actual Size:  120 MiB
Version:      FortiOS 7.6.5.M build 3651
Owner:        qemu:qemu
```

### FortiFlex Token (Optional)

For VM licensing, get a token first:

```json
{
  "tool": "fortiflex-token-create",
  "config_id": 53713,
  "description": "NYC-01 Spoke"
}
```

## Interface Mapping

After provisioning, FortiGate interfaces map as follows:

| FortiGate Port | KVM Network | Purpose |
|----------------|-------------|---------|
| port1 | br0 (WAN bridge) | WAN / Management |
| port2 | br0 (WAN bridge) | Secondary WAN / LAN |
| port3 | VM-Net-XX | BGP / SD-WAN Peering |

## Troubleshooting

### Bootstrap ISO Not Applied

**Symptoms**: FortiGate boots to factory defaults (192.168.1.99)

**Causes** (v1.0.9 verified working procedure):
- Missing `/openstack/content/0000` empty file
- Wrong directory structure (must be `/openstack/latest/user_data`)
- Disk not fresh (FortiOS only reads config-drive on FIRST boot of fresh disk)
- ISO file not created before VM boot
- ISO not attached to VM
- Missing `password-policy disable` in config

**Check**:
```bash
# Verify ISO is attached
virsh dumpxml <vm_name> | grep -A5 cdrom
ls -la /tmp/fgt-bootstrap-*.iso

# Verify ISO contents have correct structure
mkdir -p /tmp/check-iso && mount -o loop /tmp/fgt-bootstrap-*.iso /tmp/check-iso
ls -la /tmp/check-iso/openstack/content/   # Should have 0000
ls -la /tmp/check-iso/openstack/latest/    # Should have user_data
cat /tmp/check-iso/openstack/latest/user_data
umount /tmp/check-iso
```

### DHCP IP Not Discovered

**Causes**:
- VM still booting
- DHCP server not responding
- ARP table not populated

**Manual Discovery**:
```bash
MAC=$(virsh domiflist FortiGate-site | grep br0 | awk '{print $5}')
ping -c 2 -b 10.0.0.255  # Populate ARP table
arp -an | grep -i "$MAC"
```

### "No Boot Image Found" Error

**Cause**: Disk bus incorrectly set to virtio
**Solution**: Tool handles this automatically with SCSI bus.

### SSH Connection Fails

**Verify hypervisor credentials**:
```json
{"tool": "hypervisor-credential-manager", "action": "verify"}
```

## Security Considerations

1. **Generated Passwords**: Strong 16-char passwords with mixed case, numbers, symbols
2. **Password Storage**: Returned in response - should be stored securely
3. **SSH Credentials**: Stored in hypervisor_credentials.yaml - protect this file
4. **VNC Access**: VNC ports are open on hypervisor - restrict network access

## Related Tools

| Tool | Purpose |
|------|---------|
| `hypervisor-credential-manager` | Register hypervisor SSH credentials |
| `fortiflex-token-create` | Generate FortiFlex license tokens |
| `credential-manager` | Register FortiGate API credentials |
| `sdwan-blueprint-planner` | Generate full SD-WAN configuration |
| `sdwan-manifest-tracker` | Track SD-WAN devices and configs |
| `fortigate-ssh` | SSH to FortiGate for additional config |

## CRITICAL: Post-Provision Steps (AI MUST DO)

After `action=provision` succeeds, the AI agent **MUST** complete these steps:

### Step 1: Discover DHCP IP (if use_dhcp=true)

The `status` action returns MAC address but NOT the DHCP IP. To discover:

```bash
# Option A: Query hypervisor ARP table
ssh root@{hypervisor} "arp -an | grep -i {mac_address}"

# Option B: User checks VNC console
# VNC: {hypervisor}:{vnc_port}
# Login: admin / {password}
# Command: get system interface physical
```

### Step 2: Register Credentials (MANDATORY)

**fortigate-health-check and fortigate-ssh will FAIL without this step!**

```json
{
  "tool": "credential-manager",
  "action": "add",
  "device_id": "{site_name}",
  "host": "{discovered_ip}",
  "username": "admin",
  "password": "{admin_password}",
  "api_key": ""
}
```

### Step 3: Verify Connectivity

Only AFTER credentials are registered:

```json
{"tool": "fortigate-health-check", "target_ip": "{discovered_ip}"}
```

### Password Reference by Version

| Tool Version | Default Password |
|--------------|------------------|
| v1.0.10+ | `FG@dm!n2026!` |
| v1.0.9 and earlier | `admin` (bug) |

If password was not explicitly provided during provision, use the default for that version.

## CRITICAL: FortiFlex License Causes VM Shutdown

**When applying a FortiFlex license via `execute vm-license install <token>`, the FortiGate VM will SHUT DOWN to apply the license. It does NOT automatically reboot!**

### Symptoms
- SSH connection drops immediately after license command
- `virsh list` shows VM in "shut off" state
- fortigate-health-check fails with connection refused

### Required Action: Restart VM After License

The AI agent **MUST** restart the VM after license application. Use the `start` action (v1.0.12+):

```json
{
  "action": "start",
  "site_name": "{site_name}",
  "hypervisor": "rocky-kvm-lab",
  "wait_for_boot": true,
  "boot_timeout": 120
}
```

This handles everything: `virsh start`, wait for boot, DHCP IP discovery. Returns `management_ip` when ready.

**Fallback (if tool not available):**
```bash
ssh root@{hypervisor_ip} "virsh start FortiGate-{site_name}"
# Wait 60 seconds for boot
ssh root@{hypervisor_ip} "virsh domstate FortiGate-{site_name}"
```

### Detection Pattern

If using `fortigate-ssh` or `fortigate-cli-execute` for license:
1. Command succeeds with "License installed" message
2. Subsequent commands fail with "Connection refused" or timeout
3. **This is expected behavior** - do NOT treat as error
4. Execute VM restart on hypervisor
5. Wait 45-60 seconds for boot
6. Retry connectivity check

### Verification After Restart

```bash
# Via fortigate-cli-execute
execute ssh root@{hypervisor} "virsh domstate FortiGate-{site_name}"  # Should show "running"

# Via fortigate-health-check (after VM boots)
fortigate-health-check target_ip={device_ip}
```

## Complete Greenfield Workflow

```
1. hypervisor-credential-manager action=add   <- One-time setup
2. hypervisor-credential-manager action=verify <- Validate connectivity
3. fortiflex-token-create config_id=X         <- Get license token
4. kvm-fortios-provision action=provision     <- Create & configure VM
5. ** DISCOVER DHCP IP ** (if DHCP mode)      <- CRITICAL STEP
6. credential-manager action=add              <- MUST DO before health-check!
7. fortigate-health-check                     <- Verify API connectivity
8. fortigate-cli-execute: vm-license install  <- Apply FortiFlex license
9. kvm-fortios-provision action=start         <- VM shuts down after license! (v1.0.12+)
10. Wait for boot (start action handles this with wait_for_boot=true)
11. fortigate-health-check                    <- Verify VM is back up
12. sdwan-manifest-tracker action=absorb      <- Add to inventory
13. sdwan-blueprint-planner action=plan-site  <- Full SD-WAN config
```
