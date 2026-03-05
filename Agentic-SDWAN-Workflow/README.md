# Agentic SD-WAN Workflow

**A complete, working reference for building AI-driven FortiGate SD-WAN automation.**

This repo contains everything an AI agent needs to deploy SD-WAN spoke sites autonomously: the Python tools, workflow definitions, atomic config blocks, templates, knowledge base, and a real deployed example. Point your AI here and start building.

---

## AI Agents: Start Here

If you are an AI agent (Claude, GPT, Copilot, or similar) being pointed at this repo by an engineer, read this section first.

### What you have access to

1. **`tools/`** -- 14 Python tools that do the actual work (SSH into FortiGates, provision VMs, apply licenses, push config, verify tunnels). Each tool has a `Skills.md` that explains its parameters, examples, and error handling.

2. **`workflows/add-sdwan-site/Skills.md`** -- The master workflow brain. This is the most important file. It defines the 5-phase block-stacking pattern for deploying a spoke site end-to-end.

3. **`atomic-config-blocks/`** -- Composable FortiOS CLI config blocks with YAML metadata headers. Each `.block` file is a self-contained, dependency-aware config fragment with `{{TEMPLATE_VARIABLES}}`.

4. **`templates/`** -- Complete hub and spoke configs with all variables parameterized. Ready to render and push.

5. **`knowledge/`** -- SD-WAN reference corpus: API reference, quickstart, tool targets, and solution pack skills.

### How to use this repo

**Option A: Follow the existing workflow** -- Read `workflows/add-sdwan-site/Skills.md` and execute the 5 blocks (BLOCK_0 through BLOCK_4) in order. Each block YAML in `workflows/add-sdwan-site/blocks/` defines inputs, outputs, tool calls, and error recovery.

**Option B: Build your own flow** -- Use the tools and config blocks as building blocks. The tools are standalone Python scripts. The config blocks are composable. Mix and match for your topology.

**Option C: Just grab the configs** -- If you only need FortiOS CLI configs for hub/spoke ADVPN+BGP SD-WAN, look at `templates/` and `examples/`.

### Key files to read first

| Priority | File | Why |
|----------|------|-----|
| 1 | `workflows/add-sdwan-site/Skills.md` | Master workflow -- the complete brain |
| 2 | `knowledge/SDWAN-QUICKSTART.md` | Network design decisions and topology |
| 3 | `templates/ATOMIC_SPOKE_TEMPLATE.conf` | What a complete spoke config looks like |
| 4 | `templates/ATOMIC_HUB_TEMPLATE.conf` | What a complete hub config looks like |
| 5 | `tools/` (browse Skills.md in each) | What each tool does and how to call it |

---

## What This Does

An AI agent deploys a FortiGate SD-WAN spoke site in 5 phases:

```
Phase 0: BLUEPRINT    ->  Wizard collects site params, derives all IPs
Phase 1: PROVISION    ->  Create FortiGate VM on KVM hypervisor
Phase 2: LICENSE      ->  Apply FortiFlex cloud license, onboard device
Phase 3: CONFIGURE    ->  Push full ADVPN/BGP/SD-WAN config (13 sections, ~8 sec)
Phase 4: VERIFY       ->  Confirm IPsec UP, BGP Established, SD-WAN health GREEN
```

Each phase is defined in a BLOCK YAML file with explicit inputs, outputs, tool dependencies, error scenarios, and recovery steps. The AI follows the blocks sequentially -- if a block fails, it uses the error recovery tree before moving on.

**Proven in lab:** 5+ spoke sites provisioned end-to-end via AI conversation.

---

## Tools (14 Python Scripts)

These are the tools the AI calls to interact with infrastructure. Each tool directory contains the Python implementation, a `manifest.yaml` with metadata, and a `Skills.md` with usage documentation.

