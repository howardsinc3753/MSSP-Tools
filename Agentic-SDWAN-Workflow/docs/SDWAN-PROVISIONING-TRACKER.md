# SD-WAN Provisioning Project Tracker

**Project:** Add SD-WAN Site - Agentic Workflow
**Started:** 2026-01-17
**Last Updated:** 2026-01-20 (Session 4)
**Status:** Block 3 IN PROGRESS - What-If Documentation Complete, Config Push Blocked

---

## Block Status

| Block | Name | Status | Notes |
|-------|------|--------|-------|
| **Block 1** | VM Provisioning | ✅ COMPLETE | VM creation works, DHCP fallback, bootstrap ISO enhancement pending |
| **Block 2** | License + API | ✅ COMPLETE | FortiFlex applied, API token generated, device registered |
| **Block 3** | SD-WAN Blueprint | 🟡 PARTIAL | Manifest absorbed, blueprint generated, **config-push BLOCKED** |
| **Block 4** | Verification | 🔲 PENDING | Connectivity checks |

---

## Quick Reference

| Resource | Location |
|----------|----------|
| **Agentic Workflow** | `solution_packs/fortigate-ops/workflows/add-sdwan-site/` |
| **SD-WAN Manifest** | `C:/ProgramData/Ulysses/config/sdwan-manifest.yaml` |
| **Hypervisor Credentials** | `~/.config/mcp/hypervisor_credentials.yaml` |
| **KVM Provision Tool** | `tools/org.ulysses.sdwan.kvm-fortios-provision/` |
| **Credential Manager** | `tools/org.ulysses.provisioning.hypervisor-credential-manager/` |
| **NFR Reference** | `NFR-023-SDWAN-FORTIGATE-VM-PROVISIONING.md` (v1.1.0) |

---

## Environment Details

### KVM Hypervisor
- **Host:** 10.0.0.100
- **OS:** Rocky Linux 9
- **libvirt:** v10.10.0
- **SSH:** root / `{{REDACTED}}`
- **Bridge:** br0
- **Free Space:** 7.2 TB

### FortiOS Base Image
- **Path:** `/home/libvirt/images/fortios-7.6.5-base.qcow2`
- **Size:** 120 MiB
- **Version:** FortiOS 7.6.5.M
- **Critical:** Must use SCSI disk bus (not virtio - FortiOS lacks virtio disk drivers at boot)

### Existing SD-WAN Network
- **AS Number:** 65000
- **Loopback Range:** 172.16.0.0/16
- **Hub:** 10.0.1.1 (FGVMMLTMXXXXXXXXX) - FortiFlex licensed
- **Spoke:** 10.0.0.30 (FW50G5TKXXXXXXXXX) - Standard HW license
- **Hub Loopbacks:** 172.16.255.252 (BGP), 172.16.255.253 (Health)
- **Spoke Loopback:** 172.16.0.2

---

## Progress Checklist

### Phase 1: Tool Development (COMPLETE)
- [x] Create hypervisor credential manager tool
- [x] Store Rocky KVM lab credentials
- [x] Create KVM FortiOS provisioning tool
- [x] Update tools with correct base image path (from NFR v1.1.0)
- [x] Verify hypervisor connectivity (SSH, libvirt, base image, br0, disk space)
- [x] **TEST: Run actual VM provision on KVM** ✅

### Phase 2: Agentic Workflow Scaffold
- [x] Create workflow directory structure
- [x] Create manifest.yaml (goal, phases, strategies, decision points)
- [x] Create Skills.md (AI routing guide)
- [x] Test workflow Block 1 (provision) with real VM ✅
- [x] Test workflow Block 2 (license) with FortiFlex token ✅
- [ ] Test workflow Block 3 (configure) with blueprint ← NEXT
- [ ] Test workflow Block 4 (verify) with connectivity checks

### Phase 3: Integration Testing
- [ ] End-to-end VM deployment test
- [ ] End-to-end hardware onboarding test
- [ ] Error recovery / adaptive strategy test
- [ ] Document any issues and fixes

