# NFR-026: Rocky Linux SD-WAN Rules Environment

**Version:** 1.0.0
**Feature ID:** NFR-026-ROCKY-LINUX-SDWAN-RULES-ENVIRONMENT
**Component:** Project-Ulysses-Open / MCP-2.0 / Core-MCP-Authority / solution_packs / fortigate-ops
**Priority:** High
**Estimated Size:** Medium
**Submitted by:** Daniel (FortiMind Architect)
**Date:** 2026-02-05
**Updated:** 2026-02-05
**Status:** DRAFT

---

## 1. Vision

Set up a Rocky Linux environment that mirrors the Windows development environment
for SD-WAN rule block development and testing. This enables parallel development
between Windows Claude (spoke deployment, rule authoring) and Rocky Linux Claude
(SaaS application, Trust Anchor, rule execution) while staying in lock-step.

The SaaS application runs on Trust Anchor (Rocky Linux) and needs the block
library folder structure to serve SD-WAN rules to customer FortiGate devices.

---

## 2. Context: What We're Building

### 2.1 Current State

- **Spoke deployment works**: Sites 7-11 deployed via `add-sdwan-site` workflow
- **Core blocks 1-13**: Base SD-WAN spoke config (loopback, tunnels, BGP, policies)
- **Hub deployment**: Separate Claude working on blocks 20-39
- **Next phase**: Post-deployment customer-specific configuration (SD-WAN rules)

### 2.2 SD-WAN Rules (Block 10000+)

SD-WAN rules are customer-specific steering policies applied AFTER the base
spoke deployment. They steer application traffic (O365, Zoom, Teams, etc.)
to preferred SD-WAN members based on SLA criteria.

```
RANGE         CATEGORY
-----------   ---------------------------
10000-10099   SD-WAN Rule Templates
10100-10199   SaaS Application Steering    (O365, Zoom, Teams, Salesforce)
10200-10299   ISDB Category Rules          (Cloud, Video, Social)
10300-10399   Geographic/Regional Rules
10400-10499   QoS/Traffic Class Rules      (Voice, Video, Bulk)
10500-10599   Failover/Backup Rules
10600-10699   Cost Optimization Rules
10700-10799   Time-based Rules
10800-10899   Custom Application Rules
10900-10999   Rule Bundles
```

---

## 3. Core Repository Files (Full Paths)

### 3.1 GitHub Repository

```
Repository: https://github.com/howardsinc3753/Project-Ulysses-Open.git
Branch: master
```

### 3.2 NFR Documents (Read These First)

```
projects/MCP-2.0/Core-MCP-Authority/docs/NFRs/NFR-024-SECBOT-PERSONA-FORTIGATE-OPS.md
  - SecBot persona for FortiGate operations (voice, guardrails)

projects/MCP-2.0/Core-MCP-Authority/docs/NFRs/NFR-025-COMPOSABLE-CONFIG-BLOCK-FRAMEWORK.md
  - Composable block framework architecture
  - Block numbering convention
  - Dependency resolver design
  - config-push v3.0.0 specification
```

### 3.3 Existing SD-WAN Workflow Files

```
projects/MCP-2.0/Core-MCP-Authority/solution_packs/fortigate-ops/workflows/add-sdwan-site/
  Skills.md                              - Main workflow guide with SecBot persona
  BASELINE_TEMPLATE.yaml                 - Naming constants, critical settings
  CONTRACT_SCHEMA.yaml                   - Parameter validation schema
  PROCESS_LOG_TEMPLATE.yaml              - Deployment logging format
  manifest.yaml                          - Workflow metadata

  blocks/
    BLOCK_0_BLUEPRINT_WIZARD.yaml        - Site parameter collection
    BLOCK_1_PROVISION.yaml               - VM provisioning (KVM)
    BLOCK_2_LICENSE.yaml                 - FortiFlex licensing
    BLOCK_3_CONFIGURE.yaml               - Config push (blocks 1-13)
    BLOCK_4_VERIFY.yaml                  - IPsec, BGP, health-check verification
```

### 3.4 Core Tools (Trust Anchor Certified)

```
projects/MCP-2.0/Core-MCP-Authority/tools/org.ulysses.noc.fortigate-config-push/
  manifest.yaml                          - Tool metadata, version 2.0.0
  org.ulysses.noc.fortigate-config-push.py
  Skills.md                              - Usage guide

projects/MCP-2.0/Core-MCP-Authority/tools/org.ulysses.noc.fortigate-sdwan-blueprint-planner/
  manifest.yaml                          - Tool metadata, version 1.0.7
  org.ulysses.noc.fortigate-sdwan-blueprint-planner.py
  Skills.md

projects/MCP-2.0/Core-MCP-Authority/tools/org.ulysses.noc.fortigate-sdwan-status/
  manifest.yaml                          - SD-WAN status checker
  org.ulysses.noc.fortigate-sdwan-status.py

projects/MCP-2.0/Core-MCP-Authority/tools/org.ulysses.sdwan.kvm-fortios-provision/
  manifest.yaml                          - KVM VM provisioning, version 1.0.11
  org.ulysses.sdwan.kvm-fortios-provision.py
  Skills.md
```

