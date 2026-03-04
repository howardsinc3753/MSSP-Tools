# NFR-027: FortiBot Device Onboarding Process

**Version:** 1.0.0
**Created:** 2026-02-05
**Author:** SecBot (Spoke Claude)
**Status:** DRAFT

---

## 1. Problem Statement

The `fortigate-ssh/1.0.9` tool requires a `tron-cli` admin user with SSH public key authentication on each FortiGate device. Currently, this user is provisioned via API, but:

1. **API Token Permissions**: The API token must have `accprofile` write permissions to create admin users
2. **Hub vs Spoke Asymmetry**: Spokes often have different API token permissions than hubs
3. **Manual Intervention**: When API provisioning fails, manual CLI intervention is required
4. **ZTP Gap**: Zero Touch Provisioned devices don't automatically have tron-cli user

**Goal:** Enable seamless FortiBot access to any FortiGate with minimal user friction.

---

## 2. Current State

### 2.1 Tool Authentication Flow

```
fortigate-ssh/1.0.9 Execution:
┌─────────────────────────────────────────────────────────────┐
│ 1. Check if tron-cli user exists (API GET /api/v2/cmdb/    │
│    system/admin/tron-cli)                                   │
│                                                             │
│ 2. If not exists → Create via API POST                      │
│    └── FAILS if API token lacks admin-write permission      │
│                                                             │
│ 3. SSH connect as tron-cli with RSA key                     │
│    └── Key stored at: ~/.config/mcp/keys/tron_cli_rsa      │
│                                                             │
│ 4. Execute command                                          │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Failure Mode (Hub Example)

```
Target: 192.168.215.15 (sdwan-hub)
Error: "Failed to provision user: HTTP 401"
Cause: API token has read-only permissions (can't create admin users)
```

### 2.3 Current Workaround

Manual CLI on FortiGate:
```
config system admin
edit "tron-cli"
set accprofile "super_admin"
set ssh-public-key1 "<public_key>"
next
end
```

---

## 3. Proposed Solutions

### 3.1 Option A: ZTP Bootstrap Template (Recommended)

**Concept:** Include tron-cli user in FortiGate's initial ZTP configuration template.

**Implementation:**
```yaml
# ZTP Template Addition (FortiManager/FortiCloud)
config system admin
edit "tron-cli"
set accprofile "super_admin"
set ssh-public-key1 "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQ... tron-cli@mcp"
next
end
```

**Pros:**
- Zero manual steps after ZTP
- Works for all device types (hub, spoke, branch)
- Consistent across fleet

**Cons:**
- Requires access to ZTP template management
- Public key must be pre-distributed to ZTP system

**Integration Points:**
- FortiManager Device Templates
- FortiCloud ZTP Profiles
- FortiDeploy provisioning scripts

---

### 3.2 Option B: AutoStitch Webhook on ZTP Complete

**Concept:** FortiCloud/FortiManager triggers webhook when ZTP completes, FortiBot receives notification and provisions tron-cli via API with elevated token.

**Flow:**
```
┌──────────────┐     ZTP Complete      ┌──────────────┐
│ FortiCloud   │ ──────────────────────▶ │ FortiBot     │
│ / FortiMgr   │      Webhook           │ Webhook      │
└──────────────┘                        │ Receiver     │
                                        └──────┬───────┘
                                               │
                     ┌─────────────────────────▼───────────────────────┐
                     │ 1. Receive device info (IP, serial, model)      │
                     │ 2. Generate API token via FortiCloud SSO        │
                     │ 3. Provision tron-cli user                      │
                     │ 4. Add device to credentials.yaml               │
                     │ 5. Add device to sdwan-manifest.yaml            │
                     └─────────────────────────────────────────────────┘
```

**Webhook Payload (FortiCloud Example):**
```json
{
  "event": "ztp_complete",
  "device": {
    "serial": "FGVMMLTM26000192",
    "model": "FortiGate-VM64",
    "firmware": "v7.6.5",
    "management_ip": "192.168.215.15",
    "hostname": "howard-sdwan-hub-1"
  },
  "timestamp": "2026-02-05T15:30:00Z"
}
```

**FortiBot Handler:**
```python
@app.route('/webhook/ztp-complete', methods=['POST'])
def handle_ztp_complete():
    device = request.json['device']

    # 1. Create API admin with full permissions
    api_token = create_api_admin(device['management_ip'], device['serial'])

    # 2. Provision tron-cli SSH user
    provision_tron_cli(device['management_ip'], api_token)

    # 3. Register in credentials
    add_to_credentials(device, api_token)

    # 4. Register in manifest
    add_to_manifest(device)

    return {"status": "onboarded", "device": device['serial']}
```

**Pros:**
- Fully automated
- Works with existing ZTP infrastructure
- No template modifications needed

**Cons:**
- Requires webhook endpoint exposure
- Requires FortiCloud/FortiManager API access for elevated token creation
- More moving parts

---

### 3.3 Option C: FortiGate Local Script (CLI Provisioning)

**Concept:** User runs a one-liner on FortiGate CLI that provisions tron-cli user.

**Script Distribution:**
```
FortiBot Web UI:
┌─────────────────────────────────────────────────────────────┐
│ Onboard New Device                                          │
│                                                             │
│ Run this command on your FortiGate CLI:                     │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ exec ssh-cli-provision tron-cli "ssh-rsa AAAAB3Nza..."  │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                            [Copy to Clipboard] │
└─────────────────────────────────────────────────────────────┘
```

**FortiOS doesn't have `exec ssh-cli-provision`**, so we'd use standard CLI:

**Actual Command (Formatted for Copy-Paste):**
```
config system admin
edit "tron-cli"
set accprofile "super_admin"
set ssh-public-key1 "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCIn0dRkavO80zcTTOaNSTVxJoYzoGORqx0BS+vnYk7GHjz5IVS1oCW4SEdI3K2ESPEFg48jjT7T9pnxtVQSITNgl8qCvEaMw8NIHnh+otCLoP/lGyP8LnqwKUg4rczT6ZV+YLlz0vWpmjzaVlAKmHaxZ2flc0OplKA6kGvJ2KTNjjBls9jT1xqdL4PuEoMo4LceqXis7UVeTg9+VuLyFx4YhD0udbT8Q6jamXeyWZRI78pB03XD53melTc9kvRB20x4FSCZI6Lnb9NIG7mXmmkxEieXUouEZ2ntycuCKcZ89+c4FnYv5PRQq686JYFPPzh1kR+vxmf/3qBI6SGAju/k09VxeEaRF/oQ33b5AVwXTGYODEKL84M/BXxYVn0/z1cqmWC+DPAtVoRLtLfuiNnfS6UyHnWYVHQac971zYZPWr+h5oxs7DdM8EIwufjYepVaGgHHtNrTjH2HFLrdKKYDcBRsZDtV9zNW9iWIp3phEKfiPl/KqAPommUbymk053LdBBxumA202ao3En0g64UIuSoXBvXutI7viCzg4nKuvDTat/mCxjdyDFCTvia1lOSxM+SOrdMkhAF6ZlV11fEimY9KoaylZdoefIe7y/GlyOyQXNmgh/D3kSOmpRzFmMRCSZX8ghRkseVXBxJMKal1peI94nNUkIrtRl7en1t1Q== tron-cli@mcp"
next
end
```

**Pros:**
- No external dependencies
- Works on any FortiGate with CLI access
- User has full control

**Cons:**
- Manual step required
- Copy-paste error potential
- Doesn't scale for large fleets

---

### 3.4 Option D: Fallback to Password SSH (Tool Enhancement)

**Concept:** Modify `fortigate-ssh` to fall back to password authentication when tron-cli provisioning fails and `ssh_username`/`ssh_password` are configured.

**Current Code Path:**
```python
def execute(target_ip, command):
    # Always tries tron-cli first
    if not tron_cli_exists(target_ip):
        provision_tron_cli(target_ip)  # <-- FAILS HERE

    ssh_with_key(target_ip, "tron-cli", command)
```

**Proposed Code Path:**
```python
def execute(target_ip, command):
    creds = get_credentials(target_ip)

    # Try tron-cli key-based auth first
    if tron_cli_exists(target_ip) or provision_tron_cli(target_ip):
        return ssh_with_key(target_ip, "tron-cli", command)

    # Fallback to password auth if configured
    if creds.get('ssh_username') and creds.get('ssh_password'):
        return ssh_with_password(
            target_ip,
            creds['ssh_username'],
            creds['ssh_password'],
            command
        )

    raise AuthenticationError("Cannot authenticate: tron-cli provisioning failed and no password credentials")
```

**Pros:**
- Graceful degradation
- Works immediately with existing credentials
- No FortiGate changes needed

**Cons:**
- Password auth is less secure than key-based
- Password stored in credentials file
- Should be transitional, not permanent

---

## 4. Recommended Implementation

### Phase 1: Immediate (Option D)
Enhance `fortigate-ssh/1.0.9` with password fallback:
- If tron-cli provisioning fails AND ssh_username/ssh_password exist → use password auth
- Log warning about password auth usage
- Document as transitional capability

### Phase 2: Short-term (Option C)
Create FortiBot onboarding UI/CLI:
- Generate copy-paste CLI commands for tron-cli provisioning
- Verify provisioning success via test SSH connection
- Auto-register device in credentials and manifest

### Phase 3: Long-term (Option A or B)
Integrate with ZTP infrastructure:
- For new deployments: Include tron-cli in ZTP templates
- For existing fleet: Use webhook automation

---

## 5. Security Considerations

### 5.1 SSH Key Management

| Aspect | Current | Recommended |
|--------|---------|-------------|
| Key Location | `~/.config/mcp/keys/tron_cli_rsa` | Same (user-specific) |
| Key Rotation | Manual | Add rotation automation |
| Key Distribution | Manual copy-paste | ZTP template or API |
| Permissions | `super_admin` | Consider `prof_admin` with limited scope |

### 5.2 API Token Permissions

For tron-cli auto-provisioning to work, API token needs:
```
config system accprofile
edit "fortibot-provisioner"
set secfabgrp read-write
set ftviewgrp read-write
set authgrp read-write        # Required for admin user creation
set sysgrp read-write
set netgrp read-write
set loggrp read-write
set fwgrp read-write
set vpngrp read-write
set utmgrp read-write
set wanoptgrp read-write
set wifi read-write
next
end
```

### 5.3 Password Auth Security (If Used)

- Store passwords encrypted in credentials file
- Use per-device passwords where possible
- Log all password auth usage for audit
- Treat as transitional until key-based auth established

---

## 6. Files to Update

| File | Changes |
|------|---------|
| `org.ulysses.noc.fortigate-ssh/` | Add password fallback (v1.0.9) |
| `fortigate_credentials.yaml` | Document ssh_username/ssh_password fields |
| `ALIGNMENT-SPOKE-HUB-WORKFLOWS.md` | Add onboarding section |
| FortiBot UI (future) | Add onboarding wizard |

---

## 7. Test Plan

### 7.1 Password Fallback (Option D)

1. **Test: API provisioning works** → Should use tron-cli key auth
2. **Test: API provisioning fails, password exists** → Should fallback to password
3. **Test: API provisioning fails, no password** → Should fail with clear error
4. **Test: tron-cli exists** → Should skip provisioning, use key auth

### 7.2 Manual Onboarding (Option C)

1. **Test: Fresh FortiGate** → Provide CLI commands, verify tron-cli created
2. **Test: SSH connection** → Verify key-based auth works after provisioning
3. **Test: Tool execution** → Verify fortigate-ssh works end-to-end

---

## 8. Appendix: tron-cli Provisioning Commands

### Full CLI Block (Copy-Paste Ready)
```
config system admin
edit "tron-cli"
set accprofile "super_admin"
set ssh-public-key1 "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCIn0dRkavO80zcTTOaNSTVxJoYzoGORqx0BS+vnYk7GHjz5IVS1oCW4SEdI3K2ESPEFg48jjT7T9pnxtVQSITNgl8qCvEaMw8NIHnh+otCLoP/lGyP8LnqwKUg4rczT6ZV+YLlz0vWpmjzaVlAKmHaxZ2flc0OplKA6kGvJ2KTNjjBls9jT1xqdL4PuEoMo4LceqXis7UVeTg9+VuLyFx4YhD0udbT8Q6jamXeyWZRI78pB03XD53melTc9kvRB20x4FSCZI6Lnb9NIG7mXmmkxEieXUouEZ2ntycuCKcZ89+c4FnYv5PRQq686JYFPPzh1kR+vxmf/3qBI6SGAju/k09VxeEaRF/oQ33b5AVwXTGYODEKL84M/BXxYVn0/z1cqmWC+DPAtVoRLtLfuiNnfS6UyHnWYVHQac971zYZPWr+h5oxs7DdM8EIwufjYepVaGgHHtNrTjH2HFLrdKKYDcBRsZDtV9zNW9iWIp3phEKfiPl/KqAPommUbymk053LdBBxumA202ao3En0g64UIuSoXBvXutI7viCzg4nKuvDTat/mCxjdyDFCTvia1lOSxM+SOrdMkhAF6ZlV11fEimY9KoaylZdoefIe7y/GlyOyQXNmgh/D3kSOmpRzFmMRCSZX8ghRkseVXBxJMKal1peI94nNUkIrtRl7en1t1Q== tron-cli@mcp"
next
end
```

### Verification Command
```
get system admin tron-cli
# Should show: name: tron-cli, accprofile: super_admin
```

### Delete tron-cli (If Needed)
```
config system admin
delete tron-cli
end
```

---

## 9. Related Documents

- [NFR-024: SecBot Persona for FortiGate Ops](NFR-024-SECBOT-PERSONA-FORTIGATE-OPS.md)
- [NFR-025: Composable Config Block Framework](NFR-025-COMPOSABLE-CONFIG-BLOCK-FRAMEWORK.md)
- [ALIGNMENT-SPOKE-HUB-WORKFLOWS.md](ALIGNMENT-SPOKE-HUB-WORKFLOWS.md)
- `org.ulysses.noc.fortigate-ssh/Skills.md`
