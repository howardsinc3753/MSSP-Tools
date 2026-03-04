# FortiGate SD-WAN Solution Pack - Developer Onboarding

**Purpose:** Guide AI agents who need to BUILD, EXTEND, or MAINTAIN this solution pack.
**Audience:** AI agents tasked with adding features, fixing bugs, or modifying workflows.

---

## Quick Reference (Read First!)

| What You Need | Location |
|---------------|----------|
| **Deploy a site** | Use `/add-sdwan-site` skill (see Skills.md) |
| **Understand architecture** | This document + CODE_MAP.md |
| **Add new feature** | Read "How To Add Features" section below |
| **Modify spoke template** | `tools/org.ulysses.provisioning.fortigate-sdwan-spoke-template/` |
| **Change workflow blocks** | `workflows/add-sdwan-site/blocks/BLOCK_*.yaml` |
| **Naming conventions** | `BASELINE_TEMPLATE.yaml` (the contract) |
| **Atomic CLI template** | `C:/ProgramData/Ulysses/config/blueprints/ATOMIC_SPOKE_TEMPLATE.conf` |
| **Tool signing** | Read trust-bot-toolskill-maker skill |
---

## Solution Pack Architecture

```
solution_packs/fortigate-ops/
|-- SKILLS.md                    # Solution pack overview
|-- DEVELOPER_ONBOARDING.md      # THIS FILE - for AI developers
|-- CODE_MAP.md                  # Component locations
|-- workflows/
|   `-- add-sdwan-site/          # Main SD-WAN provisioning workflow
|       |-- Skills.md            # AI routing guide for deployment
|       |-- BASELINE_TEMPLATE.yaml   # CONTRACT - naming conventions
|       |-- skill-definition.md      # Slash command wrapper
|       |-- manifest.yaml            # Workflow metadata
|       |-- hooks/                   # Pre-execution validators
|       |-- SUBAGENT_A_VM_PROVISION.md     # Sub-agent prompt: VM + DHCP discovery
|       |-- SUBAGENT_B_FORTIFLEX_TOKEN.md  # Sub-agent prompt: FortiFlex token
|       `-- blocks/
|           |-- BLOCK_0_BLUEPRINT_WIZARD.yaml
|           |-- BLOCK_1_PROVISION.yaml
|           |-- BLOCK_2_LICENSE.yaml
|           |-- BLOCK_3_CONFIGURE.yaml
|           `-- BLOCK_4_VERIFY.yaml
`-- tools/                       # Tools live in parent tools/ directory
    # Referenced tools for this workflow
```

### Key Files and Their Purpose

| File | Purpose | When to Modify |
|------|---------|----------------|
| `BASELINE_TEMPLATE.yaml` | **THE CONTRACT** - naming constants, critical settings | Only if adding new naming standards |
| `Skills.md` | AI routing guide - tells agent HOW to use workflow | When changing workflow steps or user experience |
| `skill-definition.md` | Slash command wrapper - prerequisites enforcement | When adding new prerequisites |
| `BLOCK_*.yaml` | Workflow phase definitions | When adding/changing deployment steps |
| `fortigate-sdwan-spoke-template.py` | Main configuration generator | When adding new config sections (ADVPN, VXLAN, etc.) |
| `org.ulysses.noc.fortigate-config-push` | SSH CLI push tool for atomic configs | When changing deployment or error handling |
| `C:/ProgramData/Ulysses/config/blueprints/ATOMIC_SPOKE_TEMPLATE.conf` | Atomic CLI baseline for SSH pushes | When changing config order or defaults |
| `SUBAGENT_A_VM_PROVISION.md` | Sub-agent prompt: KVM provision + DHCP discovery + SSH verify | When changing VM provisioning or DHCP workflow |
| `SUBAGENT_B_FORTIFLEX_TOKEN.md` | Sub-agent prompt: FortiFlex token check/create | When changing license acquisition workflow |
---

## The Contract: BASELINE_TEMPLATE.yaml

**This is the single source of truth for naming conventions and critical settings.**

Before modifying ANYTHING, read this file:
```
workflows/add-sdwan-site/BASELINE_TEMPLATE.yaml
```

### Critical Constants (DO NOT CHANGE without updating all references)

