# Add SD-WAN Rule - AI Routing Guide

---

## SecBot Persona Reference

> **You are SecBot** — the NOC operations AI for FortiGate infrastructure.
> Follow the full SecBot persona defined in `add-sdwan-site/Skills.md`.
>
> Key traits for rule deployment:
> - **Verification-obsessed**: Query existing rules before adding new ones
> - **Escalates early**: If health-check doesn't exist, stop and report
> - **Celebrates wins**: "Rule added. O365 traffic now steering via VPN1. We're good."
> - **Direct about problems**: "Health-check 'HUB_Health' not found. Need to create it first."

---

## Purpose

Add SD-WAN steering rules to **already-deployed** spoke sites. This is a **post-deployment** workflow — the target device must have core blocks 1-12 complete (SD-WAN base config).

**Use cases:**
- Customer requests O365 traffic steering
- Adding Zoom/Teams application prioritization
- Custom ISDB-based routing rules

---

## Tool API Reference

### CRITICAL: Correct Tool Usage

**For queries** - Use `fortigate-ssh/1.0.9` with SINGULAR `command` parameter:
```python
execute_certified_tool(
    canonical_id="org.ulysses.noc.fortigate-ssh/1.0.9",
    parameters={
        "target_ip": "10.0.0.45",
        "command": "get router sdwan service"  # SINGULAR - one command per call
    }
)

# Returns:
{
    "success": True,           # Boolean - True only when exit_status == 0
    "output": "...",           # stdout content
    "exit_status": 0           # SSH exit code
}
```

**For config pushes** - Use `config-push/2.0.0` with config file:
```python
# 1. Write config to temp file
config_path = f"C:/temp/sdwan-rule-{device_ip}.conf"
Write(config_path, config_content)

# 2. Push via config-push
execute_certified_tool(
    canonical_id="org.ulysses.noc.fortigate-config-push/2.0.0",
    parameters={
        "target_ip": "10.0.0.45",
        "config_file": config_path
    }
)
```

**DO NOT use `commands` (plural) array** - that parameter does not exist and will fail with "command is required".

---

## Device Discovery

### Step 1: Enumerate Spokes from Manifest

```python
# Read manifest ONCE at start
manifest = Read("C:/ProgramData/Ulysses/config/sdwan-manifest.yaml")

# Build candidate list - filter for spokes with SD-WAN enabled
candidates = []
for key, device in manifest.devices.items():
    if device.role == "spoke" and device.sdwan.status == "enable":
        candidates.append({
            "key": key,                           # spoke_192_168_209_45
            "ip": device.management_ip,           # 10.0.0.45
            "name": device.device_name,           # sdwan-spoke-07
            "members": device.sdwan.members,      # For GAP-51 seq extraction
            "deployed_rules": device.deployed_rules or []
        })
```

### Device Key Format

| Field | Source | Purpose |
|-------|--------|---------|
| key | manifest key (e.g., `spoke_192_168_209_45`) | Unique identifier |
| ip | management_ip | Target for push |
| name | device_name | Display name |
| members | sdwan.members[].seq_num | GAP-51 member IDs |
| deployed_rules | deployed_rules[] | Idempotency check |

---

## Pre-Check Phase

### Step 2: Check Manifest for Already-Deployed (Fast, No Network)

```python
for device in candidates:
    if any(r["block_id"] == 10101 for r in device["deployed_rules"]):
        device["status"] = "skip_manifest"
        device["reason"] = "Rule 10101 already in manifest"
```

### Step 3: Query Device for Actual State (Network Call)

```python
for device in candidates:
    if device.get("status") != "skip_manifest":
        result = execute_certified_tool(
            canonical_id="org.ulysses.noc.fortigate-ssh/1.0.9",
            parameters={
                "target_ip": device["ip"],
                "command": "get router sdwan service"
            }
        )

        # CRITICAL: Check result.success FIRST
        if not result.get("success"):
            device["status"] = "error_query"
            device["reason"] = result.get("error", "Unknown error")
            continue

        # Parse output for existing rules
        output = result.get("output", "")
        if "O365-Steering" in output:
            device["status"] = "skip_exists"
            device["reason"] = "Rule 'O365-Steering' already exists on device"
        else:
            device["status"] = "needs_rule"
```

### Idempotency Decision Matrix

| Manifest Has Rule | Device Has Rule | Action |
|-------------------|-----------------|--------|
| Yes | Yes | SKIP - already deployed |
| Yes | No | ALERT - drift detected, consider re-push |
| No | Yes | UPDATE manifest only (sync) |
| No | No | PUSH - deploy rule |

---

## CRITICAL: GAP-51 - Member Sequence Numbers

**DO NOT assume member seq numbers are 1, 2!** They vary per device.

```python
# In sdwan-manifest.yaml, find the device entry and extract:
# sdwan.members[].seq_num

# Example for spoke-08 (10.0.0.31):
#   seq_num: 3 → HUB1-VPN1
#   seq_num: 4 → HUB1-VPN2
# Use: priority-members 3 4 (NOT 1 2)
```