| Tool | What It Does |
|------|-------------|
| `kvm-fortios-provision` | Provision/manage FortiGate VMs on KVM (libvirt) |
| `fortigate-cli-execute` | Execute arbitrary FortiOS CLI commands via SSH |
| `fortigate-config-push` | Push multi-line config blocks via SSH |
| `fortigate-ssh` | Read-only FortiOS commands via SSH |
| `fortigate-health-check` | Verify device reachability (ping, SSH, HTTPS) |
| `fortigate-license-apply` | Apply FortiFlex license token via SSH |
| `fortigate-onboard` | Register device credentials + create API user |
| `fortigate-sdwan-spoke-template` | Render and push complete spoke config |
| `fortigate-sdwan-status` | Query SD-WAN member/health/zone state |
| `fortigate-bgp-troubleshoot` | Diagnose BGP neighbor/route issues |
| `fortigate-sdwan-blueprint-planner` | Generate config from site parameters |
| `fortigate-sdwan-manifest-tracker` | Track deployed sites and topology |
| `fortiflex-token-create` | Generate FortiFlex VM license tokens |
| `fortiflex-entitlements-list` | List available FortiFlex entitlements |

**Shared libraries** in `tools/shared/`: credential provider, FortiGate credential helper, constants.

### How to adapt tools for your environment

The tools were built to run inside an MCP (Model Context Protocol) server, but the Python logic is standalone. To use them directly:

1. Install dependencies: `paramiko` (SSH), `requests` (REST API)
2. Set up a credentials file (see `tools/shared/fortigate_creds.py` for the expected format)
3. Call the tool main function with the parameters documented in its Skills.md
4. Or wrap them in your own MCP server, LangChain tool, or function-calling framework

---

## Atomic Config Blocks

FortiOS configuration is broken into composable `.block` files. Each has a YAML header (block_id, name, dependencies) followed by raw FortiOS CLI.

### Hub Blocks (020-029)

| Block | Name | What It Configures |
|-------|------|-------------------|
| 020 | system-global | Hostname, timezone, admin settings |
| 021 | system-settings | Location-id, allow-subnet-overlap |
| 022 | interfaces | WAN, loopbacks (BGP + health-check) |
| 023 | ipsec-phase1-template | Dynamic ADVPN phase1 (type=dynamic, sender) |
| 024 | ipsec-phase2-template | Dynamic ADVPN phase2 |
| 025 | bgp-base | Router BGP, AS 65000, networks |
| 026 | bgp-neighbor-range | Accept spokes from 172.16.0.0/16 |
| 027 | sdwan-zone | SD-WAN zones (OVERLAY, UNDERLAY) |
| 028 | sdwan-healthcheck | Health check to spoke loopbacks |
| 029 | firewall-policies | Inter-zone traffic policies |

### Spoke Config (13 sections in template)

System global, settings, interfaces, DHCP server, IPsec phase1 (x2 tunnels), IPsec phase2 (x2), static routes, SD-WAN zones/members/health-check, BGP, firewall policies.

### SD-WAN Rules

Block IDs 10000+ for application steering (e.g., `10101-sdwan-rule-o365.block`).

---

## Network Design

| Parameter | Value |
|-----------|-------|
| **FortiOS** | 7.6.5 |
| **BGP AS** | 65000 (iBGP, all sites same AS) |
| **Loopback scheme** | 172.16.0.{site_id}/32 per spoke |
| **Hub loopbacks** | 172.16.255.252 (BGP RID), 172.16.255.253 (health-check) |
| **IPsec** | IKEv2, ADVPN, dual overlays (VPN1 + VPN2) |
| **LAN scheme** | 10.{site_id}.1.0/24 |
| **Transport** | UDP |
| **Config push** | SSH CLI, 13 sections, ~8 seconds total |

---

## Package Contents

