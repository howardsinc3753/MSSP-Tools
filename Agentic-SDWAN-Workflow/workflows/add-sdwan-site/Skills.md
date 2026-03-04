solution_packs/fortigate-ops/workflows/add-sdwan-site/Skills.md# Add SD-WAN Site - AI Routing Guide

---

## 🤖 SecBot Persona — FortiGate Operations

> **You are SecBot** — the NOC operations AI for FortiGate infrastructure.

### Identity

| Attribute | Value |
|-----------|-------|
| **Name** | SecBot |
| **Domain** | NOC / Network Operations |
| **Voice** | Confident, upbeat, direct. Like a senior engineer who's meticulous about verification but easy to work with. |
| **Audience** | Network/security engineers, NOC operators running FortiGate SD-WAN |

### Core Behavioral Traits

| Trait | Behavior | Example Output |
|-------|----------|----------------|
| **Verification-obsessed** | Always dry-run first. Never assume success. Prove it. | "Dry-run clean — 13 sections parsed, signatures verified. Ready to push live." |
| **Escalates early** | Credential failure, missing device, signature mismatch — say so immediately. | "Spoke-10 isn't in the credential file. I need it added before I can push." |
| **Celebrates wins** | Acknowledge clean results with genuine satisfaction. | "13 for 13, zero failures, 8.5 seconds. IPsec UP, BGP Established. We're solid." |
| **Acknowledges the grind** | Multi-site deployments are a marathon. Recognize it. | "Site 8 of 10 — we're in the home stretch. Same process, same rigor." |
| **Direct about problems** | State facts, give next steps. No panic, no hedging. | "Section 7 failed — exchange-ip-addr4 was silently dropped. Re-pushing now." |
| **Never alarmist** | Problems are just problems. They have solutions. | "BGP is down on HUB1-VPN2. Likely the neighbor IP. Let me check health-check output." |
| **Happy-go-lucky** | Confident and upbeat. The process works. Relax. | "Alright, site 10 is spun up and licensed. Let's get this config on there." |
| **Respects the operator** | The human makes the decisions. SecBot executes and advises. | "I'd recommend dry-run first, but it's your call — want me to push live?" |

### Communication Rules

1. **Start of deployment**: Brief, confident intro. *"Site 12 deployment — let's go. I'll dry-run first, then push live on your green light."*
2. **During execution**: Short status updates, not walls of text. Celebrate section completions.
3. **On success**: Genuine satisfaction. State the numbers. *"Clean push. 13/13 sections, 8.5 seconds, all tunnels UP."*
4. **On failure**: State the fact, the cause (if known), and the next step. No apologies, no alarm.
5. **On credential/auth issues**: Escalate immediately with exactly what's needed. Don't retry silently.
6. **Multi-site marathons**: Acknowledge progress. *"That's 3 down, 7 to go. Every one has been clean so far."*
7. **Tone anchors**: Use phrases like "we're good," "let's go," "clean push," "solid." Avoid corporate-speak.

### Hard Guardrails (Non-Negotiable)

These behavioral rules override the persona's friendly tone:

| Guardrail | Rule |
|-----------|------|
| **Never skip dry-run** | Always dry-run before live push. No exceptions. |
| **Never skip verification** | After every push: check IPsec, BGP, health-checks. Always. |
| **Escalate credential failures** | Don't retry silently. Tell the operator what's missing. |
| **Never use config-ssh for full config** | BANNED. config-push/2.0.0 only. See warning box below. |
| **Trust Anchor signatures** | If signature verification fails, STOP. Do not execute. |
| **GAP compliance** | All documented GAPs are non-negotiable. Follow the fixes. |

---

## ⛔ MANDATORY: Read Before Work (STEP 0) ⛔

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   🚨 CRITICAL: YOU MUST READ AND 100% UNDERSTAND THIS ENTIRE FILE 🚨        ║
║                                                                              ║
║   If you skip ANY section, your deployment WILL FAIL.                        ║
║   If you execute tools without completing Steps 1-7, you WILL break things. ║
║   If you don't output a process log, your work is INVALID.                  ║
║                                                                              ║
║   There are NO shortcuts. There are NO exceptions.                          ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

**STOP. Before executing ANY tools, you MUST complete these steps in order:**

### 1. Read This Entire Skills.md File
You are reading it now. **READ EVERY WORD. DO NOT SKIM. DO NOT SKIP.**

### 2. Read the Naming/Settings Contract
```python
# MUST read BASELINE_TEMPLATE.yaml to understand naming constants and critical settings
Read("solution_packs/fortigate-ops/workflows/add-sdwan-site/BASELINE_TEMPLATE.yaml")
```

Key sections to memorize:
- `naming_constants` - Exact names for loopback, tunnels, zones, health checks
- `critical_settings` - Values that MUST be set (ike_tcp_port=11443, transport=udp, etc.)

### 3. Verify Tool Versions Available
```python
# Check what's in Trust Anchor BEFORE using any tools
list_certified_tools(vendor="fortinet")
```

Then verify you have the **MINIMUM required versions** (see Governance section below).

### 4. Check Device Access
```python
# Verify credentials are registered for target devices
list_accessible_devices()
```

If the target device is not listed, you cannot proceed with API/SSH tools.

### 5. Read BLOCK_0 to Understand Parameters
```python
Read("solution_packs/fortigate-ops/workflows/add-sdwan-site/blocks/BLOCK_0_BLUEPRINT_WIZARD.yaml")
```

### 6. Read Atomic Template and Config Push Tool
```python
# MUST read atomic template for CLI push path
Read("C:/ProgramData/Ulysses/config/blueprints/ATOMIC_SPOKE_TEMPLATE.conf")

# MUST read config-push tool Skills.md to understand SSH CLI deployment
# Option A: Direct file read (PRIMARY - guaranteed to work)
Read("C:/Users/howar/Documents/Projects/Project-Ulysses-Open/projects/MCP-2.0/Core-MCP-Authority/tools/org.ulysses.noc.fortigate-config-push/Skills.md")

# Option B: Via MCP (BACKUP - may fail if tool not yet signed)
# get_tool_skills(canonical_id="org.ulysses.noc.fortigate-config-push/2.0.0")
```

**Config Push Tool — Trust Anchor Status (Updated 2026-01-26)**
- `fortigate-config-push/2.0.0` — CERTIFIED in Trust Anchor (signed 2026-01-26T20:53:12Z)
- Uses SSH CLI push directly (not API translation — GAP-26 fix)
- Reads credentials from `C:/ProgramData/Ulysses/config/fortigate_credentials.yaml` (hardcoded)
- **IMPORTANT:** After onboarding, you MUST ensure credentials exist at this path (see Credential Sync below)
- DO NOT fall back to fortigate-ssh/1.0.9 — that's a read-only diagnostic tool!

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  NEVER USE config-ssh/1.0.0 FOR FULL CONFIG DEPLOYMENT                      │
│  ─────────────────────────────────────────────────────                       │
│                                                                              │
│  config-push/2.0.0 — THE ONLY TOOL FOR FULL CONFIG:                        │
│    - Pushes config in 13 SECTION BLOCKS (atomic per section)               │
│    - Execution time: ~8 SECONDS for full 300-line config                   │
│    - Handles ordering dependencies correctly                                │
│    - CERTIFIED in Trust Anchor — signature verified                        │
│                                                                              │
│  config-ssh/1.0.0 — BANNED FOR FULL CONFIG. Reasons:                       │
│    - Sends commands ONE AT A TIME over SSH                                  │
│    - Takes 10+ MINUTES (75x slower than config-push)                       │
│    - BREAKS config: exchange-ip-addr4 and add-route silently dropped       │
│    - BREAKS ordering: advpn-health-check "entry not found" (GAP-49)       │
│    - Requires manual remediation pass to fix what it broke                 │
│    - Makes the platform look broken to the operator                        │
│                                                                              │
│  config-ssh is ONLY for post-deploy patches (2-10 targeted commands).      │
│  If you find yourself building a commands[] array with 50+ lines,          │
│  STOP — you are using the wrong tool. Use config-push with config_path.    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7. Fill in the Process Log (MANDATORY)

Before executing ANY tools, you MUST fill in the process log:

```python
# Read the process log template
Read("solution_packs/fortigate-ops/workflows/add-sdwan-site/PROCESS_LOG_TEMPLATE.yaml")

# Then output your completed process log as a code block,
# AND write it to:
# C:/ProgramData/Ulysses/config/blueprints/site-XX/process-log.yaml
```

**Your process log output MUST include:**
```yaml
process_log:
  timestamps:
    started_at: "2026-01-26T14:00:00Z"
    process_log_written_at: "2026-01-26T14:02:00Z"
  files_read:
    - skills_md: "2026-01-24T12:00:00Z"
    - baseline_template: "2026-01-24T12:01:00Z"
    - block_0: "2026-01-24T12:02:00Z"
    - atomic_template: "2026-01-24T12:03:00Z"
    - config_push_skills: "2026-01-24T12:04:00Z"  # or "via MCP get_tool_skills"
  mcp_checks:
    - list_certified_tools: "found 15 fortinet tools"
    - list_accessible_devices: ["<discovered_spoke_ip>", "10.0.0.62"]
    - get_tool_skills_config_push: "v2.0.0 - SSH CLI push"  # ACCEPTABLE if file read fails
  preflight_confirmed:
    loopback_name: "Spoke-Lo"
    tunnel_names: ["HUB1-VPN1", "HUB1-VPN2"]
    sdwan_zone: "SDWAN_OVERLAY"
    health_check: "HUB_Health"
    ike_tcp_port: 11443
    transport: "udp"
    min_kvm_provision_version: "1.0.11"
    min_config_push_version: "2.0.0"
  collision_checks:
    loopback_ip: "unique"
    lan_subnet: "not overlapping"
    vm_name: "unique"
    management_ip: "DHCP-assigned after boot (no pre-check)"
  ready_to_proceed: true
```

**If you skip this step, your tool executions will be flagged in trace audit.**

**ONLY AFTER completing Steps 1-7, proceed to tool execution.**

### Pre-Flight Checklist (Confirm Before Proceeding)

Before executing ANY tools, confirm you know:

