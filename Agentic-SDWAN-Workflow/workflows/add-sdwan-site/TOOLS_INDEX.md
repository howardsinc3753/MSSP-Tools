# SD-WAN Workflow - Tools Index

This document indexes all MCP certified tools used by the Add SD-WAN Site workflow.

**Last Updated:** 2026-01-26

---

## Core Workflow Tools

These tools are directly called during workflow execution.

### BLOCK_0: Blueprint & Planning

| Tool | Version | Skills.md Path |
|------|---------|----------------|
| **fortigate-sdwan-manifest-tracker** | 1.0.0 | `tools/org.ulysses.noc.fortigate-sdwan-manifest-tracker/Skills.md` |
| **fortigate-sdwan-blueprint-planner** | 1.0.6 | `tools/org.ulysses.noc.fortigate-sdwan-blueprint-planner/Skills.md` |

### BLOCK_1: Provision

| Tool | Version | Skills.md Path |
|------|---------|----------------|
| **kvm-fortios-provision** | 1.0.11 | `tools/org.ulysses.sdwan.kvm-fortios-provision/Skills.md` |
| **fortigate-health-check** | 1.0.4 | `tools/org.ulysses.noc.fortigate-health-check/Skills.md` |
| **hypervisor-credential-manager** | 1.0.0 | `tools/org.ulysses.provisioning.hypervisor-credential-manager/Skills.md` |

### BLOCK_2: License + API Onboarding

| Tool | Version | Skills.md Path |
|------|---------|----------------|
| **fortiflex-entitlements-list** | 1.0.0 | `tools/org.ulysses.cloud.fortiflex-entitlements-list/Skills.md` |
| **fortiflex-token-create** | 1.0.3 | `tools/org.ulysses.cloud.fortiflex-token-create/Skills.md` |
| **fortigate-cli-execute** | 1.0.0 | `tools/org.ulysses.noc.fortigate-cli-execute/Skills.md` |
| **fortigate-onboard** | 1.0.1 | `tools/org.ulysses.noc.fortigate-onboard/Skills.md` |
| **fortigate-health-check** | 1.0.4 | `tools/org.ulysses.noc.fortigate-health-check/Skills.md` |

> **MANDATORY:** `fortigate-onboard/1.0.1` MUST run after license reboot. It creates the API user + token that ALL subsequent tools need. Without it, BLOCK_4 verification tools return 401.

> **VM Restart:** After license application, the FortiGate VM shuts down. Use `kvm-fortios-provision/1.0.11` with `action: start` to restart it (GAP-35 CLOSED). See BLOCK_2 Step 6.

### BLOCK_3: Configure

| Tool | Version | Skills.md Path |
|------|---------|----------------|
| **fortigate-config-push** | 2.0.0 | `tools/org.ulysses.noc.fortigate-config-push/Skills.md` |
| **credential-manager** | 1.0.0 | `tools/org.ulysses.provisioning.credential-manager/Skills.md` |

### BLOCK_4: Verify

| Tool | Version | Skills.md Path |
|------|---------|----------------|
| **fortigate-sdwan-status** | 1.2.0 | `tools/org.ulysses.noc.fortigate-sdwan-status/Skills.md` |
| **fortigate-bgp-troubleshoot** | 1.0.3 | `tools/org.ulysses.noc.fortigate-bgp-troubleshoot/Skills.md` |
| **fortigate-health-check** | 1.0.4 | `tools/org.ulysses.noc.fortigate-health-check/Skills.md` |
| **fortigate-ssh** | 1.0.7 | `tools/org.ulysses.noc.fortigate-ssh/Skills.md` |

> **Note:** `fortigate-sdwan-status/1.1.0` and `fortigate-bgp-troubleshoot/1.0.2` are FortiOS 7.6.5 compatible with correct API endpoints and MCP credential support. Published 2026-01-26.

---

## Supporting Tools

Additional tools that may be used for troubleshooting or advanced scenarios.

### SD-WAN Configuration Tools

| Tool | Version | Skills.md Path | Purpose |
|------|---------|----------------|---------|
| **fortigate-sdwan-member** | 1.0.3 | `tools/org.ulysses.noc.fortigate-sdwan-member/Skills.md` | Add/modify SD-WAN members |
| **fortigate-sdwan-zone** | 1.0.0 | `tools/org.ulysses.noc.fortigate-sdwan-zone/Skills.md` | Create/manage SD-WAN zones |
| **fortigate-sdwan-neighbor** | 1.2.0 | `tools/org.ulysses.noc.fortigate-sdwan-neighbor/Skills.md` | Configure BGP neighbors |
| **fortigate-sdwan-health-check** | 1.2.0 | `tools/org.ulysses.noc.fortigate-sdwan-health-check/Skills.md` | Define SLA health checks |
| **fortigate-sdwan-onboard** | 1.0.0 | `tools/org.ulysses.noc.fortigate-sdwan-onboard/Skills.md` | Complete spoke onboarding |