### Phase 4: Production Readiness
- [ ] Register tools with Trust Anchor
- [ ] Register workflow with solution pack
- [ ] Update solution pack SKILLS.md
- [ ] Final documentation review

---

## Tools Created

### 1. org.ulysses.provisioning.hypervisor-credential-manager
**Status:** Created, Tested
**Location:** `tools/org.ulysses.provisioning.hypervisor-credential-manager/`
**Actions:** list, add, remove, verify, paths, get

**Stored Credentials:**
```yaml
hypervisors:
  rocky-kvm-lab:
    host: 10.0.0.100
    port: 22
    username: root
    auth_method: password
    password: {{REDACTED}}
    base_image_path: /home/libvirt/images/fortios-7.6.5-base.qcow2
    vm_image_path: /home/libvirt/images/
    wan_bridge: br0
default_hypervisor: rocky-kvm-lab
```

### 2. org.ulysses.sdwan.kvm-fortios-provision
**Status:** Created, Pending Test
**Location:** `tools/org.ulysses.sdwan.kvm-fortios-provision/`
**Actions:** preflight, provision, configure, verify, full

**Key Technical Details:**
- Uses SCSI disk bus with virtio-scsi controller (critical!)
- FortiGate first-login: admin/blank → set password twice
- Console automation via virsh with expect-like patterns

**virt-install command:**
```bash
virt-install \
  --name <vm_name> \
  --vcpus 2 --memory 4096 \
  --disk path=<disk>.qcow2,bus=scsi,format=qcow2 \
  --controller type=scsi,model=virtio-scsi \
  --network bridge=br0,model=virtio \
  --osinfo detect=on,require=off \
  --graphics vnc,listen=0.0.0.0 \
  --noautoconsole --import
```

---

## Agentic Workflow Structure

**Workflow ID:** `org.ulysses.workflow.add-sdwan-site/1.0.0`

### Phases

| # | Phase | Goal | Key Tools |
|---|-------|------|-----------|
| 1 | Provision | Device exists & accessible | `kvm-fortios-provision`, `fortigate-health-check` |
| 2 | License | Valid license applied | `fortiflex-token-create`, `fortigate-ssh` |
| 3 | Configure | SD-WAN blueprint deployed | `blueprint-planner`, `config-push`, `manifest-tracker` |
| 4 | Verify | Full overlay connectivity | `fortigate-ssh` (diagnose commands) |

### Strategies
- **adaptive** (default) - LLM evaluates and decides
- **sequential** - Linear execution
- **goal_seeking** - Maximum flexibility

### Success Criteria
1. Device reachable at management IP
2. License status ACTIVE
3. IPsec tunnels UP
4. BGP state Established
5. SD-WAN health checks GREEN
6. Overlay ping succeeds (spoke loopback → hub loopback)

---

## Session Notes

### 2026-01-17
- Created initial tools for hypervisor credential management
- Created KVM provisioning tool skeleton
- Discovered FortiOS requires SCSI disk bus (not virtio)

### 2026-01-19 (Session 1)
- Updated base image path from NFR v1.1.0: `/home/libvirt/images/fortios-7.6.5-base.qcow2`
- Verified hypervisor: SSH ✓, libvirt ✓, base image ✓, br0 ✓, 7.2TB free ✓
- Updated SD-WAN manifest with fresh hub/spoke configs
- Added license tracking to manifest (FortiFlex for hub, Standard for spoke)
- Created agentic workflow scaffold (`add-sdwan-site`)

### 2026-01-19 (Session 2) - BLOCK 1 TEST
**VM Provisioned:** `sdwan-spoke-02` → `10.0.0.35`

**What Worked:**
- ✅ virt-install with SCSI disk bus
- ✅ VM-Net-2 (10.254.2.0/24) created and attached for BGP
- ✅ VM boots to FortiOS 7.6.5
- ✅ DHCP assigned 10.0.0.35
- ✅ Manual password set: `{{ADMIN_PASSWORD}}`
- ✅ SSH/HTTPS/PING enabled on port1
- ✅ Connectivity verified from Windows