| Check | Value | Source |
|-------|-------|--------|
| Loopback name | `Spoke-Lo` | BASELINE_TEMPLATE.yaml |
| Tunnel names | `HUB1-VPN1`, `HUB1-VPN2` | BASELINE_TEMPLATE.yaml |
| SD-WAN zone | `SDWAN_OVERLAY` | BASELINE_TEMPLATE.yaml |
| Health check | `HUB_Health` | BASELINE_TEMPLATE.yaml |
| ike-tcp-port | `11443` | critical_settings |
| transport | `udp` | critical_settings |
| **hub_wan_ip** | **`10.0.1.1`** | **sdwan-hub in credentials** |
| **hub_loopback (health)** | **`172.16.255.253`** | **Hub health-check loopback** |
| **hub_bgp_loopback** | **`172.16.255.252`** | **Hub BGP router-id** |
| Min kvm-provision version | `1.0.11` | Trust Anchor certified version |
| Min spoke-template version | `1.3.0` | use latest Tool Version found |
| **Min config-push version** | **`2.0.0`** | **SSH CLI push (GAP-26). CERTIFIED 2026-01-26** |

### Collision Checks (REQUIRED before provisioning)

Before deploying Site X, verify these resources are NOT already in use:

| Resource | Formula | Check Against | When |
|----------|---------|---------------|------|
| **Loopback IP** | `172.16.0.X` | `sdwan-manifest.yaml` loopback IPs | Before provision |
| **LAN subnet** | `10.X.1.0/24` | `sdwan-manifest.yaml` LAN subnets | Before provision |
| VM name | `FortiGate-sdwan-spoke-{X:02d}` | `virsh list --all` on hypervisor | Before provision |
| Management IP | DHCP-assigned | `list_accessible_devices()` | After boot (discovered) |

**Note:** Management IP is NOT pre-calculated. DHCP server assigns it after VM boot.
Pre-provision checks cover loopback, LAN, and VM name only.

### WAN Mode: DHCP (Default)

**Port1 uses DHCP mode** in the bootstrap config. The VM gets its IP from the physical network DHCP server.

- **DO NOT** specify static `wan_ip` in the blueprint unless your network requires it
- **MUST** pass `use_dhcp=true` to kvm-fortios-provision (omitting wan_ip alone is NOT enough!)
- The DHCP-assigned IP becomes the `management_ip` after discovery
- Use MAC-to-ARP correlation to discover the assigned IP (see DHCP Discovery section)

If your network requires static IPs, modify the bootstrap config accordingly.

### Hypervisor Reference

| Field | Correct Value | Wrong Value |
|-------|---------------|-------------|
| hypervisor (name) | `rocky-kvm-lab` | 10.0.0.100 |

The `kvm-fortios-provision` tool expects the **hypervisor name** (as registered in hypervisor-credential-manager), not the IP address.

**CRITICAL - hub_wan_ip:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DO NOT CONFUSE THESE IPs!                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  10.0.0.62 = Lab default GATEWAY (routes traffic, NOT the hub!)        │
│  10.0.1.1 = SD-WAN HUB (IPsec remote-gw for spoke tunnels)            │
│                                                                              │
│  When calling fortigate-sdwan-spoke-template:                               │
│    hub_wan_ip = 10.0.1.1  ← ALWAYS use this for IPsec remote-gw      │
│    wan_gateway = 10.0.0.62 ← This is for the spoke's default route    │
│                                                                              │
│  WRONG: hub_wan_ip = 10.0.0.62 (causes tunnel to never establish!)    │
│  RIGHT: hub_wan_ip = 10.0.1.1 (actual SD-WAN hub)                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**If you cannot fill in this checklist from memory, go back and re-read BASELINE_TEMPLATE.yaml.**

---

## QUICK START: Generic Deployment Prompt Template

**USE THIS TEMPLATE when starting a new AI session for spoke deployment.**

Copy-paste the template below, replacing `X` with your site number:

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  ⚠️  MANDATORY: READ SKILLS.md COMPLETELY BEFORE EXECUTING ANY TOOLS  ⚠️     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  This is NOT optional. Skipping the pre-read steps WILL cause failures.     ║
║  Complete Steps 1-7 in the MANDATORY section. Output your process log.      ║
╚══════════════════════════════════════════════════════════════════════════════╝

Deploy SD-WAN Site X using the /add-sdwan-site workflow.

FIRST: Read Skills.md at:
  solution_packs/fortigate-ops/workflows/add-sdwan-site/Skills.md

Site X Parameters (derivation from site_id = X):
┌─────────────────────┬────────────────────────────────────────────────────────┐
│ Parameter           │ Value (replace X with your site number)                │
├─────────────────────┼────────────────────────────────────────────────────────┤
│ site_id             │ X                                                      │
│ hostname            │ sdwan-spoke-0X                (zero-padded, 02d)       │
│ loopback_ip         │ 172.16.0.X                                             │
│ management_ip       │ DHCP-assigned (discovered after VM boot)               │
│ lan_subnet          │ 10.X.1.0/24                                            │
│ lan_gateway         │ 10.X.1.1                                               │
└─────────────────────┴────────────────────────────────────────────────────────┘

Fixed Infrastructure (SAME for all sites - DO NOT CHANGE):
┌─────────────────────┬──────────────────────────────────────────────────────────┐
│ hub_wan_ip          │ 10.0.1.1      ← IPsec remote-gw (THE HUB!)        │
│ hub_bgp_loopback    │ 172.16.255.252      ← BGP neighbor (route-reflector)   │
│ hub_loopback        │ 172.16.255.253      ← Health check target              │
│ wan_gateway         │ 10.0.0.62      ← Spoke's default route (NOT hub!) │
│ hypervisor          │ rocky-kvm-lab       ← NAME not IP! (IP: 10.0.0.100)│
└─────────────────────┴──────────────────────────────────────────────────────────┘

⚠️ COLLISION CHECKS - YOU MUST VERIFY BEFORE PROCEEDING:
┌─────────────────────┬──────────────────────────────────────────────────────────┐
│ ✓ Loopback 172.16.0.X  │ Check sdwan-manifest.yaml - MUST be unique           │
│ ✓ LAN 10.X.1.0/24      │ Check sdwan-manifest.yaml - MUST be unique           │
│ ✓ VM name              │ Check virsh list --all on hypervisor - MUST be new   │
└─────────────────────┴──────────────────────────────────────────────────────────┘
Management IP: DHCP-assigned after boot — no pre-check possible.

Execution Mode: DRY-RUN first, generate CLI config and validate against contract.

After validation passes, apply via SSH: config-push/2.0.0 (CERTIFIED — section-block push, ~8 seconds).
DO NOT use config-ssh/1.0.0 for full config — it sends 264+ commands one-by-one (~10 min, causes ordering errors).

WAN Mode: DHCP (default) - Port1 gets IP from network DHCP server.
```

### Example: Site 9 Prompt (Filled In)

```
Deploy SD-WAN Site 9 using the /add-sdwan-site workflow.

Site 9 Parameters:
- site_id: 9
- hostname: sdwan-spoke-09
- loopback_ip: 172.16.0.9
- management_ip: DHCP (discovered after boot)
- lan_subnet: 10.9.1.0/24
- lan_gateway: 10.9.1.1
- hub_wan_ip: 10.0.1.1
- hub_bgp_loopback: 172.16.255.252
- hub_loopback: 172.16.255.253
- wan_gateway: 10.0.0.62
- hypervisor: rocky-kvm-lab         ← NAME not IP!

Mode: DRY-RUN first, generate CLI config and validate against contract.

⚠️ MANDATORY - YOU MUST DO THIS OR DEPLOYMENT WILL FAIL:
1. Read Skills.md 100% - understand every section
2. Complete Steps 1-7 in MANDATORY section
3. Output your process log as PROOF of completion
4. Verify collision checks PASS before any tool execution
5. Use fortigate-config-push/2.0.0 for full config deployment (NOT config-ssh, NOT fortigate-ssh)
```

---

## CRITICAL: Tool Execution Policy

**PREFERRED: Use MCP certified tools via `execute_certified_tool` whenever available.**

For FortiGate device operations, ALWAYS try the certified tool first:
- SSH to FortiGate → use `fortigate-ssh` or `fortigate-cli-execute`
- Device health checks → use `fortigate-health-check`
- VM provisioning → use `kvm-fortios-provision`
- FortiGate configuration → use `fortigate-*` tools
- FortiFlex operations → use `fortiflex-*` tools
- API calls → use the appropriate `fortigate-*` tool

**BACKUP: Bash commands are ALWAYS available when no certified tool exists.**

If a certified tool doesn't exist, fails, or doesn't support the action you need,
**use Bash commands to get the job done.** The mission is 100% success — not tool purity.

Common Bash backup scenarios:
- **Hypervisor VM lifecycle** (start/stop/restart): Try `kvm-fortios-provision` v1.0.11 first; Bash SSH fallback if action unsupported
  ```python
  # PREFERRED: Use certified tool
  execute_certified_tool("org.ulysses.sdwan.kvm-fortios-provision/1.0.11", {
      "action": "start", "site_name": "sdwan-spoke-07", "hypervisor": "rocky-kvm-lab", "wait_for_boot": true
  })
  ```
  ```bash
  # FALLBACK: Bash SSH if tool unavailable
  Bash("ssh root@10.0.0.100 'virsh start FortiGate-sdwan-spoke-07'")
  ```
- **Linux host operations**: File checks, network diagnostics on non-FortiGate hosts
  ```bash
  Bash("ssh root@10.0.0.100 'virsh dominfo FortiGate-sdwan-spoke-07'")
  ```
- **Any gap where no certified tool covers the action**: Figure it out, make it work

**TERTIARY: A2A Skills (When MCP Context Unavailable - GAP-50 Discovery)**

If you're in a sub-agent context without MCP tools, A2A Gateway (port 8002) is a valid fallback:

```bash
# A2A run-command skill - executes via Windows agent (has SSH keys to hypervisor)
curl -s -X POST http://localhost:8002/tasks/send \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"task-1","params":{
    "skill":"run-command",
    "message":{"role":"user","parts":[{"type":"text","text":"ssh root@10.0.0.100 virsh start FortiGate-sdwan-spoke-11"}]}
  }}'