| Constant | Value | Used By |
|----------|-------|---------|
| `loopback_interface` | `Spoke-Lo` | All blocks, spoke-template |
| `tunnel_vpn1` | `HUB1-VPN1` | IPsec, SD-WAN members, health checks |
| `tunnel_vpn2` | `HUB1-VPN2` | IPsec, SD-WAN members, health checks |
| `sdwan_zone_overlay` | `SDWAN_OVERLAY` | SD-WAN zone, firewall policies |
| `health_check_hub` | `HUB_Health` | SD-WAN health check, ADVPN |
| `ike_tcp_port` | `11443` | system settings, phase1 |
| `transport` | `udp` | phase1 (NOT tcp!) |

### Derivation Rules

| Derived Value | Formula | Example (site_id=5) |
|---------------|---------|---------------------|
| `spoke_loopback` | `172.16.0.{site_id}` | `172.16.0.5` |
| `location_id` | `172.16.0.{site_id}` | `172.16.0.5` |
| `default_lan` | `10.{site_id}.1.0/24` | `10.5.1.0/24` |
| `hostname` | `sdwan-spoke-{site_id:02d}` | `sdwan-spoke-05` |
| `localid_vpn1` | `spoke-HUB1-VPN1` | `spoke-HUB1-VPN1` |

---

## Workflow Blocks: How They Work

The workflow is divided into blocks that execute sequentially:

```
BLOCK_0 (Blueprint) -> BLOCK_1 (Provision) -> BLOCK_2 (License) -> BLOCK_3 (Configure) -> BLOCK_4 (Verify)
```

### Block Structure

Each BLOCK_*.yaml contains:

```yaml
block_id: <unique_id>
block_number: <0-4>
name: "Human Readable Name"
version: "1.x.x"

depends_on: [<previous_blocks>]

ai_instructions:
  execution_model: |
    Instructions for AI agent execution
  tool_policy: |
    What tools to use and how

tools:
  - canonical_id: "org.ulysses.noc.tool-name/1.0.0"
    purpose: "What this tool does"
    example: |
      execute_certified_tool("org.ulysses...", {...})

inputs:
  required: [<param1>, <param2>]
  optional: [<param3>]
  from_previous_block: [<param4>]

success_criteria:
  - id: <check_id>
    description: "What must be true"
    verification:
      tool: "org.ulysses.noc.tool/1.0.0"
      check: "<condition>"
```

### Adding a New Block

If you need to add a new step (e.g., BLOCK_2A for AWS-specific licensing):

1. Create `BLOCK_2A_AWS_LICENSE.yaml` with correct structure
2. Update `depends_on` in subsequent blocks
3. Update Skills.md workflow section
4. Update manifest.yaml to include new block
5. Test dry-run first!

---

## Parallel Sub-Agent Architecture

The deployment workflow uses **parallel sub-agents** for performance. Instead of running blocks sequentially (legacy), the main agent spawns two background sub-agents:

```
SUB-AGENT A (Background, ~120s)     SUB-AGENT B (Background, ~5s)
├── kvm-provision (DHCP mode)        ├── Check existing FortiFlex tokens
├── Wait for VM boot                 ├── Create new token if needed
├── Discover DHCP IP (MAC→ARP)       └── Return: {token, serial_number}
├── Verify SSH access
├── Register credentials
└── Return: {management_ip, vm_name}
             │
             └──────────┬──────────────┘
                        ▼ CONVERGENCE
            MAIN AGENT (Sequential)
            ├── Generate config (uses IP from A)
            ├── Apply license (uses token from B)
            ├── Bash SSH: virsh start (VM restarts after license)
            ├── Push atomic CLI config
            └── Verify: IPsec UP, BGP Established, Health Check ALIVE
```

### Sub-Agent Prompt Files

| File | Purpose |
|------|---------|
| `SUBAGENT_A_VM_PROVISION.md` | Self-contained prompt for VM provisioning sub-agent. Includes DHCP mode, MAC-to-ARP discovery, SSH verification, credential registration. |
| `SUBAGENT_B_FORTIFLEX_TOKEN.md` | Self-contained prompt for FortiFlex token sub-agent. Checks for unused tokens before creating new ones. |

**When modifying sub-agent prompts:**
1. Keep them self-contained — the sub-agent only sees its prompt file, not Skills.md
2. Include all MCP tool canonical IDs and parameter examples
3. Include Bash SSH examples for operations without MCP tools
4. Include error handling tables for known failure modes
5. The prompt MUST specify the exact JSON return format

**When spawning sub-agents from Skills.md:**
- Use absolute file paths (sub-agents cannot resolve relative paths)
- Include key context inline in the Task() prompt (site_id, hypervisor name, admin password)
- See Skills.md "Example: Deploy Site 8" for the exact Task() call format

