# Agentic SD-WAN Workflow

**AI-Driven FortiGate SD-WAN Provisioning with Cryptographic Trust**

---

## What This Is

An autonomous SD-WAN deployment system where **Claude AI** orchestrates the entire lifecycle of a FortiGate SD-WAN spoke site: KVM virtual machine provisioning, FortiFlex cloud licensing, full ADVPN/BGP/SD-WAN configuration push, and automated verification -- all through a conversational interface.

Built on **MCP 2.0** (Model Context Protocol) with a **Trust Anchor** security model where every tool is RSA-signed and cryptographically verified before execution. The AI agent cannot execute unsigned or tampered tools. Credentials never leave the execution boundary.

Part of **Project Ulysses** -- an open platform for building secure AI-to-infrastructure automation.

**Proven in production:** 5+ spoke sites (7-11) provisioned end-to-end via AI agent conversation. Hub running in production with full ADVPN mesh.

---

## Architecture

```
Operator               Claude AI                MCP Trust Anchor          Infrastructure
(Human)                (Agent)                  (Crypto Verified)         (Devices)
  |                       |                          |                        |
  |  "Deploy site 12"     |                          |                        |
  |---------------------->|                          |                        |
  |                       |  list_certified_tools()  |                        |
  |                       |------------------------->|                        |
  |                       |  [15 signed tools]       |                        |
  |                       |<-------------------------|                        |
  |                       |                          |                        |
  |                       |  BLOCK 0: Blueprint      |                        |
  |  "Site ID? LAN?"      |  Wizard (Q&A)            |                        |
  |<----------------------|                          |                        |
  |  "12, 10.12.1.0/24"   |                          |                        |
  |---------------------->|                          |                        |
  |                       |                          |                        |
  |                       |  BLOCK 1: Provision VM   |                        |
  |                       |  execute_certified_tool  |                        |
  |                       |  (kvm-fortios-provision) |                        |
  |                       |------------------------->|  verify RSA sig        |
  |                       |                          |----> SSH to KVM ------>|
  |                       |                          |                   [VM Created]
  |                       |                          |                        |
  |                       |  BLOCK 2: License        |                        |
  |                       |  (fortiflex-token)       |                        |
  |                       |------------------------->|  FortiFlex API ------->|
  |                       |                          |                   [Licensed]
  |                       |                          |                        |
  |                       |  BLOCK 3: Config Push    |                        |
  |                       |  (13 atomic sections)    |                        |
  |                       |------------------------->|  verify RSA sig        |
  |                       |                          |----> SSH CLI push ---->|
  |                       |                          |                   [Configured]
  |                       |                          |                        |
  |                       |  BLOCK 4: Verify         |                        |
  |                       |  (sdwan-status, bgp)     |                        |
  |                       |------------------------->|  API + SSH checks ---->|
  |                       |                          |                        |
  |  "Site 12: IPsec UP,  |                          |                        |
  |   BGP Established,    |                          |                        |
  |   Health GREEN"       |                          |                        |
  |<----------------------|                          |                        |
```

---

## Workflow Phases

| Phase | Block | What Happens | Key MCP Tools |
|-------|-------|-------------|---------------|
| **Planning** | BLOCK_0 | Blueprint wizard collects site params, derives IPs, validates uniqueness | `manifest-tracker`, `blueprint-planner` |
| **Provision** | BLOCK_1 | FortiGate VM created on KVM with bootstrap ISO (zero-touch) | `kvm-fortios-provision` |
| **License** | BLOCK_2 | FortiFlex token generated and applied via SSH | `fortiflex-token-create`, `fortigate-cli-execute` |
| **Configure** | BLOCK_3 | Full SD-WAN config pushed (13 atomic sections, ~8 seconds) | `fortigate-config-push` |
| **Verify** | BLOCK_4 | IPsec tunnels UP, BGP Established, SD-WAN health GREEN | `fortigate-sdwan-status`, `fortigate-ssh` |

### Execution Modes

| Mode | Description |
|------|-------------|
| **Live Deploy** | Full automation: BLOCK_0 through BLOCK_4 with real device interaction |
| **Dry Run** | Generate and validate config only, save for later deployment |