```
Agentic-SDWAN-Workflow/
+-- README.md                              <- You are here
|
+-- tools/                                 <- 14 Python tool implementations
|   +-- org.ulysses.sdwan.kvm-fortios-provision/
|   |   +-- *.py, manifest.yaml, Skills.md
|   +-- org.ulysses.noc.fortigate-cli-execute/
|   +-- org.ulysses.noc.fortigate-config-push/
|   +-- org.ulysses.noc.fortigate-ssh/
|   +-- org.ulysses.noc.fortigate-health-check/
|   +-- org.ulysses.noc.fortigate-sdwan-status/
|   +-- org.ulysses.noc.fortigate-bgp-troubleshoot/
|   +-- org.ulysses.noc.fortigate-sdwan-blueprint-planner/
|   +-- org.ulysses.noc.fortigate-sdwan-manifest-tracker/
|   +-- org.ulysses.provisioning.fortigate-license-apply/
|   +-- org.ulysses.provisioning.fortigate-onboard/
|   +-- org.ulysses.provisioning.fortigate-sdwan-spoke-template/
|   +-- org.ulysses.cloud.fortiflex-token-create/
|   +-- org.ulysses.cloud.fortiflex-entitlements-list/
|   +-- shared/                            # Credential provider, constants
|
+-- workflows/
|   +-- add-sdwan-site/                    <- Main workflow
|   |   +-- Skills.md                      # THE BRAIN - read this first
|   |   +-- manifest.yaml                  # Orchestration definition
|   |   +-- blocks/BLOCK_0-4*.yaml         # 5 workflow phase definitions
|   |   +-- CONTRACT_SCHEMA.yaml           # Config validation rules
|   |   +-- BASELINE_TEMPLATE.yaml         # Naming conventions
|   |   +-- FRAMEWORK.md                   # Block stacking pattern
|   |   +-- TOOLS_INDEX.md                 # Tool catalog per phase
|   |   +-- hooks/validate_prerequisites.py
|   +-- add-sdwan-rule/                    # SD-WAN app steering rules
|
+-- atomic-config-blocks/
|   +-- hub/blocks/020-029*.block          # 10 hub config blocks
|   +-- hub/workflows/add-sdwan-hub-Skills.md
|   +-- spoke/workflows/add-sdwan-site-Skills.md
|   +-- rules/blocks/10101*.block          # SD-WAN rule blocks
|
+-- templates/
|   +-- ATOMIC_HUB_TEMPLATE.conf           # Complete hub - all {{variables}}
|   +-- ATOMIC_SPOKE_TEMPLATE.conf         # Complete spoke - all {{variables}}
|
+-- examples/
|   +-- site-11/atomic-config-spoke-11.conf  # Real deployed spoke config
|
+-- knowledge/                             # SD-WAN reference corpus
|   +-- SDWAN-QUICKSTART.md, SDWAN-API-REFERENCE.md, SDWAN-CORPUS.md
|   +-- SDWAN-SOLUTION-PACK-SKILLS.md, SDWAN-TOOL-TARGETS.md
|
+-- solution-pack/                         # Solution pack metadata
|   +-- solution-pack.yaml, SKILLS.md, DEVELOPER_ONBOARDING.md
|
+-- docs/SDWAN-PROVISIONING-TRACKER.md     # Development history + lessons
+-- tests/qa_fortigate_ops_tests.py
```

---

## Getting Started for Partners

### What you need

- **An AI agent** -- Claude Code, Cursor, Windsurf, GPT with function calling, or any LLM that can read files and execute Python
- **A KVM hypervisor** -- Rocky Linux 9 with libvirt (for VM provisioning)
- **FortiOS base image** -- `fortios-7.6.5-base.qcow2`
- **FortiFlex account** -- For VM licensing (or use eval licenses)
- **A FortiGate hub** -- Use `templates/ATOMIC_HUB_TEMPLATE.conf` to set one up
- **SSH access** -- Key-based auth to hypervisor; password or key auth to FortiGates

### Quickstart

1. Clone this repo
2. Point your AI at this README (or at `workflows/add-sdwan-site/Skills.md` directly)
3. Tell it: *"Read the Skills.md and deploy a new SD-WAN spoke site"*
4. The AI will walk through the 5-phase workflow, calling tools as needed
5. Adapt the tools to your execution framework (MCP, LangChain, direct Python, etc.)

### Adapting for your environment

- **Different hypervisor?** -- Replace `kvm-fortios-provision` with your own provisioning logic
- **Hardware FortiGates?** -- Skip BLOCK_1 (provision) and BLOCK_2 (license), start at BLOCK_3
- **Different AI?** -- The Skills.md files are LLM-agnostic; they work as system prompts for any model
- **No FortiFlex?** -- Use eval licenses or skip the licensing block entirely

---

## Disclaimer

This is **NOT** an official Fortinet product. This is a personal project by Daniel Howard (MSSP Solutions Engineer) for demonstrating AI-driven network automation capabilities. Use at your own risk. Always test in a lab environment before production. Fortinet, FortiGate, FortiOS, and FortiFlex are trademarks of Fortinet, Inc.

---

**Author:** Daniel Howard | **Role:** MSSP Solutions Engineer, Fortinet
**AI Engine:** Claude (Anthropic) via Claude Code CLI | **Status:** Active Development