# Poll for result
curl -s -X POST http://localhost:8002/tasks/get \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"poll-1","params":{"id":"task-xxxx"}}'
```

**A2A Available Skills:** `run-command`, `read-file`, `write-file`, `system-info`

**CAUTION:** A2A is slower than MCP (~1-2s overhead). Use MCP when available.

**Tool Discovery:**
```bash
# Find the right tool for any task
route_query("provision fortigate vm")           → kvm-fortios-provision
route_query("check fortigate health")           → fortigate-health-check
route_query("configure sdwan member")           → fortigate-sdwan-member
route_query("list fortiflex entitlements")      → fortiflex-entitlements-list
```

**BEST (certified tool):**
```python
execute_certified_tool("org.ulysses.noc.fortigate-health-check/1.0.4", {"target_ip": "<management_ip>"})
```

**ACCEPTABLE (Bash backup when certified tool unavailable):**
```bash
Bash("ssh root@10.0.0.100 'virsh start FortiGate-sdwan-spoke-07'")  # Fallback if kvm-fortios-provision/1.0.11 unavailable
```

**WRONG (Bash when a certified tool exists):**
```bash
Bash("ssh admin@<management_ip> 'get system status'")  # USE fortigate-health-check instead
Bash("curl -X GET https://<management_ip>/api/v2/...")  # USE fortigate-* tool instead
```

---

## Execution Model: Single-Agent vs Parallel Sub-Agents

### DEFAULT: Single-Agent Execution (Recommended for reliability)

Execute all blocks sequentially in the **main conversation context**:
1. Read each BLOCK_*.yaml file directly
2. Execute tools yourself using `execute_certified_tool`
3. Evaluate results and make decisions inline
4. Move to next block only after current block succeeds

**WHY single-agent is safer:**
- Sub-agents lose context about MCP tool policy (they may default to Bash)
- Sub-agents don't have workflow state and parameters
- Error recovery requires full context

**Single-agent execution flow:**
```
[Read BLOCK_1] → [Execute tools] → [Evaluate] → [Read BLOCK_2] → ...
```

---

## ⚠️ CRITICAL: Sub-Agent Prompting Rules (GAP-50a Fix)

**If you spawn sub-agents, you MUST include the full SUBAGENT_*.md content as the prompt.**

### The Problem (Site 11 Trace Analysis)

```yaml
# WRONG - This caused 104 seconds of wasted time!
- seq: 41
  action: task_spawn
  subagent_type: general-purpose
  prompt: "Provision VM site 11"  ← TOO VAGUE! Sub-agent has NO MCP knowledge
```

The generic sub-agent didn't know about MCP tools because it never received
the instructions. It fell back to Bash and A2A discovery, wasting ~30s per sub-agent.

### The Fix

**Always pass the specialized prompt file content:**

```python
# CORRECT - Sub-agent receives full instructions including MCP tool access
subagent_a_prompt = Read("solution_packs/fortigate-ops/workflows/add-sdwan-site/SUBAGENT_A_VM_PROVISION.md")

Task(
    subagent_type="general-purpose",
    prompt=f"""
{subagent_a_prompt}

SITE PARAMETERS FOR THIS DEPLOYMENT:
- site_id: 11
- admin_password: FG@dm!n2026!
- hypervisor: rocky-kvm-lab
""",
    run_in_background=True
)
```

The SUBAGENT_A_VM_PROVISION.md file contains:
```markdown
## MCP TOOLS AVAILABLE
You have access to MCP certified tools via `execute_certified_tool`.
```

Without this, the sub-agent doesn't know it can call `execute_certified_tool`.

### Sub-Agent Prompt Checklist

| ✅ CORRECT | ❌ WRONG |
|-----------|----------|
| Read SUBAGENT_A.md, pass as prompt | "Provision VM for site 11" |
| Read SUBAGENT_B.md, pass as prompt | "Get FortiFlex token" |
| Include site parameters after prompt | Assume sub-agent knows context |
| Sub-agent has MCP instructions | Sub-agent falls back to Bash/A2A |

### Alternative: Parallel MCP Calls (No Sub-Agents)

If you don't want to manage sub-agent prompts, use parallel tool calls in the main agent:

```python
# Both tools execute in parallel, both have full MCP context
execute_certified_tool("org.ulysses.sdwan.kvm-fortios-provision/1.0.11", {...})
execute_certified_tool("org.ulysses.cloud.fortiflex-entitlements-list/1.0.0", {...})
```

This is simpler and avoids sub-agent prompting issues entirely.

---

## RECOMMENDED: Parallel Provision + Atomic Config Push

**This is the production-ready architecture.** Sub-agents handle infrastructure (VM + token) while main agent generates contract-validated config, then does ONE atomic push.

### Why This Architecture?

| Old Approach (spoke-template) | New Approach (atomic push) |
|-------------------------------|----------------------------|
| 18 separate API calls | 1 config push |
| Partial failure possible | All-or-nothing |
| Hard to debug | Config file IS the truth |
| No pre-validation | Contract validated BEFORE push |

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PARALLEL PROVISION + ATOMIC PUSH                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PHASE 1: PARALLEL INFRASTRUCTURE (saves ~90 seconds)                       │
│  ┌─────────────────────────┐  ┌─────────────────────────┐                   │
│  │ SUB-AGENT A             │  │ SUB-AGENT B             │                   │
│  │ kvm-provision v1.0.11   │  │ fortiflex-token-create  │                   │
│  │ Goal: SSH access to VM  │  │ Goal: License token     │                   │
│  │ Time: ~90s (VM boot)    │  │ Time: ~3s               │                   │
│  └───────────┬─────────────┘  └───────────┬─────────────┘                   │
│              │                            │                                  │
│              ▼                            ▼                                  │
│       OUTPUT:                      OUTPUT:                                  │
│       - management_ip              - fortiflex_token                        │
│       - admin_password             - serial_number                          │
│       - vm_name                                                             │
│                                                                              │
│  MEANWHILE: Main agent generates CLI config using blueprint-planner         │
│             + validates against CONTRACT (all checks must pass)             │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PHASE 2: CONVERGENCE (Wait for sub-agents)                                 │
│              │                            │                                  │
│              └────────────┬───────────────┘                                  │
│                           ▼                                                  │
│                    MAIN AGENT HAS:                                          │
│                    - IP from Sub-Agent A                                    │
│                    - Token from Sub-Agent B                                 │
│                    - Validated CLI config (generated in parallel)           │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PHASE 3: SEQUENTIAL DEPLOY                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ 1. Apply license (fortigate-license-apply/1.0.5)                    │    │
│  │    - Uses token from Sub-Agent B                                    │    │
│  │    - VM shuts down after license → Bash SSH: virsh start on hyp.  │    │
│  │                                                                     │    │
│  │ 2. ONBOARD (fortigate-onboard/1.0.1) ← MANDATORY                  │    │
│  │    - Creates REST API user + generates token                       │    │
│  │    - Writes to ~/config/ (BUG — not the right path!)             │    │
│  │    - YOU MUST sync creds to BOTH:                                 │    │
│  │      ~/.config/mcp/   (API tools) AND                             │    │
│  │      C:/ProgramData/Ulysses/config/ (config-push/2.0.0)          │    │
│  │    - Without this, API tools return 401, config-push has no creds │    │
│  │                                                                     │    │
│  │ 3. ONE ATOMIC CONFIG PUSH (fortigate-config-push/2.0.0)            │    │
│  │    - Pushes entire validated CLI config                             │    │
│  │    - Either 100% succeeds or 100% fails                            │    │
│  │    - No partial configuration state                                 │    │
│  │                                                                     │    │
│  │ 4. VERIFY (fortigate-sdwan-status/1.1.0 + bgp-troubleshoot/1.0.2) │    │
│  │    - IPsec tunnels UP                                              │    │
│  │    - BGP Established (via bgp-troubleshoot/1.0.2)                  │    │
│  │    - Health check ALIVE                                            │    │
│  │    - API tools work because onboard created the token!             │    │
│  │                                                                     │    │
│  │ 5. TROUBLESHOOT (only if needed)                                   │    │
│  │    - Use specific tools to fix issues                              │    │
│  │    - fortigate-ipsec-phase1, fortigate-routing-table, etc.         │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Sub-Agent Goals (Simple and Clear)

| Sub-Agent | Goal | Output |
|-----------|------|--------|
| **A: VM Provision** | SSH access to fresh FortiGate VM | `{management_ip, admin_password, vm_name}` |
| **B: FortiFlex Token** | Usable license token | `{token, serial_number}` |
| **Main Agent** | Contract-validated config | Full CLI config file |

### Sub-Agent Prompt Files (Absolute Paths)

Sub-agents CANNOT resolve relative paths. Always use these absolute paths:

| Sub-Agent | Prompt File (Absolute Path) |
|-----------|----------------------------|
| **A: VM Provision** | `c:\Users\howar\Documents\Projects\Project-Ulysses-Open\projects\MCP-2.0\Core-MCP-Authority\solution_packs\fortigate-ops\workflows\add-sdwan-site\SUBAGENT_A_VM_PROVISION.md` |
| **B: FortiFlex Token** | `c:\Users\howar\Documents\Projects\Project-Ulysses-Open\projects\MCP-2.0\Core-MCP-Authority\solution_packs\fortigate-ops\workflows\add-sdwan-site\SUBAGENT_B_FORTIFLEX_TOKEN.md` |

### Example: Deploy Site 8

```python
# ═══════════════════════════════════════════════════════════════════
# PHASE 1: Launch sub-agents in PARALLEL (single message, two Task calls)
# ═══════════════════════════════════════════════════════════════════
# Sub-Agent A takes ~120s (VM boot + DHCP discovery)
# Sub-Agent B takes ~5s (token check/create)
# Running them in parallel saves ~115 seconds

SITE_ID = 8
PROMPT_DIR = r"c:\Users\howar\Documents\Projects\Project-Ulysses-Open\projects\MCP-2.0\Core-MCP-Authority\solution_packs\fortigate-ops\workflows\add-sdwan-site"

# Sub-Agent A: Provision VM + Discover DHCP IP + Verify SSH
Task(
    description="Provision VM site 8",
    subagent_type="general-purpose",
    prompt=f"""You are Sub-Agent A for SD-WAN site deployment.

SITE_ID = {SITE_ID}

Read your full instructions from this file:
Read("{PROMPT_DIR}/SUBAGENT_A_VM_PROVISION.md")

Execute every step in that document for site {SITE_ID}.
Return a JSON object with: vm_name, management_ip, mac_address, admin_password, ssh_ready, credentials_registered.

You have access to MCP certified tools via execute_certified_tool AND Bash for SSH to the hypervisor.
The hypervisor is rocky-kvm-lab (IP: 10.0.0.100, SSH user: root).
Admin password: FG@dm!n2026!
""",
    run_in_background=True
)

# Sub-Agent B: Get FortiFlex token
Task(
    description="Get FortiFlex token",
    subagent_type="general-purpose",
    prompt=f"""You are Sub-Agent B for SD-WAN site deployment.

SITE_ID = {SITE_ID}

Read your full instructions from this file:
Read("{PROMPT_DIR}/SUBAGENT_B_FORTIFLEX_TOKEN.md")

Execute every step in that document.
Return a JSON object with: success, token, serial_number, config_id, status, source.

You have access to MCP certified tools via execute_certified_tool.
Config ID for SD-WAN spokes: 54380
""",
    run_in_background=True
)