**What Didn't Work (Future Enhancement):**
- ❌ Bootstrap ISO (fgt-vm.conf) not read by FortiOS
- Console automation also fragile (timing issues)

**Block 1 Outcome:** SUCCESS with DHCP fallback
**Enhancement Backlog:** Bootstrap ISO / pre-configured template

**VM Details:**
- **Name:** FortiGate-sdwan-spoke-02
- **IP:** 10.0.0.35 (DHCP)
- **VNC:** 10.0.0.100:5902
- **Credentials:** admin / {{ADMIN_PASSWORD}}
- **BGP Network:** VM-Net-2 (port3 → 10.254.2.0/24)

**Next:** Block 2 - Apply FortiFlex license, register API credentials

### 2026-01-19 (Session 3) - BLOCK 2 TEST
**Device Licensed & Onboarded:** `sdwan-spoke-02` → `FGVMMLTMYYYYYYYYY`

**What Worked:**
- ✅ FortiFlex token generated: `{{FORTIFLEX_TOKEN_EXAMPLE}}` (config: sdwan-spoke-2cpu-utp / 53713)
- ✅ License applied via SSH: `execute vm-license {{FORTIFLEX_TOKEN_EXAMPLE}}`
- ✅ Serial changed from FGVM64-KVM → FGVMMLTMYYYYYYYYY
- ✅ Device rebooted and came back online at same IP
- ✅ `fortigate-onboard` tool created API user and token
- ✅ Device registered as `sdwan-spoke-02` in credentials file

**Tools Used (Block 2):**
| Tool | Purpose | Status |
|------|---------|--------|
| `fortiflex-token-create` | Generate VM license token | ✅ WORKS |
| `fortigate-onboard` | Create API user, generate key, register device | ✅ WORKS |
| `fortigate-ssh` | Apply license command | ❌ **GAP** - read-only commands only |
| `fortigate-api-token-create` | Create API token via REST | ❌ **GAP** - endpoint redirect issue |

**Tool Gaps Identified:**
1. **fortigate-ssh** - Only allows read-only diagnostic commands. Need write mode for:
   - `execute vm-license <token>`
   - `config system interface`
   - `config router static`
2. **fortigate-api-token-create** - REST endpoint returns HTML redirect instead of API response

**Block 2 Outcome:** SUCCESS using workaround (plink SSH + fortigate-onboard tool)

**Updated Device Details:**
- **Name:** FortiGate-sdwan-spoke-02
- **IP:** 10.0.0.35 (DHCP)
- **Serial:** FGVMMLTMYYYYYYYYY (FortiFlex licensed)
- **Credentials:** admin / {{ADMIN_PASSWORD}}
- **API Token:** {{API_TOKEN_EXAMPLE}}
- **Device ID:** sdwan-spoke-02 (in fortigate_credentials.yaml)

**Next:** Block 3 - Deploy SD-WAN Blueprint (IPsec/BGP/SD-WAN config)

### 2026-01-19 (Session 3 continued) - BLOCK 3 PARTIAL
**Blueprint Generated, Config Push Blocked**

**What Worked:**
- ✅ Device absorbed into manifest: `spoke_192_168_209_35`
- ✅ FortiFlex license tracked in manifest
- ✅ Blueprint generated: `sdwan-spoke-02_config.txt` (263 lines FortiOS CLI)
- ✅ Config includes: IPsec tunnels, BGP, SD-WAN zones/members/health-checks, policies

**What Didn't Work:**
- ❌ `fortigate-sdwan-spoke-template` - CLI args not parsing, applied to wrong device
- ❌ No `fortigate-config-push` tool exists to deploy CLI config

**Generated Artifacts:**
| File | Location |
|------|----------|
| Blueprint Template | `C:\ProgramData\Ulysses\config\blueprints\sdwan-spoke-02_template.csv` |
| FortiOS Config | `C:\ProgramData\Ulysses\config\blueprints\sdwan-spoke-02_config.txt` |