---

## Atomic Configuration System

Each FortiOS feature is a composable `.block` file with YAML metadata header + raw CLI body. This enables:

- **Dependency-aware ordering** -- BGP base before neighbor-range, phase1 before tunnel settings
- **Template variables** -- `{{SITE_ID}}`, `{{HUB_IP}}`, `{{PSK}}` -- no hardcoded values
- **Single-push deployment** -- ~8 seconds for a complete 300-line spoke config
- **Reusable across sites** -- same blocks, different parameters

### Block Inventory

| Role | Blocks | Range |
|------|--------|-------|
| **Hub** | 10 atomic blocks | 020-029 (system, interfaces, IPsec, BGP, SD-WAN, firewall) |
| **Spoke** | 13 config sections | System, interfaces, DHCP, IPsec, BGP, SD-WAN, firewall |
| **Rules** | Expandable | 10000+ (SD-WAN app steering rules like O365) |

### Block Numbering Convention

| Range | Domain |
|-------|--------|
| 1-19 | Core spoke infrastructure |
| 20-39 | Core hub infrastructure |
| 40-49 | Dual-hub extensions |
| 100-199 | SD-WAN advanced (app steering) |
| 10000+ | SD-WAN rules (O365, Zoom, etc.) |

### Example: Hub IPsec Phase1 Block

```yaml
---
block_id: 023
name: hub-ipsec-phase1-template
device_role: hub
depends_on:
  - block_id: 022
    reason: "Interfaces must exist (needs BGP_Lo for exchange-ip-addr4)"
---

config vpn ipsec phase1-interface
    edit "SPOKE_VPN1"
        set type dynamic
        set interface "{{WAN_INTERFACE}}"
        set ike-version 2
        set psksecret {{PSK}}
        set auto-discovery-sender enable
        set network-overlay enable
        set network-id 1
        set exchange-ip-addr4 {{BGP_LOOPBACK_IP}}
        set transport udp
    next
end
```

---

## MCP Trust Anchor Security

The system enforces a cryptographic chain of trust:

1. **Tool Signing** -- Every tool is RSA-4096 signed by the Publisher Node
2. **Signature Verification** -- Trust Anchor verifies signatures before allowing execution
3. **Credential Isolation** -- Credentials never embedded in tools; resolved at runtime via secure credential provider (Windows DPAPI or YAML fallback)
4. **Audit Trail** -- Every tool execution is logged with caller, parameters, and result
5. **No Bash Escape** -- AI agent is instructed to use ONLY certified tools, never raw SSH/curl

---

## Prerequisites

| Requirement | Details |
|-------------|---------|
| **Claude Code** | Anthropic Claude Code CLI with MCP tool support |
| **MCP Server** | Trust Anchor server (Python, default port 8000) |
| **KVM Hypervisor** | Rocky Linux 9 with libvirt, for VM provisioning |
| **FortiOS Base Image** | `fortios-7.6.5-base.qcow2` on hypervisor |
| **FortiFlex Account** | Fortinet cloud licensing for FortiGate VMs |
| **FortiGate Hub** | At least one hub with ADVPN/BGP configured |
| **Network** | Management VLAN connectivity to hub and hypervisor |

---

## Quick Start

1. **Install Claude Code** and configure the MCP secure-tools server connection
2. **Verify Trust Anchor** is running: `list_certified_tools(vendor="fortinet")`
3. **Configure credentials** in `~/.config/mcp/fortigate_credentials.yaml` and `hypervisor_credentials.yaml`
4. **Deploy your hub** using `templates/ATOMIC_HUB_TEMPLATE.conf` (substitute variables)
5. **Invoke the workflow**: Tell the AI *"Add a new SD-WAN site"*
6. **Answer the wizard** -- site ID, WAN mode, LAN subnet, PSK
7. **Watch the AI** provision, license, configure, and verify automatically

---

## Package Contents