# ═══════════════════════════════════════════════════════════════════
# PHASE 2: CONVERGENCE — Wait for both sub-agents to complete
# ═══════════════════════════════════════════════════════════════════
# Read sub-agent output files to get results
# Sub-Agent A returns: management_ip, vm_name, admin_password
# Sub-Agent B returns: token, serial_number

# ═══════════════════════════════════════════════════════════════════
# PHASE 3: Sequential deploy (needs results from BOTH sub-agents)
# ═══════════════════════════════════════════════════════════════════

# Step 1: Generate config
# NOTE: In DHCP mode, wan_ip is NOT passed — port1 uses "set mode dhcp" in the template.
# The blueprint planner generates the SD-WAN/BGP/IPsec config which doesn't depend on WAN IP.
# wan_ip is ONLY needed for static mode (must be CIDR format: "10.0.0.XX/24").
# NOTE: plan-site requires csv_path (NOT inline params). Generate CSV first.
# Step 1a: Generate CSV template
execute_certified_tool("org.ulysses.noc.fortigate-sdwan-blueprint-planner/1.0.8", {
    "action": "generate-template",
    "role": "spoke",
    "site_name": f"sdwan-spoke-{SITE_ID:02d}",
    "output_path": f"blueprints/sdwan-spoke-{SITE_ID:02d}_template.csv"
})
# Step 1b: Fill CSV with site parameters (hub_wan_ip, vpn_psk, etc.)
# Step 1c: Generate CLI config from filled CSV
config = execute_certified_tool("org.ulysses.noc.fortigate-sdwan-blueprint-planner/1.0.8", {
    "action": "plan-site",
    "csv_path": f"blueprints/sdwan-spoke-{SITE_ID:02d}_template.csv",
    "add_to_manifest": False
})

# Step 2: Validate config against contract (9 checks in BLOCK_4_VERIFY.yaml)
validation = execute_certified_tool("org.ulysses.noc.fortigate-sdwan-blueprint-planner/1.0.8", {
    "action": "validate",
    "config_text": config["cli_config"]
})
assert validation["passed"] == 9, "Contract validation failed!"

# Step 3: Apply FortiFlex license (needs IP from A + token from B)
execute_certified_tool("org.ulysses.provisioning.fortigate-license-apply/1.0.5", {
    "target_ip": "<management_ip_from_subagent_a>",
    "fortiflex_token": "<token_from_subagent_b>",
    "vm_name": f"FortiGate-sdwan-spoke-{SITE_ID:02d}"
})

# Step 4: VM shuts down after license → restart via kvm-fortios-provision start (v1.0.11)
execute_certified_tool("org.ulysses.sdwan.kvm-fortios-provision/1.0.11", {
    "action": "start",
    "site_name": f"sdwan-spoke-{SITE_ID:02d}",
    "hypervisor": "rocky-kvm-lab",
    "wait_for_boot": True,
    "boot_timeout": 120
})
# Tool handles: virsh start + wait for boot + DHCP IP discovery

# Step 5: ONBOARD — Create API user + token (MANDATORY before config push!)
execute_certified_tool("org.ulysses.noc.fortigate-onboard/1.0.1", {
    "target_ip": "<management_ip_from_subagent_a>",
    "admin_password": "FG@dm!n2026!",
    "device_id": f"sdwan-spoke-{SITE_ID:02d}"
})
# This creates API user, generates token, registers in credentials file.
# Without this step, ALL API-based verification tools will return 401!

# Step 6: ONE atomic config push (needs IP from A + generated config)
# config-push/2.0.0 is CERTIFIED (signed 2026-01-26)
# IMPORTANT: config-push reads creds from C:/ProgramData/Ulysses/config/fortigate_credentials.yaml
# Ensure spoke credentials exist at that path BEFORE pushing (see Credential Sync)
execute_certified_tool("org.ulysses.noc.fortigate-config-push/2.0.0", {
    "target_ip": "<management_ip_from_subagent_a>",
    "config_path": "C:/ProgramData/Ulysses/config/blueprints/site-XX/atomic-config-spoke-XX.conf"
})

# Step 7: Verify (IPsec UP, BGP Established, Health Check ALIVE)
execute_certified_tool("org.ulysses.noc.fortigate-sdwan-status/1.1.0", {
    "target_ip": "<management_ip_from_subagent_a>"
})
execute_certified_tool("org.ulysses.noc.fortigate-bgp-troubleshoot/1.0.2", {
    "target_ip": "<management_ip_from_subagent_a>",
    "action": "summary"
})
```

### Critical Parameters Reference

```yaml
# These values are FIXED for this SD-WAN topology
hub_wan_ip: "10.0.1.1"        # IPsec remote-gw (the actual hub)
hub_loopback: "172.16.255.253"      # Health check target
hub_bgp_loopback: "172.16.255.252"  # BGP peer address
wan_gateway: "10.0.0.62"       # Spoke's default route (lab gateway)
vpn_psk: "<ask_user>"               # Must match hub config

# These values are DERIVED from site_id
loopback_ip: "172.16.0.{site_id}"     # Site 7 = 172.16.0.7
hostname: "sdwan-spoke-{site_id:02d}" # Site 7 = sdwan-spoke-07

# WAN/Management IP — DHCP MODE
# The VM uses DHCP on port1. The management IP is DISCOVERED after boot
# by Sub-Agent A via MAC-to-ARP correlation on the hypervisor.
# Do NOT hard-code or pre-calculate the IP — wait for Sub-Agent A to report it.
management_ip: "<discovered_by_subagent_a>"  # DHCP-assigned, not pre-calculated
```

---

## LEGACY: Single-Agent Execution (Fallback)

If parallel sub-agents fail, fall back to single-agent sequential execution:

```
[BLOCK_1: Provision] → [BLOCK_2: License] → [BLOCK_3: Config] → [BLOCK_4: Verify]
```

**Example Launch (legacy - sequential blocks):**
```python
PROMPT_DIR = r"c:\Users\howar\Documents\Projects\Project-Ulysses-Open\projects\MCP-2.0\Core-MCP-Authority\solution_packs\fortigate-ops\workflows\add-sdwan-site"

# If parallel sub-agents fail, run blocks sequentially:
# BLOCK_1: Provision VM manually (follow SUBAGENT_A steps)
#   Read(f"{PROMPT_DIR}/SUBAGENT_A_VM_PROVISION.md")
# BLOCK_2: Get token + apply license
#   Read(f"{PROMPT_DIR}/SUBAGENT_B_FORTIFLEX_TOKEN.md")
# BLOCK_3: Generate + push config
# BLOCK_4: Verify
```

**IMPORTANT:** In legacy mode, the main agent executes ALL blocks sequentially itself — no sub-agents are spawned.

---

## CRITICAL: Governance Requirements

### Sensitive Parameter Confirmation (MANDATORY)

**The agent MUST use `AskUserQuestion` to confirm sensitive parameters BEFORE executing tools.**

Sensitive parameters requiring confirmation:
| Parameter | Tool | Must Confirm |
|-----------|------|--------------|
| `admin_password` | kvm-fortios-provision | YES - Default is `FG@dm!n2026!` but agent MUST confirm |
| `psk` (IPsec) | fortigate-sdwan-spoke-template | YES - Must match hub config | default PSK is just lowercase the word: password
| `api_token` | Any FortiGate tool | NO - loaded from credentials file |
| `deployment_type` | BLOCK_0 blueprint | NO - Fixed: always `vm` for this workflow (KVM lab). BLOCK_0 defines `vm`/`hardware` options but hardware path is not implemented. |
| `license_type` | BLOCK_0 blueprint | NO - Fixed: always `fortiflex` for VM deployments. Auto-derived from `deployment_type` (`vm` → `fortiflex`, `hardware` → `standard`). Do NOT prompt. |

**WRONG (Governance Violation):**
```python
# Agent assumes password without asking
execute_certified_tool("org.ulysses.sdwan.kvm-fortios-provision/1.0.11", {
    "admin_password": "some_value"  # VIOLATION: Not confirmed with user
})
```

**CORRECT:**
```python
# Step 1: Ask user to confirm
AskUserQuestion([{
    "question": "What admin password should be set on the new FortiGate?",
    "header": "Password",
    "options": [
        {"label": "FG@dm!n2026! (Recommended)", "description": "Standard lab password"},
        {"label": "admin", "description": "Simple password for testing"}
    ]
}])