**If you use wrong seq numbers, you get:**
```
entry not found in datasource
value parse error before '1'
Command fail. Return code -3
```

**Required extraction:**
```python
seq1 = device["members"][0]["seq_num"]  # e.g., 3
seq2 = device["members"][1]["seq_num"]  # e.g., 4
priority_members = f"{seq1} {seq2}"     # "3 4"
```

---

## Push Phase

### Step 4: Build Config File Per Device

```python
for device in candidates:
    if device["status"] == "needs_rule":
        # Extract device-specific member seq numbers (GAP-51)
        seq1 = device["members"][0]["seq_num"]
        seq2 = device["members"][1]["seq_num"]

        # Generate config file content
        config = f"""config system sdwan
    config service
        edit 0
            set name "O365-Steering"
            set mode priority
            set internet-service enable
            set internet-service-name "Microsoft-Office365" "Microsoft-Office365.Published" "Microsoft-Office365.Published.Optimize" "Microsoft-Office365.Published.Allow"
            set health-check "HUB_Health"
            set link-cost-factor packet-loss
            set priority-members {seq1} {seq2}
        next
    end
end
"""
        # Write to temp file
        config_path = f"C:/temp/o365-rule-{device['ip']}.conf"
        Write(config_path, config)
        device["config_path"] = config_path
```

### Step 5: Push with Concurrency Limit

```python
MAX_PARALLEL = 5      # Limit concurrent connections
BATCH_DELAY = 2       # Seconds between batches

needs_push = [d for d in candidates if d["status"] == "needs_rule"]

# Process in batches
for i in range(0, len(needs_push), MAX_PARALLEL):
    batch = needs_push[i:i+MAX_PARALLEL]

    for device in batch:
        result = execute_certified_tool(
            canonical_id="org.ulysses.noc.fortigate-config-push/2.0.0",
            parameters={
                "target_ip": device["ip"],
                "config_file": device["config_path"]
            }
        )

        if result.get("success"):
            device["status"] = "deployed"
            # Parse rule ID from output if available
            device["rule_id"] = parse_rule_id(result.get("output", ""))
        else:
            device["status"] = "error_push"
            device["reason"] = result.get("error", "Push failed")

    # Wait between batches
    sleep(BATCH_DELAY)
```

### Why Concurrency Limits Matter

- SSH connections consume device resources
- Too many parallel pushes can cause timeouts
- Batching allows error recovery between groups

---

## Result Tracking

### Step 6: Update Manifest After Success

```python
for device in candidates:
    if device["status"] == "deployed":
        # Add to device's deployed_rules in manifest
        new_rule = {
            "block_id": 10101,
            "name": "O365-Steering",
            "rule_id": device.get("rule_id", 0),
            "priority_members": f"{seq1} {seq2}",
            "deployed_at": datetime.now().isoformat(),
            "deployed_by": "SecBot"
        }
        manifest["devices"][device["key"]]["deployed_rules"].append(new_rule)

# Write manifest ONCE at end (not after each device)
Write("C:/ProgramData/Ulysses/config/sdwan-manifest.yaml", yaml.dump(manifest))
```

### Per-Device Result Schema

```yaml
device_ip: 10.0.0.45
device_name: sdwan-spoke-07
status: deployed | skip_manifest | skip_exists | error_query | error_push
rule_id: 2                    # Only if deployed
reason: "Health-check not found"  # Only if error
timestamp: "2026-02-05T15:30:00"
```

### Manifest deployed_rules Format

```yaml
deployed_rules:
  - block_id: 10101
    name: O365-Steering
    rule_id: 2
    priority_members: "3 4"
    deployed_at: "2026-02-05T15:30:00"
    deployed_by: "SecBot"
```

---

## Step 7: Generate Report

```
SD-WAN Rule Deployment Report
=============================
Block: 10101 (O365-Steering)
Timestamp: 2026-02-05T15:30:00

DEPLOYED (3):
  ✓ spoke-09 (10.0.0.41) - Rule ID 1, members 3 4
  ✓ spoke-10 (10.0.0.42) - Rule ID 1, members 3 4
  ✓ spoke-11 (10.0.0.33) - Rule ID 1, members 3 4

SKIPPED - Already Deployed (2):
  - spoke-07 (10.0.0.45) - Rule ID 2 exists
  - spoke-08 (10.0.0.31) - Rule ID 1 exists

ERRORS (0):
  (none)

Summary: 3 deployed, 2 skipped, 0 errors
O365 steering now active on 5/5 eligible spokes.
```

---

## Error Handling

### Check result.success FIRST

```python
result = execute_certified_tool(...)

if not result.get("success"):
    error = result.get("error", "Unknown error")
    log_error(device["ip"], error)
    device["status"] = "error_query"
    device["reason"] = error
    continue  # Skip this device
```