```
Agentic-SDWAN-Workflow/
├── README.md                              # This file
├── docs/
│   ├── architecture-overview.md           # MCP 2.0 architecture deep-dive
│   ├── pilot-guide.html                   # Fortinet-branded pilot guide
│   ├── train-your-human.md               # Operator onboarding
│   └── SDWAN-PROVISIONING-TRACKER.md     # Development progress tracker
├── solution-pack/
│   ├── solution-pack.yaml                 # Pack definition (tools, domains)
│   ├── SKILLS.md                          # Top-level AI skills
│   └── DEVELOPER_ONBOARDING.md            # Developer extension guide
├── workflows/
│   ├── add-sdwan-site/                    # Main workflow
│   │   ├── Skills.md                      # AI routing guide (the brain)
│   │   ├── manifest.yaml                  # Orchestration definition
│   │   ├── FRAMEWORK.md                   # Block stacking pattern
│   │   ├── CONTRACT_SCHEMA.yaml           # Config validation rules
│   │   ├── BASELINE_TEMPLATE.yaml         # Naming conventions
│   │   ├── TOOLS_INDEX.md                 # Tool catalog per phase
│   │   ├── blocks/BLOCK_0-4*.yaml         # 5 workflow phase definitions
│   │   └── hooks/validate_prerequisites.py
│   └── add-sdwan-rule/                    # SD-WAN rule workflow
├── atomic-config-blocks/
│   ├── hub/blocks/020-029*.block          # 10 hub atomic blocks
│   ├── spoke/workflows/                   # Spoke Skills.md
│   └── rules/blocks/                      # SD-WAN rule blocks
├── templates/
│   ├── ATOMIC_HUB_TEMPLATE.conf           # Full hub config ({{variables}})
│   └── ATOMIC_SPOKE_TEMPLATE.conf         # Full spoke config ({{variables}})
├── examples/
│   └── site-11/atomic-config-spoke-11.conf # Real deployed config
├── knowledge/                             # SD-WAN reference corpus (5 docs)
├── nfrs/                                  # Architecture vision docs (3 NFRs)
└── tests/
    └── qa_fortigate_ops_tests.py          # QA test suite
```

---

## Key Technical Details

| Parameter | Value |
|-----------|-------|
| **FortiOS Version** | 7.6.5 |
| **BGP AS Number** | 65000 (iBGP, all sites) |
| **Loopback Scheme** | 172.16.0.{site_id}/32 |
| **Hub Loopbacks** | 172.16.255.252 (BGP), 172.16.255.253 (Health) |
| **IPsec** | IKEv2, ADVPN, dual tunnels (HUB1-VPN1, HUB1-VPN2) |
| **Transport** | UDP (port 11443 for IKE-TCP fallback) |
| **LAN Scheme** | 10.{site_id}.1.0/24 |
| **Config Push** | SSH CLI, 13 sections, ~8 seconds |

---

## Lab Network Topology (Reference)

| Device | IP | Role |
|--------|-----|------|
| sdwan-hub-1 | 192.168.215.15 | SD-WAN Hub (ADVPN + BGP) |
| sdwan-spoke-07 | DHCP | Spoke (site_id=7) |
| sdwan-spoke-08 | DHCP | Spoke (site_id=8) |
| sdwan-spoke-09 | DHCP | Spoke (site_id=9) |
| sdwan-spoke-10 | DHCP | Spoke (site_id=10) |
| sdwan-spoke-11 | DHCP | Spoke (site_id=11) |

---

## Disclaimer

This is **NOT** an official Fortinet product. This is a personal project by Daniel Howard (MSSP Solutions Engineer) for demonstrating AI-driven network automation capabilities. Use at your own risk. Always test in a lab environment before any production deployment. Fortinet, FortiGate, FortiOS, and FortiFlex are trademarks of Fortinet, Inc.

---

## About

**Author:** Daniel Howard
**Role:** MSSP Solutions Engineer, Fortinet
**Platform:** Project Ulysses -- Open AI-to-Infrastructure Automation
**AI Engine:** Claude (Anthropic) via Claude Code CLI
**Status:** Active Development -- 5+ spoke sites deployed, hub operational