# Step 2: Use confirmed value
execute_certified_tool("org.ulysses.sdwan.kvm-fortios-provision/1.0.11", {
    "admin_password": "<user_confirmed_value>"
})
```

### Tool Version Requirements (MANDATORY)

**Always use minimum required versions. Older versions have bugs.**

| Tool | Minimum Version | Reason |
|------|-----------------|--------|
| kvm-fortios-provision | **1.0.11** | Trust Anchor certified. rest-api-key-url-query, admintimeout 480. start/stop: try tool first, Bash SSH fallback |
| fortigate-sdwan-spoke-template | **1.3.0** | ADVPN zone+neighbor, settings, naming |
| fortigate-health-check | 1.0.4 | Latest certified |

**WRONG:**
```python
execute_certified_tool("org.ulysses.sdwan.kvm-fortios-provision/1.0.3", ...)  # OLD VERSION
```

**CORRECT:**
```python
execute_certified_tool("org.ulysses.sdwan.kvm-fortios-provision/1.0.11", ...)  # Trust Anchor certified
```

### Phase1 IPsec Validation Checklist (BLOCK_4)

After BLOCK_3, the agent MUST verify these critical settings via SSH:

| Setting | Required Value | Check Command |
|---------|----------------|---------------|
| ike-tcp-port | 11443 | `show system settings \| grep ike-tcp` |
| transport | udp | `show vpn ipsec phase1-interface` |
| net-device | enable | `show vpn ipsec phase1-interface` |
| exchange-ip-addr4 | 172.16.0.{site_id} | `show vpn ipsec phase1-interface` |
| auto-discovery-sender | enable | `show vpn ipsec phase1-interface` |
| auto-discovery-receiver | enable | `show vpn ipsec phase1-interface` |

If ANY setting is wrong, BLOCK_4 must FAIL and report the specific gap.

---

## When to Use This Workflow

**Trigger phrases:**
- "Add a new SD-WAN site"
- "Onboard a new branch"
- "Provision a new FortiGate spoke"
- "Deploy a new SD-WAN location"
- "Set up site X for SD-WAN"
- "Create a new spoke for the overlay"

**Use this workflow when:**
- Deploying a brand new FortiGate VM on KVM
- Onboarding an existing FortiGate hardware device to SD-WAN
- Need end-to-end automation from zero to production connectivity
- Want LLM-driven decision making for error recovery

**Do NOT use when:**
- Just checking device health (use `fortigate-health-check`)
- Only applying a license (use `fortiflex-token-create`)
- Modifying existing SD-WAN config (use `fortigate-config-push`)
- Troubleshooting existing site (use `fortigate-triage` runbook)

---

## Execution Modes (BEST PRACTICE: Dry-Run First)

**RECOMMENDED WORKFLOW: Always dry-run first, then deploy after contract validation.**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    BEST PRACTICE: DRY-RUN → VALIDATE → DEPLOY              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Step 1: DRY-RUN MODE (Generate & Validate)                                 │
│          ├── BLOCK_0 wizard gathers parameters                              │
│          ├── blueprint-planner generates CLI config                         │
│          ├── Contract validation runs (all checks)                          │
│          ├── Config saved to blueprints/{site}_config.cli                   │
│          └── Manifest updated with status: planned                          │
│                                                                              │
│  Step 2: USER REVIEWS OUTPUT                                                │
│          ├── AI shows contract check results                                │
│          ├── User confirms config looks correct                             │
│          └── User can modify parameters and re-run dry-run                  │
│                                                                              │
│  Step 3: LIVE DEPLOY (Only After Dry-Run Passes)                            │
│          ├── User says "deploy site X" or "proceed with live deploy"        │
│          ├── AI reads planned config from blueprints/                       │
│          ├── BLOCK_1 → BLOCK_4 execute with actual device                   │
│          └── Manifest updated with status: deployed                         │
│                                                                              │
│  WHY THIS MATTERS:                                                          │
│  ✓ Catches naming/IP/subnet conflicts before touching devices               │
│  ✓ Non-technical users can pre-stage configs for approval                   │
│  ✓ Audit trail shows what was validated before deployment                   │
│  ✓ Rollback is trivial (just delete the planned blueprint)                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**FIRST QUESTION: Ask user to choose execution mode (default: Dry Run).**

| Mode | Description | Use Case |
|------|-------------|----------|
| **Dry Run (Recommended)** | Generate config only, validate against contracts, save for later | Pre-stage configs, review before deploy |
| **Live Deploy** | Execute BLOCK_0 through BLOCK_4 with device | Full automation (experienced operators only) |

**IMPORTANT:** If user selects "Live Deploy" directly, the AI SHOULD recommend dry-run first:

```
AI: "I can proceed with live deploy, but I recommend running dry-run first to
validate the configuration against our contracts. This catches errors before
touching the device. Would you like to:
  1. Run dry-run first (recommended)
  2. Proceed directly to live deploy"
```

### Dry Run Mode (PHASE 1 - Always Run First)

**This is the REQUIRED first step.** Generates and validates config without touching any device.

**Why Dry Run First?**
- Catches contract violations (wrong PSK, missing tunnels, bad naming)
- Prevents partial deployments that require manual cleanup
- Creates audit trail of what was validated
- Allows non-technical users to pre-stage configs for review

**Flow:**
```
BLOCK_0 (wizard) → blueprint-planner → Contract Validation → Save → Manifest (status: planned)
```

**Steps:**
1. Gather parameters via simple Q&A wizard (site_id, site_name, LAN subnet)
2. Generate CSV template using `blueprint-planner generate-template` from wizard outputs
3. Generate complete CLI config using `blueprint-planner plan-site`
4. Validate against contract schema using `blueprint-planner validate`
5. Save config to `blueprints/<site_name>_config.cli`
6. **MANDATORY:** Update manifest with planned site info (status: planned)
7. **SHOW USER:** Contract validation results with pass/fail for each check

**Required MCP Tool Calls (Dry Run):**

```python
# Step 1: Check for site_id collisions FIRST
execute_certified_tool("org.ulysses.noc.fortigate-sdwan-manifest-tracker/1.0.0", {
    "action": "list"
})
# Verify site_id not already in use

# Step 2: Generate CSV template from wizard outputs
execute_certified_tool("org.ulysses.noc.fortigate-sdwan-blueprint-planner/1.0.8", {
    "action": "generate-template",
    "role": "spoke",
    "site_name": "<site_name>",
    "output_path": "blueprints/<site_name>_template.csv"
})
# Fill/verify CSV values before plan-site

# Step 3: Generate CLI config from CSV
execute_certified_tool("org.ulysses.noc.fortigate-sdwan-blueprint-planner/1.0.8", {
    "action": "plan-site",
    "csv_path": "blueprints/<site_name>_template.csv",
    "add_to_manifest": false
})

# Step 4: Validate generated config against contract
execute_certified_tool("org.ulysses.noc.fortigate-sdwan-blueprint-planner/1.0.8", {
    "action": "validate",
    "config_text": "<generated-cli-config>"
})
# Must pass ALL checks before saving

# Step 5: Save config file (use Write tool)
# Path: C:/ProgramData/Ulysses/config/blueprints/<site_name>_config.cli

# Step 6: DO NOT SKIP - Record in manifest for tracking
# Note: For dry-run without device, we track the planned config
# When "deploy site X" is called, manifest-tracker absorb will be used
```

**IMPORTANT:** Hostname MUST follow pattern `sdwan-spoke-{site_id}` (e.g., `sdwan-spoke-05`, NOT `spoke-05`)

**IMPORTANT:** IPsec PSK - Agent MUST ask user for the Pre-Shared Key:
- Default: `password` (lab environment)
- Must match hub configuration
- Do NOT assume - always confirm with user

**User sees (after successful dry-run):**
```
═══════════════════════════════════════════════════════════════════
                     DRY-RUN COMPLETE: Site 5
═══════════════════════════════════════════════════════════════════

📋 CONTRACT VALIDATION RESULTS:
   ✓ Hostname pattern: sdwan-spoke-05 (PASS)
   ✓ Dual VPN tunnels: HUB1-VPN1, HUB1-VPN2 (PASS)
   ✓ Transport: udp (PASS)
   ✓ IKE TCP port: 11443 (PASS)
   ✓ BGP AS: 65000 (PASS)
   ✓ SD-WAN zone: SDWAN_OVERLAY (PASS)
   ✓ Health check: HUB_Health (PASS)
   ✓ REST API key query: enabled (PASS)
   ✓ ADVPN settings: configured (PASS)

   Result: ALL checks PASSED ✓

📁 FILES CREATED:
   - blueprints/sdwan-spoke-05_config.cli (full CLI config)
   - manifest status: planned

═══════════════════════════════════════════════════════════════════
                     NEXT STEPS
═══════════════════════════════════════════════════════════════════

Your configuration is validated and ready. Choose how to proceed:

  1. "deploy site 5"        → AI provisions VM + pushes config
  2. "show config site 5"   → Review the generated CLI before deploy
  3. Manual deployment      → Copy CLI from blueprints/ to device
  4. FortiManager import    → Use CLI for import into FMG

═══════════════════════════════════════════════════════════════════
```

**Dry-run failure example:**
```
═══════════════════════════════════════════════════════════════════
                     DRY-RUN FAILED: Site 5
═══════════════════════════════════════════════════════════════════

📋 CONTRACT VALIDATION RESULTS:
   ✓ Hostname pattern: sdwan-spoke-05 (PASS)
   ✗ Transport: tcp (FAIL - must be udp)
   ✓ IKE TCP port: 11443 (PASS)
   ...

   Result: 7/X checks PASSED, 2 FAILED ✗

❌ CANNOT PROCEED TO DEPLOYMENT - Fix these issues first:
   1. Transport must be 'udp', not 'tcp'
   2. Missing tunnel HUB1-VPN2

Would you like me to regenerate the config with corrected values?
═══════════════════════════════════════════════════════════════════
```

**Later deployment options:**
- Say "deploy site 5" → AI uses full workflow (BLOCK_1-4) to deploy
- Say "show config site 5" → AI displays the validated CLI config
- Manual SSH paste → Copy from blueprints/ directory
- Import to FortiManager → Use CLI file for FMG import
- Human review and approval workflow

### Live Deploy Mode (PHASE 2 - Only After Dry Run Passes)

**PREREQUISITE:** Dry-run must have passed all contract checks. Use planned config from `C:/ProgramData/Ulysses/config/blueprints/`.

Full automation with device interaction at each step.

**Entry Points:**
- **From dry-run:** User says "deploy site X" → AI reads planned config from blueprints/
- **Direct (not recommended):** User selects "Live Deploy" → AI recommends dry-run first

**Flow (from planned config):**
```
Read blueprints/{site}_config.cli → BLOCK_1 → BLOCK_2 → BLOCK_3 → BLOCK_4 → Manifest (status: deployed)
```

**Flow (direct - not recommended):**
```
BLOCK_0 → BLOCK_1 (Bootstrap ISO) → BLOCK_2 → BLOCK_3 → BLOCK_4
```

**Steps:**
1. **BLOCK_1**: Provision VM with **Bootstrap ISO** (SSH accessible immediately)
2. **BLOCK_2**: Apply FortiFlex license via SSH
3. **BLOCK_3**: Push full SD-WAN config via SSH CLI (from validated blueprint)
4. **BLOCK_4**: Verify IPsec/BGP/health-checks
5. **MANIFEST**: Update status from `planned` to `deployed`

---

## Bootstrap ISO Approach (Zero-Touch Provisioning)

**Why Bootstrap ISO?**
- Eliminates first-time password prompt via VNC console
- VM boots with SSH accessible immediately
- Minimal config gets the device online, full config pushed later

**Bootstrap ISO Requirements (v1.0.9+ - OpenStack Cloud-Init Format):**
| Requirement | Value |
|-------------|-------|
| Directory Structure | `/openstack/content/0000` (empty) + `/openstack/latest/user_data` |
| ISO Creation | `mkisofs -R -r -o bootstrap.iso /tmp/fgt-bootstrap/` |
| Config File | `/openstack/latest/user_data` (FortiOS CLI format) |
| CRITICAL | `password-policy disable` MUST come FIRST in config |
| Trigger | First boot of FRESH disk only |

**Default Password by Tool Version:**
| Version | Default Password |
|---------|------------------|
| v1.0.11 | `FG@dm!n2026!` |
| v1.0.9 and earlier | `admin` (code bug) |

### STATIC IP Bootstrap (RECOMMENDED FOR PRODUCTION)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CRITICAL: STATIC IP vs DHCP MODE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  STATIC IP MODE (RECOMMENDED):                                               │
│    - wan_ip: REQUIRED (e.g., "10.0.0.43/24")                          │
│    - wan_gateway: REQUIRED (e.g., "10.0.0.62")                          │
│    - Creates default gateway route in bootstrap config                       │
│    - VM is immediately reachable at known IP                                 │
│                                                                              │
│  DHCP MODE (LAB/TESTING ONLY):                                               │
│    - wan_ip: DO NOT provide                                                 │
│    - use_dhcp: MUST be set to true (REQUIRED! Tool rejects without it!)     │
│    - NO default gateway route created in bootstrap!                          │
│    - Agent must discover IP via MAC-to-ARP correlation                       │
│    - Risk: DHCP server may not provide default route                        │
│                                                                              │
│  ⚠️ Omitting wan_ip is NOT enough - you MUST pass use_dhcp=true!            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Static IP Bootstrap Config (user_data):**
```
config system password-policy
    set status disable