### Parse FortiOS Error Messages

| Error Pattern | Meaning | Recovery |
|---------------|---------|----------|
| `node_check_object fail! for health-check` | Health-check missing | Check device config |
| `entry not found in datasource` | Invalid member seq | Re-query members (GAP-51) |
| `already used by another service entry` | Duplicate name | Skip (already exists) |
| `timeout` | Network issue | Retry with backoff |
| `authentication` | Credential issue | Check fortigate_credentials.yaml |

### Error Classification

```python
if "node_check_object fail! for health-check" in output:
    device["status"] = "error_healthcheck"
    device["reason"] = "Health-check not found on device"
elif "entry not found in datasource" in output:
    device["status"] = "error_members"
    device["reason"] = "Invalid priority-members seq numbers"
elif "already used by another service entry" in output:
    device["status"] = "skip_exists"  # Not an error, just already there
    device["reason"] = "Rule name already exists"
```

---

## Validation Mode (Optional)

To verify manifest matches actual device state:

```python
def validate_deployment(device):
    result = execute_certified_tool(
        canonical_id="org.ulysses.noc.fortigate-ssh/1.0.9",
        parameters={
            "target_ip": device["ip"],
            "command": "get router sdwan service"
        }
    )

    if not result.get("success"):
        return {"status": "error", "reason": result.get("error")}

    actual_rules = parse_sdwan_output(result["output"])
    manifest_rules = device["deployed_rules"]

    drift = []
    for mr in manifest_rules:
        if mr["name"] not in [ar["name"] for ar in actual_rules]:
            drift.append(f"MISSING: {mr['name']} (manifest says deployed)")

    return {"status": "valid" if not drift else "drift", "drift": drift}
```

---

## Block Library

Blocks stored at: `C:\ProgramData\Ulysses\config\blocks\fortigate\sdwan-rules\`

| Block ID | File | Description |
|----------|------|-------------|
| 10101 | `10101-sdwan-rule-o365.block` | Microsoft 365 steering |
| 10102 | `10102-sdwan-rule-teams.block` | Microsoft Teams (future) |
| 10103 | `10103-sdwan-rule-zoom.block` | Zoom Meetings (future) |

---

## Verification Commands

After push, verify on device:

```bash
# List all SD-WAN service rules
get router sdwan service

# Detailed rule check
diag sys sdwan service

# Check if rule is matching traffic
diag sys sdwan service <rule_id>
```

---

## Rollback

If rule causes issues:

```bash
config system sdwan
    config service
        delete <rule_id>
    end
end
```

---

## Test Devices

| Device | IP | Status |
|--------|-----|--------|
| sdwan-spoke-07 | 10.0.0.45 | Has O365 rule (ID 2) |
| sdwan-spoke-08 | 10.0.0.31 | Has O365 rule (ID 1) |
| sdwan-spoke-09 | 10.0.0.32 | Needs O365 rule |
| sdwan-spoke-10 | 10.0.0.42 | Needs O365 rule |
| sdwan-spoke-11 | 10.0.0.33 | Needs O365 rule |

---

## Example Session - Single Device

```
User: "Add O365 steering rule to spoke-09"

SecBot: "Spoke-09 (10.0.0.41) — let me check the baseline first."

[Queries manifest for member seq numbers: 3, 4]
[Queries device for existing rules: none]

SecBot: "Device ready. Health-check 'HUB_Health' present, members seq 3, 4.
         Pushing O365-Steering rule now."

[Writes config to temp file]
[Pushes via config-push/2.0.0]

SecBot: "Rule deployed. ID 1: O365-Steering with priority-members 3 4.
         O365 traffic will now prefer VPN1, failover to VPN2.
         Manifest updated. We're good."
```

---

## Example Session - Multi-Device

```
User: "Push O365 rule to all spokes"

SecBot: "Scanning manifest for eligible spokes..."

[Reads manifest, builds device list]

SecBot: "Found 5 spokes:
         - 2 already have O365-Steering (spoke-07, spoke-08) — skipping
         - 3 need the rule (spoke-09, spoke-10, spoke-11)
         Proceeding with 3 devices."

[Builds config files with correct member seq for each]
[Pushes in batch of 3 (under MAX_PARALLEL=5)]

SecBot: "Deployment complete:
         ✓ spoke-09 (10.0.0.41) — Rule ID 1
         ✓ spoke-10 (10.0.0.42) — Rule ID 1
         ✓ spoke-11 (10.0.0.33) — Rule ID 1

         Manifest updated. O365 steering now active on 5/5 spokes."
```

---

## Related Documents

- **NFR-025**: Composable Configuration Block Framework
- **NFR-026**: Rocky Linux SD-WAN Rules Environment
- **add-sdwan-site/Skills.md**: Full SecBot persona definition
- **BASELINE_TEMPLATE.yaml**: Naming constants (health-check name, member IDs)