**Block 3 Outcome:** BLOCKED - Need config-push capability

---

## Tool Gap Backlog

| Tool | Issue | Priority | Fix Required |
|------|-------|----------|--------------|
| `fortigate-ssh` | Read-only commands only | **HIGH** | Add `provisioning_mode` with write command allowlist |
| `fortigate-onboard` | Writes to wrong credentials path | **HIGH** | Use `~/.config/mcp/` not relative path |
| `fortigate-sdwan-spoke-template` | CLI argument parsing broken | **HIGH** | Fix argument parser to accept positional args |
| **MISSING** | `fortigate-config-push` | **HIGH** | Create tool to push CLI config via SSH/API |
| `fortigate-api-token-create` | REST redirect issue | MEDIUM | Fix session-based auth for FortiOS 7.6+ |
| `kvm-fortios-provision` | Bootstrap ISO ignored | LOW | Investigate FortiOS bootstrap config format |

### Detailed Gap Analysis (2026-01-20)

#### fortigate-ssh (Block 2)
**Location:** `tools/org.ulysses.noc.fortigate-ssh/org.ulysses.noc.fortigate-ssh.py`
**Issue:** `COMMAND_ALLOWLIST` (lines 43-77) only allows read-only commands.
**Missing Commands for Provisioning:**
- `execute vm-license <token>` - FortiFlex license application
- `config system interface` - interface configuration
- `config vpn ipsec phase1-interface` - IPsec tunnels
- `config router static` - static routing
- `config router bgp` - BGP configuration
- `config system sdwan` - SD-WAN configuration

**Proposed Fix:**
```python
# Add provisioning_mode parameter
provisioning_mode = args.get("provisioning_mode", False)

# Separate allowlist for provisioning
PROVISIONING_ALLOWLIST = [
    r"^execute vm-license \S+$",
    r"^config system interface$",
    r"^config vpn ipsec phase1-interface$",
    r"^config router static$",
    r"^config router bgp$",
    r"^config system sdwan$",
    # ... etc
]
```

#### fortigate-onboard (Block 2)
**Location:** `tools/org.ulysses.provisioning.fortigate-onboard/org.ulysses.provisioning.fortigate-onboard.py`
**Issue:** Lines 199-212 use wrong credential paths (relative instead of ~/.config/mcp/)
**Current Code:**
```python
config_paths = [
    Path("config/fortigate_credentials.yaml"),  # WRONG
]
```
**Proposed Fix:**
```python
config_paths = [
    Path.home() / ".config" / "mcp" / "fortigate_credentials.yaml",  # CORRECT
    Path("C:/ProgramData/mcp/fortigate_credentials.yaml"),  # Windows system-wide
]
```

#### fortigate-sdwan-spoke-template (Block 3)
**Location:** `tools/org.ulysses.provisioning.fortigate-sdwan-spoke-template/org.ulysses.provisioning.fortigate-sdwan-spoke-template.py`
**Issue:** Lines 537-548 have hardcoded test values that run when executed standalone.
**Current Code:**
```python
if __name__ == "__main__":
    result = main({
        "target_ip": "10.0.0.30",  # HARDCODED - WRONG!
        "hub_wan_ip": "66.110.253.68",
        # ... more hardcoded values
    })
```
**Impact:** When running standalone, tool always targets `.30` instead of intended device.
**Proposed Fix:**
```python
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-ip", required=True)
    parser.add_argument("--hub-wan-ip", required=True)
    parser.add_argument("--loopback-ip", required=True)
    parser.add_argument("--psk", required=True)
    # ... etc
    args = parser.parse_args()
    result = main(vars(args))
```

#### fortigate-config-push (Block 3 - MISSING)
**Status:** Tool does not exist
**Need:** Push FortiOS CLI configuration from blueprint file
**Design Options:**
1. **SSH-based push** - Read config file, send commands via SSH
2. **REST API push** - Convert CLI to API calls (complex, many endpoints)
3. **FortiManager integration** - Use FMG scripts (requires FMG)

