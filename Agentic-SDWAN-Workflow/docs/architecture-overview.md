# Architecture Overview: MCP 2.0 Trust Anchor for Agentic SD-WAN

## The Problem

Giving an AI agent direct SSH/API access to production network devices is dangerous. There's no audit trail, no access control, and no way to verify what code the agent is actually executing. Traditional automation (Ansible, Terraform) solves this with static playbooks -- but loses the adaptive intelligence that makes AI valuable.

## The Solution: Cryptographic Trust Boundary

MCP 2.0 introduces a **Trust Anchor** -- a cryptographic intermediary between the AI agent and infrastructure. Every tool the agent can execute must be:

1. **Published** -- Submitted to the Publisher Node with manifest, code, and Skills.md
2. **Signed** -- RSA-4096 signed by the Publisher's private key
3. **Registered** -- Stored in the Trust Anchor's certified tool registry
4. **Verified** -- Signature and hash checked before every execution

The AI agent never touches devices directly. It calls `execute_certified_tool()` and the Trust Anchor handles the rest.

---

## Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      WINDOWS WORKSTATION                     │
│                                                              │
│  ┌──────────────┐     ┌──────────────────────────────────┐  │
│  │  Claude Code  │────>│  MCP Bridge (Secure Tools Server) │  │
│  │  (AI Agent)   │<────│  - Tool router                    │  │
│  │              │      │  - Signature validator             │  │
│  │  Skills.md   │      │  - Credential provider             │  │
│  │  guides the  │      │  - Audit logger                    │  │
│  │  agent's     │      └──────────┬───────────────────────┘  │
│  │  decisions   │                 │                           │
│  └──────────────┘                 │ HTTPS/SSH                 │
│                                   ▼                           │
│                    ┌──────────────────────────┐               │
│                    │  Trust Anchor (Port 8000) │               │
│                    │  - Tool registry           │              │
│                    │  - RSA public keys          │             │
│                    │  - Runbook definitions       │            │
│                    └──────────────────────────┘               │
└───────────────────────────────┬───────────────────────────────┘
                                │
                    ┌───────────┼───────────┐
                    │           │           │
                    ▼           ▼           ▼
            ┌──────────┐ ┌──────────┐ ┌──────────┐
            │  KVM Lab  │ │ FortiFlex│ │ FortiGate│
            │ (Rocky 9) │ │  Cloud   │ │ Devices  │
            │           │ │          │ │          │
            │ VM create │ │ License  │ │ SSH/API  │
            │ Bootstrap │ │ tokens   │ │ Config   │
            └──────────┘ └──────────┘ └──────────┘
```

---

## Key Components

### 1. MCP Bridge (Secure Tools Server)

The bridge runs as a local Python server and exposes tools to Claude Code via the Model Context Protocol. It provides:

- **`execute_certified_tool`** -- Execute a signed tool by canonical ID
- **`route_query`** -- Semantic search for tools using natural language
- **`list_certified_tools`** -- Browse available tools by domain/vendor
- **`execute_runbook`** -- Run multi-step workflows

Before executing any tool, the bridge:
1. Fetches the tool manifest from Trust Anchor
2. Verifies the RSA signature against the publisher's public key
3. Verifies the SHA-256 hash of the tool code matches the manifest
4. Only then executes the tool with the provided parameters

### 2. Trust Anchor

A central registry server that stores:
- **Certified tools** -- Signed manifests + code bundles
- **Publisher public keys** -- For signature verification
- **Runbook definitions** -- Multi-step workflows
- **Device registry** -- Known devices and their capabilities

### 3. Publisher Node

The tool authoring and signing authority:
- Validates tool manifests against the MCP schema
- Signs tools with RSA-4096 private key
- Publishes to Trust Anchor
- Generates Skills.md (AI guidance) for each tool

### 4. Credential Provider

Credentials are resolved at runtime, never embedded in tools:
- **Primary:** Windows DPAPI encrypted vault (`%LOCALAPPDATA%/UlyssesMCP/vault/`)
- **Fallback:** YAML files (`~/.config/mcp/fortigate_credentials.yaml`)
- Credentials stay on the execution endpoint -- they are never sent to Trust Anchor

---

## Security Model

### Chain of Trust

```
Developer → Publisher Node → Trust Anchor → MCP Bridge → Device
   │              │               │              │           │
   │  writes      │  RSA signs    │  stores      │ verifies  │ executes
   │  tool code   │  manifest     │  certified   │ signature │ commands
   │              │  + hash       │  bundle      │ + hash    │