### 3.5 Configuration Files (Windows Paths - Adapt for Linux)

```
Windows:
  C:\ProgramData\Ulysses\config\fortigate_credentials.yaml
  C:\ProgramData\Ulysses\config\sdwan-manifest.yaml
  C:\ProgramData\Ulysses\config\blueprints\

Linux equivalent:
  /etc/ulysses/config/fortigate_credentials.yaml
  /etc/ulysses/config/sdwan-manifest.yaml
  /etc/ulysses/config/blueprints/
```

---

## 4. Rocky Linux Folder Structure

### 4.1 Block Library (Create This)

```
/etc/ulysses/config/blocks/
    fortigate/
        core/
            # Spoke core infrastructure (blocks 1-13)
            001-system-global.block
            002-system-settings.block
            003-system-interfaces.block
            004-dhcp-server.block
            005-ipsec-phase1.block
            006-ipsec-phase2.block
            007-tunnel-interface-settings.block
            008-static-routes.block
            009-firewall-addresses.block
            010-bgp.block
            011-sdwan-base.block
            012-sdwan-healthcheck-binding.block
            013-firewall-policies.block

            # Hub core infrastructure (blocks 20-39) - OTHER CLAUDE
            020-hub-system-global.block
            ...

        sdwan-rules/
            # SD-WAN steering rules (blocks 10000+) - THIS NFR
            10101-sdwan-rule-o365.block
            10102-sdwan-rule-teams.block
            10103-sdwan-rule-zoom.block
            10104-sdwan-rule-salesforce.block
            ...

        security/
            # Security profiles (blocks 200+) - FUTURE
            201-webfilter-profile.block
            202-ips-profile.block
            ...

        logging/
            # Logging blocks (blocks 500+) - FUTURE
            501-fortianalyzer-forwarding.block
            ...
```

### 4.2 SaaS Application Integration

```
/opt/ulysses/saas-app/
    config/
        block-catalog.yaml               # Index of available blocks
        customer-manifests/              # Per-customer configuration
    api/
        routes/
            sdwan-rules.py               # REST API for rule management
    services/
        block-resolver.py                # Dependency resolution
        config-pusher.py                 # Wrapper for config-push tool
```

---

## 5. Block File Format

Each `.block` file contains YAML header + FortiOS CLI body:

```yaml
---
block_id: 10101
name: sdwan-rule-o365
display_name: "SD-WAN Rule - Microsoft 365"
version: 1.0.0
category: sdwan-rules
vendor: fortinet
platform: fortigate
min_fortios: "7.4.0"

depends_on:
  - range: "1-12"
    reason: "SD-WAN base, members, and health-checks must exist"

provides:
  - "sdwan-rule-microsoft365"

parameters:
  - name: RULE_ID
    description: "SD-WAN service rule ID (1-4000, 0=auto)"
    type: integer
    default: 0
  - name: RULE_NAME
    description: "Rule display name"
    type: string
    default: "O365-Steering"
  - name: HEALTH_CHECK
    description: "SLA health-check name"
    type: string
    default: "HUB_Health"
  - name: PRIORITY_MEMBERS
    description: "Preferred SD-WAN member sequence numbers"
    type: string
    default: "1 2"

tags:
  - sdwan
  - microsoft365
  - saas
---

config system sdwan
    config service
        edit {{RULE_ID}}
            set name "{{RULE_NAME}}"
            set mode priority
            set internet-service enable
            set internet-service-name "Microsoft-Office365" "Microsoft-Office365.Published" "Microsoft-Office365.Published.Optimize" "Microsoft-Office365.Published.Allow"
            set health-check "{{HEALTH_CHECK}}"
            set link-cost-factor packet-loss
            set priority-members {{PRIORITY_MEMBERS}}
        next
    end
end
```

---

## 6. Skill Architecture

### 6.1 New Skill: `/add-sdwan-rule`

**Purpose:** Add SD-WAN steering rules to deployed spokes

**Location:**
```
projects/MCP-2.0/Core-MCP-Authority/solution_packs/fortigate-ops/workflows/add-sdwan-rule/
    Skills.md                            # Workflow guide
    manifest.yaml                        # Skill metadata
```

**Workflow:**
```
1. Validate target device has blocks 1-12 deployed (check sdwan-manifest.yaml)
2. Load block from library (e.g., 10101-sdwan-rule-o365.block)
3. Substitute parameters (RULE_NAME, HEALTH_CHECK, PRIORITY_MEMBERS)
4. Push via config-push or direct SSH
5. Verify rule exists: "get router sdwan service"
```

### 6.2 Skill-to-Block Mapping

One skill per category, not per block:

```
/add-sdwan-rule          → blocks 10000-10999 (all SD-WAN rules)
/add-security-profile    → blocks 200-299 (future)
/add-traffic-shaper      → blocks 300-399 (future)
/add-logging-config      → blocks 500-599 (future)
```

---

## 7. Test Environment

### 7.1 Available Test Devices