**Recommended Approach:** SSH-based push using `fortigate-ssh` with `provisioning_mode`
- Enables single tool fix to unblock both Block 2 and Block 3
- Blueprint file is already FortiOS CLI format

### Gap Analysis Summary
- **Block 1**: 1 gap (bootstrap ISO) - ✅ RSA key auth FIXED
- **Block 2**: 3 gaps (ssh write, onboard path, api-token-create)
- **Block 3**: 2 gaps (spoke-template args, missing config-push)

### Block 1 Gap Fixes Applied
| Gap | Fix | Date |
|-----|-----|------|
| Password-based SSH auth | Switched to RSA-4096 key auth | 2026-01-19 |
| Key location | `~/.config/mcp/keys/hypervisor_rsa` | 2026-01-19 |

### 2026-01-20 (Session 4) - WHAT-IF DOCUMENTATION
**What-If Scenarios Documented in Agentic Workflow Manifest**

Added comprehensive error_handling sections to `manifest.yaml`:

**Block 1 - VM Provisioning (8 scenarios):**
| # | Condition | Description |
|---|-----------|-------------|
| 1 | `vm_running and no_dhcp_lease` | VM boots but no IP - console fallback to static |
| 2 | `base_image_not_found` | FortiOS qcow2 not at expected path |
| 3 | `insufficient_disk_space` | Not enough free space for VM disk |
| 4 | `vm_name_conflict` | VM name already exists in libvirt |
| 5 | `bridge_not_found` | WAN bridge (br0) not configured |
| 6 | `libvirt_unavailable` | libvirtd service not running |
| 7 | `hypervisor_ssh_failed` | SSH authentication failure to KVM host |
| 8 | `vm_boot_failure` | FortiOS doesn't boot (SCSI driver issue) |

**Block 2 - License Application (6 scenarios):**
| # | Condition | Description |
|---|-----------|-------------|
| 1 | `token_rejected` | FortiFlex token invalid/expired/used |
| 2 | `license_no_reboot` | VM shut off instead of rebooting |
| 3 | `ssh_tool_readonly` | fortigate-ssh doesn't allow write commands |
| 4 | `api_token_failed` | REST API token creation fails |
| 5 | `ip_changed_after_reboot` | Device IP changed after license reboot |
| 6 | `password_changed` | Cannot authenticate after license |

**Block 3 - Configuration (8 scenarios):**
| # | Condition | Description |
|---|-----------|-------------|
| 1 | `config_push_missing` | No fortigate-config-push tool exists |
| 2 | `template_args_failed` | spoke-template argument parsing broken |
| 3 | `config_syntax_error` | FortiOS rejected config syntax |
| 4 | `object_exists` | Config object already exists |
| 5 | `psk_mismatch` | IPsec PSK doesn't match hub |
| 6 | `network_id_mismatch` | SD-WAN network-id wrong |
| 7 | `blueprint_failed` | Blueprint generation failed |
| 8 | `wrong_creds_path` | fortigate-onboard wrote to wrong path |

**Key Fixes Applied:**
- Fixed `execute vm-license install` → `execute vm-license` (no "install" keyword)
- Documented fortigate-ssh read-only workaround (use plink or fortigate-onboard)
- Added escalation paths for all scenarios

**Next:** Review and fix actual tool gaps (fortigate-ssh, fortigate-config-push)

### 2026-01-20 (Session 4 continued) - AGENTIC AI BLOCK STACKING FRAMEWORK

**Created Framework for Sub-Agent Dispatch**

Refactored monolithic manifest.yaml into block-separated architecture for context-efficient sub-agent execution.

**New Directory Structure:**
```
workflows/add-sdwan-site/
├── manifest.yaml          # MASTER - Full orchestration (unchanged)
├── Skills.md              # AI routing guide
├── FRAMEWORK.md           # Framework documentation (NEW)
└── blocks/                # Sub-agent briefings (NEW)
    ├── BLOCK_1_PROVISION.yaml   # ~250 lines
    ├── BLOCK_2_LICENSE.yaml     # ~250 lines
    ├── BLOCK_3_CONFIGURE.yaml   # ~300 lines
    └── BLOCK_4_VERIFY.yaml      # ~250 lines
```