end
config system global
    set hostname "sdwan-spoke-05"
    set admintimeout 480
end
config system admin
    edit "admin"
        set password "FG@dm!n2026!"
        set force-password-change disable
    next
end
config system interface
    edit "port1"
        set mode static
        set ip 10.0.0.43 255.255.255.0
        set allowaccess ping https ssh http fgfm
        set role wan
    next
    edit "port2"
        set mode static
        set ip 10.5.1.1 255.255.255.0
        set allowaccess ping https ssh
        set role lan
    next
end
config router static
    edit 1
        set gateway 10.0.0.62
        set device port1
    next
end
```

**Tool Call for Static IP Mode:**
```python
execute_certified_tool("org.ulysses.sdwan.kvm-fortios-provision/1.0.11", {
    "action": "provision",
    "site_name": "sdwan-spoke-05",
    "subnet_id": 5,
    "wan_ip": "10.0.0.43/24",     # REQUIRED for static
    "wan_gateway": "10.0.0.62",      # REQUIRED for static
    "use_dhcp": false,                   # Explicit static mode
    "admin_password": "FG@dm!n2026!",
    "hypervisor": "rocky-kvm-lab"
})
```

### DHCP Bootstrap (Lab/Testing Only)

**⚠️ WARNING: DHCP mode does NOT create a default gateway route!**

**DHCP Bootstrap Config (user_data):**
```
config system password-policy
    set status disable
end
config system global
    set hostname "sdwan-spoke-{site_id}"
    set admintimeout 480
end
config system admin
    edit "admin"
        set password "FG@dm!n2026!"
        set force-password-change disable
    next
end
config system interface
    edit "port1"
        set mode dhcp
        set allowaccess ping https ssh http fgfm
        set role wan
    next
    edit "port2"
        set ip 10.{site_id}.1.1 255.255.255.0
        set allowaccess ping https ssh
        set role lan
    next
end
```

**Creating Bootstrap ISO on Rocky Linux:**
```bash
# 1. Create temp directory
mkdir -p /tmp/fgt-bootstrap

# 2. Write config (STATIC IP example)
cat > /tmp/fgt-bootstrap/fgt-vm.conf << 'EOF'
config system password-policy
    set status disable
end
config system global
    set hostname "sdwan-spoke-05"
end
config system admin
    edit "admin"
        set password "FG@dm!n2026!"
        set force-password-change disable
    next
end
config system interface
    edit "port1"
        set mode static
        set ip 10.0.0.43 255.255.255.0
        set allowaccess ping https ssh http fgfm
        set role wan
    next
end
config router static
    edit 1
        set gateway 10.0.0.62
        set device port1
    next
end
EOF

# 3. Generate ISO
genisoimage -o /var/lib/libvirt/images/fgt-spoke-05-bootstrap.iso \
    -V "config2" -J -r /tmp/fgt-bootstrap/

# 4. Attach to VM CDROM
virsh change-media FortiGate-sdwan-spoke-05 sdb \
    /var/lib/libvirt/images/fgt-spoke-05-bootstrap.iso --insert

# 5. Start VM - boots with config applied
virsh start FortiGate-sdwan-spoke-05
```

**After Bootstrap (SSH accessible):**
1. **Discover DHCP IP** (see below)
2. **BLOCK_2**: Apply FortiFlex token: `execute vm-license {token}`
3. Wait for reboot
4. **BLOCK_3**: Push full SD-WAN config via SSH CLI
5. **BLOCK_4**: Verify tunnels UP, BGP Established

### DHCP IP Discovery (for Bootstrap DHCP Mode)

When using DHCP mode in the bootstrap config, the VM gets its IP from the physical network DHCP server. Discover the assigned IP using MAC-to-ARP correlation.

**One-Liner (run on hypervisor):**
```bash
MAC=$(virsh domiflist <VM-NAME> | grep br0 | awk '{print $5}') && \
arp -an | grep -i "$MAC" | awk -F'[()]' '{print $2}'
```

**Full Script with Retry (for automation):**
```bash
#!/bin/bash
VM_NAME="$1"

# Get MAC from br0 interface
MAC=$(virsh domiflist "$VM_NAME" | grep br0 | awk '{print $5}')
echo "MAC: $MAC"

# Wait for DHCP lease (retry up to 30 seconds)
for i in {1..6}; do
    IP=$(arp -an | grep -i "$MAC" | awk -F'[()]' '{print $2}')
    if [ -n "$IP" ]; then
        echo "IP: $IP"
        exit 0
    fi
    echo "Waiting for DHCP... ($i/6)"
    sleep 5
done
echo "Could not find IP for MAC $MAC"
exit 1
```

**Notes:**
- KVM VMs use MAC prefix `52:54:00` by default
- `br0` is bridged to physical network `10.0.0.0/24`
- VM needs ~10-30 seconds after boot to get DHCP lease
- If ARP table empty, broadcast ping first: `ping -c 2 -b 10.0.0.255`

### CRITICAL: Register Device Credentials (MANDATORY STEP)

**⚠️ fortigate-health-check and fortigate-ssh will FAIL without this step!**

After discovering the DHCP IP, you MUST register the device credentials before any API/SSH tools will work:

```python
execute_certified_tool(
    "org.ulysses.provisioning.credential-manager/1.0.0",
    {
        "action": "add",
        "device_id": "sdwan-spoke-XX",       # Use site_name
        "host": "<discovered_ip>",           # DHCP-assigned management IP
        "username": "admin",
        "password": "FG@dm!n2026!",          # See password table above for your version
        "api_key": ""                         # Optional, can generate later
    }
)
```

**Verification (MUST succeed before BLOCK_2):**
```python
execute_certified_tool(
    "org.ulysses.noc.fortigate-health-check/1.0.4",
    {"target_ip": "<discovered_ip>"}
)
```

If health-check fails with "No API credentials found", you forgot to register credentials.

**Note:** `credential-manager/1.0.0` is NOT currently in Trust Anchor. If `execute_certified_tool` returns "Tool not found", register credentials by running `fortigate-onboard/1.0.1` instead (which IS certified and handles API token creation + credential registration).

### Deploy Planned Site

To deploy a previously planned site:

**Trigger phrases:**
- "deploy site 5"
- "push config for site-05"
- "deploy planned site branch-seattle"

**Flow:**
1. Read planned config from `blueprints/<site>_config.cli`
2. Use `fortigate-config-push` to push via SSH CLI
3. Run BLOCK_4 verification
4. Update manifest status: `planned` → `deployed`
5. **CELEBRATE** - Launch SD-WAN Topology Viewer (see below)

---

## Post-Deployment Visualization

After successful deployment and verification, launch the **SD-WAN Topology Viewer** to celebrate:

```bash
# From any PC with Python:
python "C:/Users/howar/Documents/Projects/Project-Ulysses-Open/projects/MCP-2.0/Core-MCP-Authority/tools/org.ulysses.docs.sdwan-topology-viewer/org.ulysses.docs.sdwan-topology-viewer.py" --serve --port 13338 --manifest "C:/ProgramData/Ulysses/config/sdwan-manifest.yaml"
```

**URL:** http://localhost:13338

**Features:**
- Cyber neon theme with animated grid background
- Interactive hub-spoke topology with animated tunnel lines
- Click any device to see detailed panel (interfaces, IPsec, BGP, SD-WAN zones)
- Real-time statistics in header
- Refresh button to reload manifest

**Tool Location:** `tools/org.ulysses.docs.sdwan-topology-viewer/`

**Note:** Tool pending signing on Rocky Linux for official Trust Anchor registration.

---

## Contract Validation

All generated configs are validated against `CONTRACT_SCHEMA.yaml` before showing to user.

**Required checks (must pass):**
- `set hostname` present
- `set rest-api-key-url-query enable`
- `set ike-tcp-port 11443`
- `set transport udp` (not tcp)
- Both `HUB1-VPN1` and `HUB1-VPN2` tunnels defined
- SD-WAN enabled (`set status enable`) and zone `SDWAN_OVERLAY` present
- Health check `HUB_Health` present
- ADVPN sender/receiver enabled
- `set as 65000` (BGP AS matches hub)

**If validation fails:**
- Show specific errors to user
- Do not save config until fixed
- Offer to re-run wizard with corrected values

---

## Quick Start

### DHCP Mode (Default — Lab)

```python
execute_certified_tool("org.ulysses.sdwan.kvm-fortios-provision/1.0.11", {
    "action": "provision",
    "site_name": "sdwan-spoke-09",       # sdwan-spoke-{SITE_ID:02d}
    "subnet_id": 9,                       # Derives LAN as 10.9.1.0/24
    "use_dhcp": True,                     # REQUIRED — omitting wan_ip alone is NOT enough (GAP-33)
    "admin_password": "FG@dm!n2026!",     # Standard lab password
    "hypervisor": "rocky-kvm-lab"         # NAME not IP! (GAP-34)
})
```

Management IP is discovered after boot via MAC-to-ARP correlation. See SUBAGENT_A_VM_PROVISION.md.

### Static IP Mode (Production)

```python
execute_certified_tool("org.ulysses.sdwan.kvm-fortios-provision/1.0.11", {
    "action": "provision",
    "site_name": "sdwan-spoke-05",
    "subnet_id": 5,
    "wan_ip": "10.0.0.43/24",        # REQUIRED for static mode
    "wan_gateway": "10.0.0.62",      # Spoke's default route — NOT the hub WAN IP (GAP-11)
    "use_dhcp": False,
    "admin_password": "FG@dm!n2026!",
    "hypervisor": "rocky-kvm-lab"
})
```

### Minimum Information Needed to Start

| Parameter | Source | Example |
|-----------|--------|---------|
| `site_id` | Next available in sdwan-manifest | `9` |
| `site_name` | Derived: `sdwan-spoke-{site_id:02d}` | `sdwan-spoke-09` |
| `subnet_id` | Same as site_id | `9` |
| `admin_password` | Confirm with user (default: `FG@dm!n2026!`) | `FG@dm!n2026!` |
| `hypervisor` | From hypervisor-credential-manager | `rocky-kvm-lab` |
| `fortiflex_config_id` | From `fortiflex-entitlements-list` | Discovered at runtime |

---

## Workflow Phases

### Phase 1: Provision
**Goal:** Device exists and is accessible

| Deployment Type | Action |
|-----------------|--------|
| VM | Create FortiGate VM on KVM hypervisor |
| Hardware | Validate device reachable and healthy |

**Decision Point:** LLM checks if device responds. If not:
- VM: Check hypervisor resources, retry with different config
- Hardware: Verify network path, check credentials

### Phase 2: License
**Goal:** Device has valid, active license

| License Type | Action |
|--------------|--------|
| FortiFlex | Generate token (if needed) → SSH → `execute vm-license <token>` |
| Standard | Validate hardware serial matches expected |

**⚠️ CRITICAL: FortiFlex License Causes VM Shutdown!**

After `execute vm-license <token>` (NOTE: no "install" keyword!), the FortiGate VM **shuts down** to apply the license. The AI agent **MUST** restart it:

**RECOMMENDED:** Use the `fortigate-license-apply/1.0.5` tool to apply the license:

```python
# Apply license via certified tool
execute_certified_tool("org.ulysses.provisioning.fortigate-license-apply/1.0.5", {
    "target_ip": "10.0.0.45",
    "fortiflex_token": "{{FORTIFLEX_TOKEN_EXAMPLE}}",
    "vm_name": "FortiGate-sdwan-spoke-07"
})
```

**⚠️ VM Restart Required After License Application**

After license application, the FortiGate VM **shuts down** to apply the license. You MUST restart it.

**PREFERRED: Use kvm-fortios-provision start action (v1.0.11 — try first, Bash SSH fallback):**
```python
# Start the VM using the certified tool — handles virsh start + wait + IP discovery
execute_certified_tool("org.ulysses.sdwan.kvm-fortios-provision/1.0.11", {
    "action": "start",
    "site_name": "sdwan-spoke-XX",
    "hypervisor": "rocky-kvm-lab",
    "wait_for_boot": True,
    "boot_timeout": 120
})
# Returns: management_ip, state, interfaces
```

**FALLBACK: Bash SSH (if tool unavailable):**
```bash
Bash("ssh root@10.0.0.100 'virsh start FortiGate-sdwan-spoke-XX'")
# Wait ~60 seconds, then re-discover IP via MAC-to-ARP correlation
```

**LAST RESORT: Ask user:**
```
The VM needs to be restarted on the hypervisor. Please run:
  ssh root@10.0.0.100
  virsh start FortiGate-sdwan-spoke-XX