```yaml
# From fortigate_credentials.yaml
sdwan-spoke-07:
  host: 192.168.209.45
  model: FortiGate-VM
  firmware: v7.6.5
  serial: FGVMMLTM26000460

sdwan-spoke-08:
  host: 192.168.209.31
  model: FortiGate-VM
  firmware: v7.6.5
  serial: FGVMMLTM26000464

sdwan-spoke-09:
  host: 192.168.209.41
  model: FortiGate-VM
  firmware: v7.6.5
  serial: FGVMEVUNTZXDMG12
```

### 7.2 Test Plan

```
Phase 1: Single rule test
  1. Create block 10101-sdwan-rule-o365.block
  2. Push to spoke-07 (192.168.209.45)
  3. Verify: "diag sys sdwan service" shows O365 rule
  4. Test traffic steering (optional)

Phase 2: Multiple rules
  1. Create blocks 10102 (Teams), 10103 (Zoom)
  2. Push all three to spoke-08
  3. Verify rule ordering

Phase 3: SaaS integration
  1. REST API endpoint to list available blocks
  2. REST API endpoint to push block to device
  3. Customer portal selects rules → backend executes
```

---

## 8. Coordination Points

### 8.1 Windows Claude (This Session)

**Responsibilities:**
- Authoring block files (YAML header + CLI body)
- Testing push to FortiGate devices
- Skills.md documentation
- SecBot persona enforcement

**Artifacts produced:**
- `.block` files in repo
- Workflow Skills.md files
- Test results and GAP documentation

### 8.2 Rocky Linux Claude (Your Session)

**Responsibilities:**
- Setting up folder structure on Linux
- SaaS application REST API
- Block catalog indexing
- Dependency resolver implementation
- Integration with Trust Anchor

**Artifacts needed from Windows Claude:**
- Block files (this NFR tells you where they are)
- Credential file format
- config-push tool interface

### 8.3 Sync Protocol

```
1. Windows Claude creates block file → pushes to GitHub
2. Rocky Linux Claude pulls from GitHub
3. Rocky Linux Claude deploys to /etc/ulysses/config/blocks/
4. Rocky Linux Claude tests via SaaS API
5. Both report results in shared trace file
```

---

## 9. Acceptance Criteria

### Phase 1: Environment Setup
- [ ] Rocky Linux has folder structure: `/etc/ulysses/config/blocks/fortigate/`
- [ ] Credential file synced: `/etc/ulysses/config/fortigate_credentials.yaml`
- [ ] Can reach test devices (192.168.209.45, .31, .41) from Rocky Linux
- [ ] config-push tool executable on Rocky Linux

### Phase 2: Block Library
- [ ] Block 10101 (O365) created and tested
- [ ] Block pushed to spoke-07 successfully
- [ ] Rule visible in FortiGate CLI: `get router sdwan service`

### Phase 3: SaaS Integration
- [ ] REST API: GET /api/blocks → returns block catalog
- [ ] REST API: POST /api/blocks/apply → pushes block to device
- [ ] Customer portal can select and deploy rules

---

## 10. Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| NFR-024 SecBot Persona | Complete | Persona in Skills.md |
| NFR-025 Composable Blocks | Draft | Framework architecture |
| config-push/2.0.0 | Certified | Needs Linux build |
| Spoke deployment (sites 7-11) | Complete | Test targets available |
| Hub deployment (blocks 20-39) | In Progress | Other Claude |
| Trust Anchor on Rocky Linux | **Required** | SaaS app dependency |

---

## 11. Quick Start for Rocky Linux Claude

```bash
# 1. Clone the repo
git clone https://github.com/howardsinc3753/Project-Ulysses-Open.git
cd Project-Ulysses-Open

# 2. Read the core NFRs
cat projects/MCP-2.0/Core-MCP-Authority/docs/NFRs/NFR-024-SECBOT-PERSONA-FORTIGATE-OPS.md
cat projects/MCP-2.0/Core-MCP-Authority/docs/NFRs/NFR-025-COMPOSABLE-CONFIG-BLOCK-FRAMEWORK.md
cat projects/MCP-2.0/Core-MCP-Authority/docs/NFRs/NFR-026-ROCKY-LINUX-SDWAN-RULES-ENVIRONMENT.md

# 3. Read the current workflow
cat projects/MCP-2.0/Core-MCP-Authority/solution_packs/fortigate-ops/workflows/add-sdwan-site/Skills.md

# 4. Create block library structure
sudo mkdir -p /etc/ulysses/config/blocks/fortigate/{core,sdwan-rules,security,logging}

# 5. Copy credentials (get from Windows or sync)
sudo cp fortigate_credentials.yaml /etc/ulysses/config/

# 6. Test device reachability
ping 192.168.209.45  # spoke-07
ping 192.168.209.31  # spoke-08

# 7. Ready for block development
```

---

## 12. Notes

- Block numbering 10000+ chosen to avoid collision with core blocks (1-999)
- SD-WAN rules are spoke-side config; hub doesn't need these blocks
- Each rule references a health-check that pings the hub (172.16.255.253)
- FortiGate allows up to 4000 SD-WAN service rules per device
- Rules are processed top-to-bottom (first match wins)