**Block File Schema:**
- `block_id/name/version` - Identity
- `depends_on` - Block dependencies with required outputs
- `goal` - Sub-agent objective statement
- `inputs` - From master + previous blocks
- `success_criteria` - How to verify completion
- `outputs` - What to report back to Master
- `tools` - Available tools for this block
- `tool_gaps` - Known issues + workarounds
- `error_handling` - What-if scenarios (8 per block)
- `report_format` - Structured response template

**Benefits:**
| Aspect | Before | After |
|--------|--------|-------|
| Context per sub-agent | ~800 lines | ~250 lines |
| Block independence | Coupled | Isolated |
| Testing | Full workflow | Per-block |
| Failure handling | Pollutes context | Isolated |

---

## Next Session Agenda

### Priority 1: Tool Gap Review (Blocks 1-3)

Before continuing Block 3, audit and fix tool gaps:

1. **Block 1 - VM Provisioning**
   - [x] Document what-if scenarios (no DHCP, wrong image, disk full) ✅ Added to manifest.yaml
   - [ ] Add bootstrap ISO enhancement to backlog with details
   - [ ] Verify `kvm-fortios-provision` handles errors gracefully

2. **Block 2 - License + API**
   - [ ] Fix `fortigate-ssh` - add provisioning mode for write commands
   - [ ] Fix `fortigate-onboard` - write to correct credentials path
   - [x] Document FortiFlex token workflow ✅ Added to manifest.yaml

3. **Block 3 - SD-WAN Blueprint**
   - [ ] Fix `fortigate-sdwan-spoke-template` argument parsing
   - [ ] Create `fortigate-config-push` tool OR fix spoke-template
   - [ ] Complete config push to sdwan-spoke-02

### Priority 2: Complete Block 3
- Push generated config to 10.0.0.35
- Verify IPsec tunnel negotiates with hub
- Verify BGP peering establishes

### Priority 3: Block 4 - Verification
- Full connectivity tests
- Health check validation

**Tools Verified This Session:**
| Tool | Status |
|------|--------|
| `fortigate-sdwan-manifest-tracker` | ✅ Works (absorb, update-license) |
| `fortigate-sdwan-blueprint-planner` | ✅ Works (generate-template, plan-site) |
| `fortigate-onboard` | ⚠️ Works but wrong creds path |
| `fortiflex-token-create` | ✅ Works |

---

## Known Issues / Gotchas

| Issue | Solution |
|-------|----------|
| FortiOS lacks virtio disk drivers at boot | Use `bus=scsi` with `virtio-scsi` controller |
| First login requires password set twice | Console automation must handle double password prompt |
| SSH password was wrong initially | Correct password: `{{REDACTED}}` |
| Base image path was `/tmp/fortios.qcow2` | Updated to `/home/libvirt/images/fortios-7.6.5-base.qcow2` |

---

## Commands Reference

### Hypervisor SSH
```bash
ssh root@10.0.0.100
# Password: {{REDACTED}}
```

### Check libvirt
```bash
virsh list --all
virsh net-list
```

### Provision Test VM (manual)
```bash
cd /home/libvirt/images
cp fortios-7.6.5-base.qcow2 test-spoke.qcow2
qemu-img resize test-spoke.qcow2 30G

virt-install --name test-spoke --vcpus 2 --memory 4096 \
  --disk path=test-spoke.qcow2,bus=scsi,format=qcow2 \
  --controller type=scsi,model=virtio-scsi \
  --network bridge=br0,model=virtio \
  --osinfo detect=on,require=off \
  --graphics vnc,listen=0.0.0.0 --noautoconsole --import
```

### Console Access
```bash
virsh console test-spoke
# Escape: Ctrl+]
```

### FortiGate First Login
```
login: admin
Password: <blank, press Enter>
You are forced to change your password. Please input a new password.
New Password: <enter new password>
Confirm Password: <enter again>
```