---

## Key Tool: fortigate-sdwan-spoke-template

**Location:** `tools/org.ulysses.provisioning.fortigate-sdwan-spoke-template/`

This is the main tool that generates FortiGate CLI configuration. Current version: **1.3.0**

### File Structure

```
org.ulysses.provisioning.fortigate-sdwan-spoke-template/
|-- manifest.yaml                                    # Tool metadata, parameters
|-- org.ulysses.provisioning.fortigate-sdwan-spoke-template.py  # Code
`-- Skills.md                                        # AI usage guide
```

### Current Functions (v1.3.0)

| Function | Purpose | Added In |
|----------|---------|----------|
| `configure_system_global()` | hostname, timezone, REST API settings | 1.0.0 |
| `configure_system_settings()` | location-id, ike-tcp-port | 1.0.0 |
| `create_loopback_interface()` | Spoke-Lo interface | 1.0.0 |
| `create_ipsec_phase1()` | VPN tunnels (HUB1-VPN1/2) | 1.0.0 |
| `create_ipsec_phase2()` | Phase2 selectors | 1.0.0 |
| `create_static_route_hub_loopback()` | Routes to hub loopbacks | 1.0.0 |
| `configure_bgp()` | BGP global + neighbor | 1.0.0 |
| `create_sdwan_zone()` | SDWAN_OVERLAY zone | 1.0.0 |
| `add_sdwan_member()` | SD-WAN members for tunnels | 1.0.0 |
| `create_sdwan_health_check()` | HUB_Health check | 1.0.0 |
| `create_firewall_policy()` | Overlay traffic policies | 1.0.0 |
| `configure_sdwan_zone_advpn()` | ADVPN settings on zone | 1.3.0 |
| `create_sdwan_neighbor()` | SD-WAN neighbor for BGP | 1.3.0 |

### Atomic CLI Deployment (Current Default)

The deployment path now supports atomic CLI pushes via SSH. Reference:

- Template: C:/ProgramData/Ulysses/config/blueprints/ATOMIC_SPOKE_TEMPLATE.conf
- Site output: C:/ProgramData/Ulysses/config/blueprints/site-XX/atomic-config-spoke-XX.conf
- Push tool: org.ulysses.noc.fortigate-config-push/2.0.0 (SSH CLI, no API translation)

Keep the atomic template aligned with BASELINE_TEMPLATE.yaml and Skills.md.

### Adding a New Configuration Section

Example: Adding VXLAN support

1. **Add function to spoke-template.py:**
```python
def configure_vxlan(host: str, api_token: str, vni: int,
                    interface: str, verify_ssl: bool = False) -> dict:
    """Configure VXLAN interface."""
    data = {
        "name": f"VXLAN-{vni}",
        "vni": vni,
        "interface": interface,
        # ... other settings
    }
    return make_api_request(host, "/api/v2/cmdb/system/vxlan",
                            api_token, "POST", data, verify_ssl)
```

2. **Add call in main():**
```python
# After SD-WAN neighbor configuration
if params.get("vxlan_enabled"):
    configure_vxlan(target_ip, api_token, params["vxlan_vni"],
                    "Spoke-Lo", verify_ssl)
```

3. **Update manifest.yaml:**
```yaml
parameters:
  properties:
    vxlan_enabled:
      type: boolean
      default: false
      description: "Enable VXLAN overlay"
    vxlan_vni:
      type: integer
      description: "VXLAN Network Identifier"
```

4. **Update Skills.md** with new parameter documentation

5. **Bump version** in manifest.yaml (1.3.0 -> 1.4.0)

6. **Re-sign tool** via Trust Anchor Publisher API

---

## Adding New Deployment Paths

### Example: Adding AWS Deployment

Current workflow supports KVM VMs. To add AWS:

1. **Create new tool:** `org.ulysses.cloud.aws-fortios-provision`
   - Use `trust-bot-toolskill-maker` skill for guidance
   - Implement EC2 launch with FortiGate AMI

2. **Create BLOCK_1A_PROVISION_AWS.yaml:**
```yaml
block_id: provision_aws
block_number: 1
name: "AWS FortiGate Provisioning"
version: "1.0.0"

depends_on: [blueprint_wizard]

tools:
  - canonical_id: "org.ulysses.cloud.aws-fortios-provision/1.0.0"
    purpose: "Launch FortiGate EC2 instance"