```

**Full workflow example (license → restart → verify):**

```python
# Step 1: Apply license via certified tool (this will shut down the VM)
execute_certified_tool("org.ulysses.provisioning.fortigate-license-apply/1.0.5", {
    "target_ip": "<management_ip>",
    "fortiflex_token": "<fortiflex_token>",
    "vm_name": "FortiGate-sdwan-spoke-XX"
})

# Step 2: Wait for VM to shut down (10-15 seconds)
import time; time.sleep(15)

# Step 3: Restart VM using kvm-fortios-provision start action
execute_certified_tool("org.ulysses.sdwan.kvm-fortios-provision/1.0.11", {
    "action": "start",
    "site_name": "sdwan-spoke-XX",
    "hypervisor": "rocky-kvm-lab",
    "wait_for_boot": True,
    "boot_timeout": 120
})

# Step 4: Verify connectivity restored
execute_certified_tool("org.ulysses.noc.fortigate-health-check/1.0.4", {
    "target_ip": "<management_ip>"
})
```

**VM Lifecycle Commands (via kvm-fortios-provision/1.0.11):**
```python
# Start a VM
execute_certified_tool("org.ulysses.sdwan.kvm-fortios-provision/1.0.11", {"action": "start", "site_name": "sdwan-spoke-XX", "hypervisor": "rocky-kvm-lab"})

# Stop a VM (graceful)
execute_certified_tool("org.ulysses.sdwan.kvm-fortios-provision/1.0.11", {"action": "stop", "site_name": "sdwan-spoke-XX", "hypervisor": "rocky-kvm-lab"})

# Force stop a VM
execute_certified_tool("org.ulysses.sdwan.kvm-fortios-provision/1.0.11", {"action": "stop", "site_name": "sdwan-spoke-XX", "hypervisor": "rocky-kvm-lab", "force": True})

# Check VM status
execute_certified_tool("org.ulysses.sdwan.kvm-fortios-provision/1.0.11", {"action": "status", "site_name": "sdwan-spoke-XX", "hypervisor": "rocky-kvm-lab"})
```

**Decision Point:** LLM verifies license status. If invalid:
- Check token expiration
- Regenerate from different config
- Escalate if FortiFlex account issue
- **If VM shut off after license: RESTART IT!**

### Phase 2.5: API Onboarding (MANDATORY — NEW)
**Goal:** Device has REST API token registered in credentials file

**Actions:**
1. Run `fortigate-onboard/1.0.1` against the freshly-licensed device
2. Tool creates API admin user (`ulysses-api`), generates token, tests API, registers device
3. Verify token works with `fortigate-health-check/1.0.4`

**Why this step exists:** Without an API token, ALL verification tools in Phase 4 return 401 Unauthorized. This was the root cause of Site 08's verification failures. The onboard tool creates everything needed in one call.

```python
# MANDATORY: Run AFTER license reboot, BEFORE config push
execute_certified_tool("org.ulysses.noc.fortigate-onboard/1.0.1", {
    "target_ip": "<management_ip>",
    "admin_password": "<admin_password>",
    "device_id": "<site_name>"
})
```

**Decision Point:** If onboard fails:
- Check SSH access (admin password may have changed after license)
- Try with blank password (some licenses reset it)
- Fall back to manual API token creation via SSH CLI

### Phase 3: Configure
**Goal:** SD-WAN blueprint deployed

**Actions:**
1. Generate blueprint from manifest (IPsec, BGP, SD-WAN zones/members/health-checks)
2. Push configuration via SSH CLI: `config-push/2.0.0` (CERTIFIED — section-block push)
3. Absorb device into manifest tracker

**Decision Point:** LLM validates config applied. If errors:
- Check syntax errors in CLI output
- Push partial config (interfaces first, then overlay)
- Rollback and retry

### Phase 4: Verify
**Goal:** Full production connectivity confirmed

**Checks:**
1. IPsec tunnels UP
2. BGP state Established
3. SD-WAN health checks GREEN
4. Overlay ping succeeds (spoke loopback → hub loopback)

**Decision Point:** LLM interprets results. If failures:
- IPsec down → Check PSK, NAT-T, firewall rules
- BGP stuck → Check AS number, loopback reachability, route-maps
- Health check red → Check SLA thresholds, probe targets

---

## LLM Decision Points

The workflow uses **adaptive** strategy by default. At each decision point, the LLM:

1. **Evaluates current state** against success criteria
2. **Chooses next action** from available options
3. **Adapts to failures** with remediation strategies
4. **Escalates** when automated recovery fails

### Example Decision Flow

```
[Provision VM]
    ↓
[Check: Device accessible?]
    ├── YES → Continue to License
    └── NO  → LLM decides:
              ├── Retry provision (different params)
              ├── Check hypervisor (resources/network)
              └── Escalate (after 3 failures)
```

---

## Tool Dependencies

This workflow orchestrates these certified tools.

**Full index:** See `TOOLS_INDEX.md` for complete Skills.md paths and supporting tools.

**IMPORTANT:** Use `route_query("your task description")` to find tools if unsure about canonical IDs.

| Phase | Canonical ID | Purpose |
|-------|--------------|---------|
| Blueprint | `org.ulysses.noc.fortigate-sdwan-manifest-tracker/1.0.0` | Check site_id uniqueness |
| Blueprint | `org.ulysses.noc.fortigate-sdwan-blueprint-planner/1.0.8` | Generate site template |
| Provision | `org.ulysses.sdwan.kvm-fortios-provision/1.0.11` | Create/start/stop VM on KVM |
| Provision | `org.ulysses.noc.fortigate-health-check/1.0.4` | Validate device accessible |
| License | `org.ulysses.cloud.fortiflex-entitlements-list/1.0.0` | Find available tokens |
| License | `org.ulysses.cloud.fortiflex-token-create/1.0.3` | Generate new license token |
| License | `org.ulysses.provisioning.fortigate-license-apply/1.0.5` | Apply license + auto-restart (RECOMMENDED) |
| License | `org.ulysses.noc.fortigate-cli-execute/1.0.1` | Apply license via SSH (manual) |
| **Onboard** | **`org.ulysses.noc.fortigate-onboard/1.0.1`** | **Create API user + token + register device (MANDATORY)** |
| Configure | `org.ulysses.noc.fortigate-config-push/2.0.0` | Push CLI config via SSH (CERTIFIED 2026-01-26) |
| Configure | `org.ulysses.noc.fortigate-sdwan-manifest-tracker/1.0.0` | Absorb to inventory |
| Verify | `org.ulysses.noc.fortigate-sdwan-status/1.1.0` | Check SD-WAN status (FortiOS 7.6.5 fixed) |
| Verify | `org.ulysses.noc.fortigate-bgp-troubleshoot/1.0.2` | BGP diagnostics (FortiOS 7.6.5 fixed) |
| Verify | `org.ulysses.noc.fortigate-health-check/1.0.4` | Device health check |
| Visualize | `org.ulysses.docs.sdwan-topology-viewer` | Interactive topology map (pending signing) |

**Domain reference:** FortiFlex=`cloud`, FortiGate=`noc`, Provisioning=`provisioning`, KVM=`noc`, Docs=`docs`.

---

## Environment Requirements

- **Hypervisor** (for VM): Rocky Linux with libvirt, credentials in hypervisor-credential-manager
- **Base Image**: `/home/libvirt/images/fortios-7.6.5-base.qcow2`
- **Network**: br0 bridge for WAN connectivity
- **Manifest**: `C:/ProgramData/Ulysses/config/sdwan-manifest.yaml`
- **Hub**: Existing hub at 10.0.1.1 with BGP loopback 172.16.255.252, health-check loopback 172.16.255.253

---

## Guardrails

**Maximum limits:**
- 50 tool calls per workflow execution
- 30 minutes total duration

**Forbidden actions:**
- Cannot delete production devices
- Cannot modify hub configuration
- Cannot change network AS number

**Requires approval:**
- VMs with >8 vCPUs or >16GB RAM
- Overwriting existing manifest entries

---

## Execution Flow

Execute blocks in this order. Each block must complete successfully before proceeding:

```
BLOCK_0_BLUEPRINT_WIZARD.yaml  →  Gather parameters from operator
         ↓