### FortiFlex License Tools

| Tool | Version | Skills.md Path | Purpose |
|------|---------|----------------|---------|
| **fortiflex-programs-list** | 1.0.0 | `tools/org.ulysses.cloud.fortiflex-programs-list/Skills.md` | List FortiFlex programs |
| **fortiflex-config-list** | 1.0.0 | `tools/org.ulysses.cloud.fortiflex-config-list/Skills.md` | List config templates |
| **fortiflex-config-create** | 1.0.0 | `tools/org.ulysses.cloud.fortiflex-config-create/Skills.md` | Create new config |

### Device Provisioning Tools

| Tool | Version | Skills.md Path | Purpose |
|------|---------|----------------|---------|
| **fortigate-api-token-create** | 1.0.0 | `tools/org.ulysses.provisioning.fortigate-api-token-create/Skills.md` | Generate REST API token |
| **fortigate-device-register** | 1.0.0 | `tools/org.ulysses.provisioning.fortigate-device-register/Skills.md` | Register device credentials |
| **fortigate-onboard** | 1.0.1 | `tools/org.ulysses.noc.fortigate-onboard/Skills.md` | Full device onboarding (MANDATORY in BLOCK_2) |
| **fortigate-set-hostname** | 1.0.0 | `tools/org.ulysses.provisioning.fortigate-set-hostname/Skills.md` | Set device hostname |
| **fortigate-single-hub-bgp-sdwan** | 1.0.0 | `tools/org.ulysses.provisioning.fortigate-single-hub-bgp-sdwan/Skills.md` | Single-hub config |
| **fortigate-sdwan-hub-template** | 1.0.0 | `tools/org.ulysses.provisioning.fortigate-sdwan-hub-template/Skills.md` | Hub configuration |

---

## Tool Discovery

Use `route_query` to find the right tool for any task:

```python
# Examples
route_query("provision fortigate vm")           # → kvm-fortios-provision
route_query("check fortigate health")           # → fortigate-health-check
route_query("configure sdwan member")           # → fortigate-sdwan-member
route_query("list fortiflex entitlements")      # → fortiflex-entitlements-list
route_query("push fortigate config")            # → fortigate-config-push
route_query("execute cli command")              # → fortigate-cli-execute
```

---

## Credential Files

Tools check credentials in priority order (first match wins):

| Credential Type | PRIMARY Path | Backup Path |
|-----------------|-------------|-------------|
| FortiGate devices (API + SSH) | `~/.config/mcp/fortigate_credentials.yaml` | `C:/ProgramData/mcp/fortigate_credentials.yaml` |
| FortiCloud / FortiFlex API | `C:/ProgramData/mcp/forticloud_credentials.yaml` | — |
| Hypervisor SSH | Key-based auth to `root@192.168.209.115` (ed25519, autonomous) | — |

**IMPORTANT:** Keep the PRIMARY file up to date. Tools use it first and never check backups if it exists.

---

## Version Update Checklist

When updating tool versions in this workflow:

1. Update version in this index
2. Update version in `Skills.md` Tool Dependencies table
3. Update version in `BLOCK_*.yaml` files if hardcoded
4. Re-sign tool via Trust Anchor if code changed
5. Test workflow end-to-end

---

## Quick Reference: Canonical IDs

```
# Blueprint
org.ulysses.noc.fortigate-sdwan-manifest-tracker/1.0.0
org.ulysses.noc.fortigate-sdwan-blueprint-planner/1.0.7

# Provision + VM Lifecycle
org.ulysses.sdwan.kvm-fortios-provision/1.0.11          # start/stop/status/provision/destroy/list
org.ulysses.noc.fortigate-health-check/1.0.4
org.ulysses.provisioning.hypervisor-credential-manager/1.0.0

# License + Onboard
org.ulysses.cloud.fortiflex-entitlements-list/1.0.0
org.ulysses.cloud.fortiflex-token-create/1.0.3
org.ulysses.noc.fortigate-cli-execute/1.0.1
org.ulysses.noc.fortigate-onboard/1.0.1         # MANDATORY: Creates API token

# Configure
org.ulysses.noc.fortigate-config-push/2.0.0     # SSH CLI push (not API translation)
org.ulysses.provisioning.credential-manager/1.0.0

# Verify
org.ulysses.noc.fortigate-sdwan-status/1.1.0    # FortiOS 7.6.5 compatible
org.ulysses.noc.fortigate-bgp-troubleshoot/1.0.2 # FortiOS 7.6.5 compatible
org.ulysses.noc.fortigate-health-check/1.0.4
```