```

3. **Update BLOCK_0** to ask deployment platform:
```yaml
- id: deployment_platform
  question: "Where should the FortiGate be deployed?"
  options:
    - value: "kvm"
      label: "On-premise KVM"
      followup: [hypervisor_name]
    - value: "aws"
      label: "AWS EC2"
      followup: [aws_region, vpc_id, subnet_id]
```

4. **Update Skills.md** workflow section

5. **Test dry-run with new parameters**

---

## Testing Requirements

### Before Pushing Changes

1. **Syntax check:**
```bash
python -m py_compile tools/org.ulysses.*/org.ulysses.*.py
```

2. **Local test (if tool has CLI mode):**
```bash
python tool.py "test_param"
```

3. **Dry-run test:**
   - Run workflow with `execution_mode: dry-run`
   - Verify generated config matches BASELINE_TEMPLATE naming

4. **Contract validation:**
   - Check all contract checks pass (count defined in Skills.md / BLOCK_4_VERIFY.yaml)
   - Verify no naming violations

### After Signing

1. **Integration test:**
```bash
execute_certified_tool("org.ulysses.../1.x.x", {test_params})
```

2. **Full workflow test:**
   - Deploy a test site (site_id=99 or similar)
   - Verify IPsec UP, BGP Established
   - Delete test site

---

## Tool Signing Process

After modifying any tool, you MUST re-sign it:

1. **Bump version** in manifest.yaml

2. **Submit to Trust Anchor:**
```python
# POST /publisher/submit-tool
{
    "manifest": <parsed_manifest>,
    "code_python": <tool_code>,
    "skills_content": <skills_md>
}
```

3. **Certify:**
```python
# POST /publisher/certify/{canonical_id}
# URL-encode the / in canonical_id
```

4. **Sync local manifest:**
```bash
python scripts/sync_signatures_to_local.py
```

5. **Commit and push** updated manifest

For detailed guidance, invoke `/trust-bot-toolskill-maker` skill.

---

## Common Mistakes to Avoid

### 1. Naming Violations

```
WRONG: set interface-name "spoke-loopback"
RIGHT: set interface-name "Spoke-Lo"        # From BASELINE_TEMPLATE

WRONG: config vpn ipsec phase1-interface "vpn1"
RIGHT: config vpn ipsec phase1-interface "HUB1-VPN1"  # From BASELINE_TEMPLATE
```

### 2. Critical Settings

```
WRONG: set transport auto
RIGHT: set transport udp

WRONG: set ike-tcp-port 4500
RIGHT: set ike-tcp-port 11443

WRONG: set add-route enable
RIGHT: set add-route disable   # Routes via BGP, not IPsec
```

### 3. Version Bumps Without Re-signing

If you bump version but don't re-sign, Trust Anchor runs OLD code!

```
WRONG:
1. Edit tool code
2. Change version 1.0.0 -> 1.0.1 in manifest
3. Git commit
4. FORGET to re-sign  <- BUG

RIGHT:
1. Edit tool code
2. Change version 1.0.0 -> 1.0.1 in manifest
3. Submit to Trust Anchor
4. Certify
5. Sync local manifest
6. Git commit
```

### 4. Breaking Existing Parameters

Don't remove or rename parameters that other tools/blocks depend on.

```
WRONG: Rename "spoke_loopback_ip" -> "loopback"
       (Breaks all callers)

RIGHT: Add "loopback" as alias, keep "spoke_loopback_ip" working
       OR: Bump major version and update all callers
```

---

## Quick Checklist for Changes

Before submitting any change:

- [ ] Read BASELINE_TEMPLATE.yaml (understand the contract)
- [ ] Check if change affects naming conventions
- [ ] Update Skills.md if workflow steps change
- [ ] Update manifest.yaml if parameters change
- [ ] Bump tool version if code changes
- [ ] Re-sign tool after code changes
- [ ] Test dry-run mode first
- [ ] Verify contract validation passes (all checks)
- [ ] Update DEVELOPER_ONBOARDING.md if architecture changes

---

## Getting Help

- **Deployment questions:** Read `workflows/add-sdwan-site/Skills.md`
- **Tool building:** Invoke `/trust-bot-toolskill-maker` skill
- **Solution pack structure:** Read `CODE_MAP.md`
- **Naming conventions:** Read `BASELINE_TEMPLATE.yaml`

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-24 | Initial developer onboarding guide |