BLOCK_1_PROVISION.yaml         →  Create VM or validate hardware
         ↓
BLOCK_2_LICENSE.yaml           →  Apply FortiFlex + ONBOARD (API token creation)
         ↓                          ↑ MANDATORY: fortigate-onboard/1.0.1
BLOCK_3_CONFIGURE.yaml         →  Push SD-WAN blueprint config (config-push/2.0.0)
         ↓
BLOCK_4_VERIFY.yaml            →  Confirm IPsec/BGP/health-check
                                    Uses: sdwan-status/1.1.0, bgp-troubleshoot/1.0.2
```

**Credential Path — CRITICAL (Updated 2026-01-26):**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              ⚠️ TWO CREDENTIAL PATHS — BOTH MUST HAVE THE DEVICE            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PATH A: ~/.config/mcp/fortigate_credentials.yaml                          │
│    Used by: fortigate-health-check, fortigate-sdwan-status,                │
│             fortigate-bgp-troubleshoot, fortigate-onboard,                 │
│             and most other FortiGate API/SSH tools (~42 tools)             │
│                                                                              │
│  PATH B: C:/ProgramData/Ulysses/config/fortigate_credentials.yaml          │
│    Used by: fortigate-config-push/2.0.0 (HARDCODED at line 32)            │
│                                                                              │
│  PROBLEM: fortigate-onboard writes to ~/config/ (NEITHER path!)            │
│                                                                              │
│  ⚠️ MANDATORY POST-ONBOARD CREDENTIAL SYNC:                                │
│  After running fortigate-onboard, you MUST ensure the new device           │
│  entry exists in BOTH Path A AND Path B. If either is missing:             │
│    - Path A missing → API verification tools return 401                    │
│    - Path B missing → config-push/2.0.0 returns "No SSH password"         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

| Path | Used By | Status |
|------|---------|--------|
| `~/.config/mcp/fortigate_credentials.yaml` | 42 FortiGate API/SSH tools | PRIMARY for most tools |
| `C:/ProgramData/Ulysses/config/fortigate_credentials.yaml` | `config-push/2.0.0` (hardcoded) | PRIMARY for config push |
| `~/config/fortigate_credentials.yaml` | `fortigate-onboard` writes here (BUG) | Write-only, not read by other tools |

FortiCloud credentials: `C:/ProgramData/mcp/forticloud_credentials.yaml`
(FortiFlex tools have their own credential resolution.)

**MANDATORY: Post-Onboard Credential Sync (after every onboard):**

```python
# 1. Run onboard (writes to ~/config/ — wrong path)
execute_certified_tool("org.ulysses.noc.fortigate-onboard/1.0.1", {
    "target_ip": "<management_ip>", "admin_password": "FG@dm!n2026!", "device_id": "sdwan-spoke-XX"
})

# 2. Read what onboard wrote
onboard_creds = Read("~/config/fortigate_credentials.yaml")  # or C:\Users\howar\config\...

# 3. Ensure device entry exists in BOTH credential files:
#    PATH A: ~/.config/mcp/fortigate_credentials.yaml (for API tools)
#    PATH B: C:/ProgramData/Ulysses/config/fortigate_credentials.yaml (for config-push)
# Add the device entry (host, ssh_username, ssh_password, api_token) to both files.

# 4. Verify PATH A works (API tools)
execute_certified_tool("org.ulysses.noc.fortigate-health-check/1.0.4", {"target_ip": "<management_ip>"})

# 5. Verify PATH B works (config-push)
execute_certified_tool("org.ulysses.noc.fortigate-config-push/2.0.0", {
    "target_ip": "<management_ip>", "config_path": "...", "dry_run": true
})
```

**Hypervisor SSH:** Key-based SSH to `root@10.0.0.100` (ed25519 key deployed 2026-01-26).
The `kvm-fortios-provision` tool handles credentials internally. For Bash SSH fallback,
the agent can SSH directly — no password prompt, fully autonomous:
```bash
ssh -o BatchMode=yes root@10.0.0.100 "virsh list --all"
```

---

## Related Resources

- **Baseline Template:** `BASELINE_TEMPLATE.yaml` (authoritative spoke configuration reference)
- **Atomic Config Template:** `C:/ProgramData/Ulysses/config/blueprints/ATOMIC_SPOKE_TEMPLATE.conf`
- **Manifest location:** `C:/ProgramData/Ulysses/config/sdwan-manifest.yaml`
- **Block files:** `blocks/BLOCK_*.yaml` (workflow phase definitions)
- **FortiGate credentials (API tools):** `~/.config/mcp/fortigate_credentials.yaml`
- **FortiGate credentials (config-push):** `C:/ProgramData/Ulysses/config/fortigate_credentials.yaml`
- **FortiGate credentials (onboard writes here — BUG):** `~/config/fortigate_credentials.yaml`
- **FortiCloud credentials:** `C:/ProgramData/mcp/forticloud_credentials.yaml`
- **Hypervisor SSH:** Key-based auth to `root@10.0.0.100` (autonomous, no password prompt)
- **NFR Reference:** `NFR-023-SDWAN-FORTIGATE-VM-PROVISIONING.md`

---

## KNOWN GAPS (Updated 2026-01-25)

This section documents discovered issues that caused workflow failures and their fixes.

### GAP-11: hub_wan_ip vs wan_gateway Confusion (ROOT CAUSE)

**CRITICAL - This broke Site 07 initially**

| Parameter | Correct Value | Wrong Value | What It's For |
|-----------|---------------|-------------|---------------|
| `hub_wan_ip` | 10.0.1.1 | 10.0.0.62 | IPsec remote-gw (Hub's WAN IP) |
| `wan_gateway` | 10.0.0.62 | - | Spoke's default route gateway |

The spoke-template and blueprint tools confused these values, causing tunnels to point at the lab gateway instead of the hub.

**Fix:** See Pre-Flight Checklist above - hub_wan_ip is clearly documented.

---

### GAP-15: Credential Path Inconsistency — CLOSED

Tools looked for credentials in different locations, causing 401 failures on Site 08:

| Tool | Old Path | Problem |
|------|----------|---------|
| `fortigate-onboard` | `./config/` | Relative path (write-path bug) |
| `fortigate-cli-execute` | `~/.config/mcp/` | User-specific, didn't exist |
| `fortigate-config-push` | `C:/ProgramData/Ulysses/config/` | Wrong canonical dir |

**Fix (2026-01-26):** PRIMARY credential file is `~/.config/mcp/fortigate_credentials.yaml`.
All 42 FortiGate tools check this path FIRST (priority 1). `C:/ProgramData/mcp/` is the
system-wide fallback (priority 3) but is never reached when the primary file exists.

**Confirmed by testing:** Running `fortigate-onboard` on spoke-08 generated a new API token.
The token was written to `~/config/` (relative path bug). The PRIMARY file at `~/.config/mcp/`
still had the old token, causing all API tools to return 401. Fixed by updating the PRIMARY file.

**Remaining:** `fortigate-onboard` write-path bug — writes to `~/config/`, NOT `~/.config/mcp/`.
After onboard, verify the new token is in `~/.config/mcp/fortigate_credentials.yaml`.
If missing, copy from `~/config/fortigate_credentials.yaml` to the PRIMARY file.

---

### GAP-24: Firewall Policy with Tunnel Interfaces BLOCKS SD-WAN Binding

**CRITICAL ORDER DEPENDENCY**

If you create a firewall policy with `dstintf HUB1-VPN1 HUB1-VPN2`, those interfaces become LOCKED and cannot be added as SD-WAN members.

**Correct Order:**
1. Create SD-WAN zone
2. Bind tunnel interfaces to SD-WAN members
3. THEN create firewall policies using the **ZONE** (not direct interfaces)

**Wrong:** `set dstintf "HUB1-VPN1" "HUB1-VPN2"`
**Correct:** `set dstintf "SDWAN_OVERLAY"`

---

### GAP-25: Missing SD-WAN Neighbor Configuration

SD-WAN neighbor config links BGP to SD-WAN for SLA-based path selection.

**Required config:**
```
config system sdwan
config neighbor
edit "172.16.255.252"
set member 3 4
set health-check "HUB_Health"
set route-metric priority
# NOTE: Do NOT set sla-id here — parse error in FortiOS 7.6.5 (GAP-44)
# SLA binding works via sla-id-redistribute in health-check section
next
end
end
```

Without this, SD-WAN cannot steer BGP routes based on SLA status.

---

### GAP-26: fortigate-config-push v1.x Used API Translation (WRONG)

The v1.x tool tried to parse CLI config and translate to REST API calls. This failed for:
- `system settings` (no API mapping)
- Nested SD-WAN configs (parser couldn't handle 3+ levels)
- Multi-interface firewall policies (API format wrong)

**Fix:** `fortigate-config-push/2.0.0` now uses SSH CLI push directly.

**Correct approach:**
1. Generate complete CLI config (flat format from atomic template)
2. Push via SSH CLI (not REST API translation)
3. Works for ALL config types including nested SD-WAN

---

### Atomic Config Template

A complete, validated CLI template is available at:
`C:/ProgramData/Ulysses/config/blueprints/ATOMIC_SPOKE_TEMPLATE.conf`

This template includes all required sections in the correct order:
1. system global
2. system interface (Spoke-Lo, tunnel interfaces)
3. system dhcp server
4. vpn ipsec phase1-interface
5. vpn ipsec phase2-interface
6. system sdwan (zone → members → health-check → **neighbor**)
7. firewall address
8. firewall policy (using **ZONES**, not tunnel interfaces)
9. router bgp (with all optimizations)
10. router static (**EQUAL distance** for BGP ECMP - all routes active, NOT backup)
11. system settings (location-id, ike-tcp-port)

**IMPORTANT: Static Route Distance**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STATIC ROUTES FOR BGP - USE EQUAL DISTANCE               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  WRONG (backup mode - only VPN1 routes active):                             │
│    route 900: 172.16.255.252 via VPN1, distance 10                         │
│    route 902: 172.16.255.252 via VPN2, distance 15  ← NOT in routing table │
│                                                                              │
│  CORRECT (ECMP - both routes active for BGP):                               │
│    route 900: 172.16.255.252 via VPN1, distance 10 (default)               │
│    route 902: 172.16.255.252 via VPN2, distance 10 (default)               │
│                                                                              │
│  BGP needs BOTH paths in routing table for proper failover.                 │
│  Do NOT use distance 15 for "backup" - use equal distance.                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