```

### What the AI Agent CANNOT Do

- Execute unsigned or tampered tools (signature verification fails)
- Access credentials directly (resolved by credential provider, not exposed to agent)
- Run arbitrary shell commands on devices (only certified tool operations)
- Modify or delete production hub configuration (guardrail in Skills.md)
- Execute more than 50 tool calls per workflow (hard limit)

### What the AI Agent CAN Do

- Discover tools via semantic search (`route_query`)
- Execute certified tools with parameters
- Make adaptive decisions based on tool results
- Recover from errors using alternative strategies
- Escalate to human when automated recovery fails

---

## Workflow Engine: Block Stacking Pattern

The SD-WAN workflow uses a **block stacking** pattern where each phase (BLOCK_0 through BLOCK_4) is a self-contained unit with:

- **Inputs** -- Parameters from previous blocks or user
- **Tools** -- Certified MCP tools to execute
- **Success Criteria** -- Conditions that must be met before advancing
- **Error Handling** -- LLM-driven remediation strategies
- **Outputs** -- Results passed to the next block

```
BLOCK_0 (Blueprint Wizard)
    │ site_id, hostname, loopback, LAN subnet
    ▼
BLOCK_1 (Provision VM)
    │ management_ip, vm_name, vnc_port
    ▼
BLOCK_2 (License)
    │ serial_number, license_status
    ▼
BLOCK_3 (Configure)
    │ config_applied, sections_pushed
    ▼
BLOCK_4 (Verify)
    │ ipsec_status, bgp_state, health_check
    ▼
  [DONE] Site operational
```

The AI agent reads each block's YAML definition, executes the tools, evaluates results against success criteria, and decides whether to advance, retry, or escalate.

---

## Composable Config Block System

FortiOS configurations are decomposed into atomic `.block` files following NFR-025:

```yaml
---
# YAML Header (metadata)
block_id: 023
name: hub-ipsec-phase1-template
depends_on:
  - block_id: 022
    reason: "Interfaces must exist"
parameters:
  - name: PSK
    type: string
    sensitive: true
---
# CLI Body (FortiOS commands)
config vpn ipsec phase1-interface
    edit "SPOKE_VPN1"
        set type dynamic
        set psksecret {{PSK}}
    next
end
```

Benefits:
- **Composable** -- Mix and match blocks for different topologies
- **Testable** -- Each block can be validated independently
- **Versionable** -- Track changes per feature, not per device
- **Template-driven** -- Same blocks work for any site with different parameters
- **Dependency-aware** -- Blocks declare what they need, engine resolves order

---

## Data Flow: Site Deployment

```
1. User says: "Add SD-WAN site 12"

2. BLOCK_0 runs:
   - Checks manifest: site_id 12 is unique
   - Derives: loopback=172.16.0.12, LAN=10.12.1.0/24
   - Asks: WAN mode? PSK? VLANs?
   - Output: complete blueprint

3. BLOCK_1 runs:
   - Creates bootstrap ISO (config2 label, admin password, DHCP WAN)
   - Provisions VM on KVM (qcow2 clone, 2 vCPU, 4GB RAM)
   - Discovers DHCP IP via MAC-to-ARP correlation
   - Verifies SSH accessible

4. BLOCK_2 runs:
   - Lists FortiFlex entitlements (finds PENDING token)
   - SSH: "execute vm-license <token>"
   - Waits for reboot
   - Verifies: Serial=FGVMMLTM26000XXX, License=Valid

5. BLOCK_3 runs:
   - Renders ATOMIC_SPOKE_TEMPLATE.conf with site parameters
   - Pushes 13 config sections via SSH CLI (~8 seconds)
   - Validates: hostname set, IPsec tunnels created, SD-WAN enabled

6. BLOCK_4 runs:
   - Checks: IPsec selectors UP (1/1)
   - Checks: BGP state=Established, prefixes received
   - Checks: SD-WAN health=alive, packet-loss <5%
   - Updates manifest tracker

7. User sees:
   "Site 12 deployed successfully.
    IPsec: 2/2 tunnels UP
    BGP: Established (3 prefixes)
    Health: GREEN (12ms latency, 0% loss)"
```
