# NFR-025: Composable Configuration Block Framework

**Version:** 1.0.0
**Feature ID:** NFR-025-COMPOSABLE-CONFIG-BLOCK-FRAMEWORK
**Component:** Project-Ulysses-Open / MCP-2.0 / Core-MCP-Authority / solution_packs / fortigate-ops
**Priority:** High
**Estimated Size:** Large
**Submitted by:** Daniel (FortiMind Architect)
**Date:** 2026-01-27
**Updated:** 2026-01-27
**Status:** DRAFT

---

## 1. Vision

Transform the current fixed-section SD-WAN template into a composable block
framework where any FortiGate feature (SD-WAN rules, security profiles, traffic
shaping, logging, VPN overlays) is a self-contained configuration block with
declared dependencies. An AI agent selects which blocks a site needs, the
framework resolves the correct push ordering automatically, and config-push
deploys them atomically through Trust Anchor.

The goal: an agent says "I need core SD-WAN + O365 steering + web filter +
FortiAnalyzer logging" and the system composes and deploys the full
configuration in seconds, with zero ordering errors, regardless of which
combination of features is selected.

---

## 2. Problem Statement

### 2.1 What Exists Today

The current SD-WAN deployment pipeline uses a monolithic atomic template
(ATOMIC_SPOKE_TEMPLATE.conf) with 13 hardcoded sections. config-push/2.0.0
splits the template by `config ... end` blocks and pushes them in file order.

This works for the base SD-WAN spoke use case but has limitations:

| Limitation | Impact |
|------------|--------|
| Fixed section count | Adding a feature means editing the monolithic template |
| No dependency metadata | Section ordering is implicit (file order), not declared |
| No composability | Every site gets the same config; no per-site feature selection |
| No block reuse | SD-WAN app steering can't be shared across different base templates |
| No validation before push | Dependencies aren't checked until the device rejects a command |
| Single vendor assumption | Block format is FortiGate-specific with no abstraction layer |

### 2.2 What We Need

A framework where:

1. Each feature is a **self-contained block** with a manifest declaring its
   dependencies, vendor, FortiOS version compatibility, and parameters.
2. The **blueprint planner** composes blocks based on site requirements.
3. A **dependency resolver** validates the block graph and determines push order.
4. **config-push** (v3.0.0) reads block metadata and pushes in resolved order.
5. **New features** are added by dropping a block file into the blocks library —
   no changes to config-push, the template, or the workflow.

---

## 3. Architecture

### 3.1 Block Library Structure

```
C:\ProgramData\Ulysses\config\blocks\
    fortigate\
        core\
            # Spoke core infrastructure (1-13)
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

            # Hub core infrastructure (20-39) - NEW
            020-hub-system-global.block
            021-hub-system-settings.block
            022-hub-interfaces.block
            023-hub-ipsec-phase1-template.block
            024-hub-ipsec-phase2-template.block
            025-hub-bgp-base.block
            026-hub-bgp-neighbor-range.block
            027-hub-sdwan-zone.block
            028-hub-sdwan-healthcheck.block
            029-hub-firewall-policies.block

            # Dual-hub core (40-49) - NEW
            040-dual-hub-ha-settings.block
            041-dual-hub-bgp-failover.block
            042-dual-hub-route-redistribution.block

        sdwan-advanced\
            101-sdwan-app-steering-o365.block
            102-sdwan-app-steering-zoom.block
            103-sdwan-app-steering-teams.block
            104-sdwan-app-steering-salesforce.block
            105-sdwan-app-steering-webex.block
            110-sdwan-traffic-duplication.block
            111-sdwan-performance-sla.block
            120-sdwan-custom-rules.block

        security\
            201-webfilter-profile.block
            202-ips-profile.block
            203-antivirus-profile.block
            204-ssl-inspection.block
            205-application-control.block
            210-security-policy-group.block

        traffic-shaping\
            301-shaping-profile.block
            302-shaping-policy.block
            303-bandwidth-guarantee.block

        vpn\
            401-dual-hub-failover.block
            402-dialup-ipsec.block
            403-spoke-to-spoke-shortcuts.block
            404-ssl-vpn-portal.block

        logging\
            501-fortianalyzer-forwarding.block
            502-syslog-forwarding.block
            503-snmp-traps.block
            504-netflow-export.block

        ha\
            701-ha-active-passive.block
            702-ha-fgcp.block
            703-ha-session-sync.block

        cloud\
            801-aws-vpc-peering.block
            802-azure-vwan.block
            803-fortigate-cnf.block

        site-overrides\
            901-site-specific-addresses.block
            902-site-specific-policies.block
            903-site-specific-routes.block
```

### 3.2 Block File Format

Each .block file contains a YAML header (metadata) and the raw FortiOS
CLI configuration body. The header declares everything the framework
needs to resolve dependencies, validate compatibility, and compose configs.

```yaml
---
block_id: 101
name: sdwan-app-steering-o365
display_name: "SD-WAN Application Steering - Microsoft 365"
version: 1.0.0
category: sdwan-advanced
vendor: fortinet
platform: fortigate
min_fortios: "7.4.0"
max_fortios: null

# Dependency declaration
depends_on:
  - range: "1-11"
    reason: "SD-WAN members and health-checks must exist"
  - block: 13
    reason: "Firewall policy must allow the traffic"
    type: soft
    # soft = warning if missing, hard = fail if missing

# What this block provides (other blocks can depend on these)
provides:
  - "sdwan-service-microsoft365"
  - "sdwan-app-steering"

# Parameters that must be substituted at deploy time
parameters:
  - name: PRIORITY_MEMBER
    description: "Preferred SD-WAN member for O365 traffic"
    type: integer
    default: 1
  - name: SLA_TARGET
    description: "SLA health-check name to use for steering"
    type: string
    default: "HUB_Health"

# Conflicts (cannot coexist with these blocks)
conflicts_with: []

# Tags for semantic discovery
tags:
  - sdwan
  - application-steering
  - microsoft365
  - saas
---

# Block 101: SD-WAN Application Steering - Microsoft 365
# Requires: SD-WAN base (blocks 1-11), health-checks active

config system sdwan
    config service
        edit 10
            set name "Microsoft365"
            set internet-service enable
            set internet-service-name "Microsoft-Office365"
            set priority-members {{PRIORITY_MEMBER}}
            set sla "{{SLA_TARGET}}"
            set sla-compare-method number
        next
    end
end
```

### 3.3 Block Numbering Convention

```
RANGE        DOMAIN                          RESERVED FOR
---------    -----------------------------   ---------------------------
1-19         Core spoke infrastructure       Base spoke config (existing)
20-39        Core hub infrastructure         Single-hub SD-WAN deployment (NEW)
40-49        Dual-hub infrastructure         Active-active dual-hub (NEW)
50-99        Reserved                        Future core expansion
100-199      SD-WAN advanced features        App steering, rules, duplication, SLAs
200-299      Security profiles               WebFilter, IPS, AV, SSL-I, App Control
300-399      Traffic shaping / QoS           Shaping profiles, policies, guarantees
400-499      VPN extensions                  Dual-hub, dialup, mesh, SSL VPN
500-599      Logging / SIEM integration      FAZ, syslog, SNMP, NetFlow
600-699      Authentication                  RADIUS, LDAP, SAML, FortiToken
700-799      High Availability               HA active-passive, FGCP, session sync
800-899      Cloud / ZTNA                    AWS, Azure, ZTNA rules, CASB, SWG
900-999      Site-specific overrides         Custom addresses, policies, routes
```

### 3.4 Dependency Resolution

The framework resolves block ordering using a topological sort on the
dependency graph. This ensures every block's dependencies are pushed
before the block itself.

```
INPUT:  Agent requests blocks [1-13, 101, 201, 501]

STEP 1: Load block manifests
        Block 101 depends_on: [1-11, 13(soft)]
        Block 201 depends_on: [1-2]
        Block 501 depends_on: [1-2]
        Blocks 1-13: sequential chain (existing core)

STEP 2: Build dependency graph
        1 -> 2 -> 3 -> ... -> 13
        1-11 -> 101
        1-2 -> 201
        1-2 -> 501
        13 -> 101 (soft)

STEP 3: Topological sort
        Result: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 201, 501, 13, 101]

STEP 4: Validate
        - All hard dependencies satisfied: YES
        - Soft dependency (101 -> 13): 13 is before 101: YES
        - No circular dependencies: YES
        - FortiOS version compatible: YES

STEP 5: Push in resolved order
        config-push sends blocks in the order from Step 3.
```

**Circular Dependency Handling:**

If the resolver detects a cycle, it reports the cycle and suggests a
deferred-binding split (the same technique used for GAP-49). This is how
Section 11b (now Section 12) was created — the framework would automate
that pattern.

### 3.5 Component Changes

```
COMPONENT              CURRENT (v2)              TARGET (v3)
-------------------    -----------------------   ----------------------------
ATOMIC_SPOKE_TEMPLATE  Monolithic 13-section     Replaced by block composition
                       file                       from blocks library

config-push            v2.0.0                    v3.0.0
                       Splits on config/end       Reads block manifests
                       Pushes in file order       Pushes in resolved order
                       No dependency awareness    Full dependency resolver
                       Single config file input   Block list or composed file

blueprint-planner      v1.0.8                    v2.0.0
                       Generates monolithic       Selects blocks from library
                       config from template       Composes based on site needs
                       Fixed feature set          Feature selection per site

Trust Anchor           No change                 No change (blocks are signed
                                                  like any other artifact)

Skills.md (workflow)   References 13 sections    References block library
                       Fixed deployment steps     Dynamic block composition
```

---

## 4. Detailed Design

### 4.1 Block Manifest Schema

```yaml
# REQUIRED fields
block_id: integer           # Unique numeric ID within the numbering scheme
name: string                # Machine-readable name (lowercase, hyphens)
display_name: string        # Human-readable name
version: string             # Semantic version (e.g., "1.0.0")
category: string            # One of: core, sdwan-advanced, security,
                            # traffic-shaping, vpn, logging, auth, ha, cloud,
                            # site-overrides
vendor: string              # "fortinet" (extensible to other vendors)
platform: string            # "fortigate" (extensible)

# DEPENDENCY fields
depends_on: list            # List of dependency declarations
  - range: "1-11"           # Block ID range (shorthand for 1,2,3,...,11)
    reason: string          # Why this dependency exists
    type: "hard" | "soft"   # hard = fail if missing, soft = warn if missing
                            # Default: hard
  - block: integer          # Single block ID dependency

provides: list[string]      # Capabilities this block provides
                            # Other blocks can depend on capabilities
                            # instead of block IDs for loose coupling

conflicts_with: list[int]   # Block IDs that cannot coexist with this block

# COMPATIBILITY fields
min_fortios: string | null  # Minimum FortiOS version (e.g., "7.4.0")
max_fortios: string | null  # Maximum FortiOS version (null = no limit)

# PARAMETER fields
parameters: list            # Values substituted at deploy time
  - name: string            # Parameter name (UPPERCASE, used in {{NAME}})
    description: string     # What this parameter controls
    type: string            # string, integer, boolean, ip_address, cidr
    default: any | null     # Default value (null = required, no default)
    required: boolean       # Must be provided at deploy time

# METADATA fields
tags: list[string]          # Semantic search tags
author: string              # Who created this block
created: string             # ISO 8601 date
notes: string | null        # Freeform notes
```

### 4.2 Dependency Resolver Algorithm

```
FUNCTION resolve_block_order(requested_blocks: list[int]) -> list[int]:

    1. Load manifests for all requested blocks
    2. For each block, expand range dependencies (e.g., "1-11" -> [1,2,...,11])
    3. Check that all hard dependencies are in the requested set
       - If missing: ERROR "Block 101 requires blocks [1-11] but block 7 is
         not in the request"
    4. Check soft dependencies and emit warnings if missing
    5. Build adjacency list: for each block, add edges from its dependencies
    6. Run Kahn's algorithm (topological sort):
       a. Compute in-degree for each block
       b. Initialize queue with all blocks having in-degree 0
       c. While queue is not empty:
          - Dequeue block with lowest block_id (stable ordering)
          - Add to result list
          - For each dependent block, decrement in-degree
          - If in-degree reaches 0, enqueue
       d. If result list length != requested block count:
          - Circular dependency detected
          - Report the cycle
          - Suggest deferred-binding split
    7. Return ordered list

FUNCTION validate_composition(ordered_blocks: list[int], target_device: dict):

    1. Check FortiOS version compatibility for each block
    2. Check conflicts_with for each pair of blocks
    3. Check that all required parameters have values
    4. Return validation result (pass/fail with details)
```

### 4.3 config-push v3.0.0 Changes

Current v2.0.0 `split_config_sections()` function (lines 87-130):
- Tracks nesting depth starting at 0
- Splits on `config <name>` at depth 0
- Returns sections in file order

v3.0.0 adds:
- Block manifest parser (read YAML header from .block files)
- Dependency resolver (Section 4.2 above)
- Composed-config mode: accepts a list of block IDs + parameters,
  loads blocks from library, resolves order, substitutes parameters,
  pushes in resolved order
- Backward compatibility: still accepts a plain config file (v2 mode)
  when no block metadata is present

New execution modes:

```
# v2 mode (backward compatible) - plain config file
config-push --config_path /path/to/atomic-config.conf --target_ip 192.168.209.42

# v3 mode - block composition
config-push --blocks 1-13,101,201,501 --site_id 10 --target_ip 192.168.209.42

# v3 mode - block composition with parameter overrides
config-push --blocks 1-13,101 --site_id 10 --target_ip 192.168.209.42 \
    --param PRIORITY_MEMBER=2 --param SLA_TARGET="BACKUP_Health"
```

### 4.4 Blueprint Planner v2.0.0 Changes

Current v1.0.8:
- Takes site parameters and generates a monolithic config file
- Uses ATOMIC_SPOKE_TEMPLATE.conf as base
- Substitutes variables (SITE_ID, TUNNEL_IPS, etc.)

v2.0.0 adds:
- Feature selection input: agent specifies which features the site needs
- Block catalog query: looks up which blocks implement requested features
- Block composition: assembles selected blocks with site parameters
- Dependency validation: confirms the composition is valid before output
- Output: either a composed config file (for v2 push) or a block manifest
  (for v3 push)

Example agent interaction:

```
Agent: "Deploy site 10 with SD-WAN base, O365 app steering,
        web filter, and FortiAnalyzer logging."

Blueprint Planner v2.0.0:
  1. Core SD-WAN:     blocks 1-13  (always included)
  2. O365 steering:   block 101
  3. Web filter:      blocks 201, 210
  4. FortiAnalyzer:   block 501
  5. Resolved order:  [1-12, 201, 210, 501, 13, 101]
  6. Parameters:      SITE_ID=10, TUNNEL_IPS=..., PRIORITY_MEMBER=1, ...
  7. Output:          composed config file with all blocks in order
```

### 4.5 Block Signing

Blocks are signed through Trust Anchor just like tools:

1. Developer submits .block file to Publisher Node
2. Publisher computes SHA-256 hash of the block content (header + body)
3. Publisher signs the hash with RSA private key
4. Signed block stored in Trust Anchor registry
5. config-push v3 verifies block signatures before push

This extends the chain of trust: AI Agent -> Trust Anchor -> Signed Tool
(config-push) -> Signed Blocks -> FortiGate Device.

Every artifact in the pipeline is cryptographically verified.

---

## 5. Migration Path

### Phase 1: Extract blocks from existing template (no code changes)

- Take ATOMIC_SPOKE_TEMPLATE.conf sections 1-13
- Create 13 .block files with YAML headers in the blocks library
- Add dependency declarations based on GAP documentation (GAPs 1-49)
- config-push v2.0.0 continues to work unchanged (reads plain config files)
- Blueprint planner v1.0.8 continues to work unchanged

Outcome: Block library exists, current pipeline unaffected.

### Phase 2: Build dependency resolver

- Implement topological sort resolver as a standalone module
- Add block manifest parser (YAML header extraction)
- Write validation logic (version compat, conflicts, required params)
- Unit test with blocks 1-13 to confirm it produces the correct order
- Unit test with blocks 1-13 + 101 + 201 to confirm extended ordering

Outcome: Resolver is tested and ready for integration.

### Phase 3: config-push v3.0.0

- Integrate dependency resolver into config-push
- Add --blocks mode alongside existing --config_path mode
- Add --param flag for parameter overrides
- Backward compatible: plain config files still work (v2 mode)
- Sign and certify config-push v3.0.0 in Trust Anchor

Outcome: config-push handles both plain files and block composition.

### Phase 4: Build feature blocks

- Create blocks for SD-WAN advanced features (100-series)
- Create blocks for security profiles (200-series)
- Create blocks for logging (500-series)
- Each block tested individually and in combination
- All blocks signed in Trust Anchor

Outcome: Block library covers common FortiGate features.

### Phase 5: Blueprint planner v2.0.0

- Add feature selection input to blueprint planner
- Add block catalog query and composition logic
- Planner outputs composed configs using blocks instead of monolithic template
- Sign and certify blueprint-planner v2.0.0 in Trust Anchor

Outcome: Agents can request feature-specific deployments.

### Phase 6: Multi-vendor extensibility (future)

- Abstract block format to support other vendors (Cisco, Palo Alto)
- Vendor-specific block libraries under blocks/{vendor}/
- Dependency resolver is vendor-agnostic (operates on block metadata)

Outcome: Framework extends beyond FortiGate.

---

## 6. Example: Full Deployment with Blocks

### Scenario: Site 15 needs SD-WAN + O365 steering + Web Filter + FAZ logging

```
AGENT REQUEST:
  site_id: 15
  target_ip: 192.168.209.55
  features:
    - core-sdwan-spoke
    - sdwan-app-steering-o365
    - webfilter-profile
    - security-policy-group
    - fortianalyzer-forwarding
  parameters:
    SITE_ID: 15
    WAN_IP: 192.168.209.55
    LOOPBACK_IP: 10.10.10.15
    HUB1_VPN1_REMOTE: 198.51.100.1
    HUB1_VPN2_REMOTE: 203.0.113.1
    BGP_ASN_SPOKE: 65015
    PRIORITY_MEMBER: 1
    FAZ_IP: 192.168.209.200

BLUEPRINT PLANNER v2.0.0:
  1. Resolve features to blocks:
     core-sdwan-spoke         -> blocks 1-13
     sdwan-app-steering-o365  -> block 101
     webfilter-profile        -> block 201
     security-policy-group    -> block 210
     fortianalyzer-forwarding -> block 501
  2. Dependency resolution:
     Block 101: depends [1-11, 13(soft)]
     Block 201: depends [1-2]
     Block 210: depends [1-2, 201]
     Block 501: depends [1-2]
  3. Topological sort:
     [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 201, 210, 501, 13, 101]
  4. Substitute parameters in all blocks
  5. Validate composition (version compat, no conflicts)
  6. Output composed config (17 blocks)

CONFIG-PUSH v3.0.0:
  Dry-run: 17/17 blocks parsed, all signatures verified
  Live push: 17/17 blocks success, 0 failures, ~12 seconds
  Verification: IPsec UP, BGP Established, Health ALIVE, Web Filter active,
                FAZ logging confirmed
```

---

## 7. Acceptance Criteria

### Phase 1: Core Framework
- [ ] Block file format defined and documented (.block with YAML header + CLI body)
- [ ] Block numbering convention established (1-19 spoke, 20-39 hub, 40-49 dual-hub, etc.)
- [ ] Existing 13 sections extracted into individual .block files (1-13)
- [ ] Dependency resolver implemented (topological sort with cycle detection)
- [ ] Resolver correctly orders blocks 1-13 (matches current hardcoded order)
- [ ] Resolver correctly inserts feature blocks (101, 201, etc.) at correct positions
- [ ] Circular dependency detection works and suggests deferred-binding splits
- [ ] config-push v3.0.0 supports both plain file (v2) and block composition (v3) modes
- [ ] Parameter substitution works for all block parameters
- [ ] Block signing through Trust Anchor verified
- [ ] Blueprint planner v2.0.0 supports feature selection and block composition
- [ ] Backward compatibility confirmed: v2 config files still push correctly
- [ ] Performance: block composition adds less than 1 second to total push time

### Phase 2: Feature Blocks
- [ ] At least 5 SD-WAN advanced blocks created (101-105)
- [ ] At least 3 security profile blocks created (201-203)
- [ ] At least 2 logging blocks created (501-502)
- [ ] Full deployment tested with core + 3 feature blocks on a FortiGate VM

### Phase 3: Hub Deployment (NEW)
- [ ] Hub core blocks created (20-29)
- [ ] Dual-hub blocks created (40-42)
- [ ] `/add-sdwan-hub` skill implemented
- [ ] Single-hub deployment tested and verified
- [ ] Dual-hub deployment tested with iBGP peering verified
- [ ] Hub can terminate at least 3 spoke connections
- [ ] Spoke can connect to dual-hub (both tunnels UP)

### Phase 4: Customer Organization (NEW)
- [ ] Directory structure created (deployments/lab, deployments/partners)
- [ ] Partner manifest schema defined and documented
- [ ] Customer manifest schema defined and documented
- [ ] `create-partner` management tool implemented
- [ ] `create-customer` management tool implemented
- [ ] Blueprint wizard updated to accept partner/customer parameters
- [ ] config-push outputs to correct partner/customer paths
- [ ] Lab deployments (site 7-11) migrated to deployments/lab/
- [ ] At least 1 test partner + 2 test customers created
- [ ] Deployment reporting works (list sites by partner/customer)

---

## 8. Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| config-push/2.0.0 | Certified | Becomes baseline for v3.0.0 |
| blueprint-planner/1.0.8 | Certified | Becomes baseline for v2.0.0 |
| Trust Anchor tool signing | Complete | Extends to block signing |
| GAP-1 through GAP-50 | Documented | Dependency rules derived from gaps |
| NFR-024 SecBot Persona | Draft | Persona applies to block-based deployment |
| ATOMIC_SPOKE_TEMPLATE.conf | Stable | Source for extracting spoke blocks (1-13) |
| Hub template config | **Missing** | Need to create hub template for blocks 20-29 |
| Dual-hub template config | **Missing** | Need to create dual-hub template for blocks 40-42 |
| Manifest schema validator | **Missing** | Validates partner/customer manifest files |

---

## 9. Patent Implications

This framework generalizes the invention described in the patent disclosure
from "13 ordered sections for SD-WAN" to "composable, dependency-ordered
configuration blocks for any network feature." This broadens the patent
claims significantly:

- The section-block atomic push method applies to ANY block, not just SD-WAN
- The dependency resolver is a general algorithm (topological sort with
  deferred-binding for cycles), not specific to any configuration type
- The block signing extends the cryptographic chain of trust to configuration
  artifacts, not just tools
- The gap-feedback mechanism feeds into block dependency declarations,
  creating a self-improving composition system

The patent attorney should be made aware of this NFR so claims can be
drafted to cover the general method, with the 13-section SD-WAN deployment
as the first embodiment.

---

## 10. Customer/Partner Organization Structure

### 10.1 Problem: Deployments are Unorganized

Currently, all deployments (VMs, configs, blueprints, traces) are scattered across
folders with no customer or partner hierarchy:

```
C:\ProgramData\Ulysses\config\blueprints\
    site-07\
    site-08\
    site-09\
    site-10\
    site-11\
    ATOMIC_SPOKE_TEMPLATE.conf

\\192.168.209.105\LocalShare\Patent-sdwan\
    trace-1769556663261.yaml
    GAP-50-A2A-DISCOVERY.md
```

Issues:
- No way to distinguish between lab sites, POC customers, and production partners
- No isolation between customer deployments
- No partner-level reporting (e.g., "how many sites deployed for Partner X?")
- No customer-specific config overrides or templates
- Difficult to clean up test deployments vs production

### 10.2 Proposed Structure

```
C:\ProgramData\Ulysses\deployments\
    lab\                                    # Internal lab/testing
        sdwan-hub\
            config\
                hub-config.conf
            logs\
                deployment-2026-01-25.yaml
        sdwan-spoke-07\
        sdwan-spoke-08\
        ...

    partners\
        Partner_MSP_Alpha\                  # Partner container
            customers\
                Customer_RetailCorp\        # Customer container
                    sites\
                        site-001-hq\
                            config\
                                atomic-config-spoke-001.conf
                                blocks.yaml
                            logs\
                                deployment-2026-01-31.yaml
                                verification-2026-01-31.yaml
                        site-002-branch\
                        site-003-branch\
                    hubs\
                        hub-primary\
                        hub-secondary\
                    manifest.yaml           # Customer metadata

                Customer_HealthcareInc\
                    sites\
                        site-001-datacenter\
                        site-002-clinic\
                    manifest.yaml

            manifest.yaml                   # Partner metadata
            templates\                      # Partner-specific templates
                retail-spoke-template.block
                healthcare-spoke-template.block

        Partner_Cloud_Provider\
            customers\
                Customer_SaaS_Startup\
                    ...

    templates\                              # Global templates
        blocks\                             # Shared block library (from Section 3.1)
        base-configs\
```

### 10.3 Manifest Files

**Partner Manifest** (`partners/Partner_MSP_Alpha/manifest.yaml`):
```yaml
partner_id: "partner-msp-alpha"
partner_name: "MSP Alpha Corporation"
contact:
  name: "John Smith"
  email: "john@mspalpha.com"
  phone: "+1-555-0100"
created: "2026-01-20"
billing:
  model: "per-site-monthly"
  rate: 150.00
  currency: "USD"
customers: 12
total_sites: 47
total_hubs: 4
```

**Customer Manifest** (`partners/Partner_MSP_Alpha/customers/Customer_RetailCorp/manifest.yaml`):
```yaml
customer_id: "customer-retailcorp"
customer_name: "RetailCorp Inc"
partner_id: "partner-msp-alpha"
contact:
  name: "Jane Doe"
  email: "jane@retailcorp.com"
created: "2026-01-25"
subscription:
  tier: "premium"
  features:
    - core-sdwan
    - webfilter
    - ips
    - fortianalyzer
sites: 3
hubs: 1
hub_bgp_asn: 65000
spoke_bgp_asn_range: "65001-65254"
default_psk: "<encrypted>"
default_features:
  - core-sdwan-spoke
  - webfilter-profile
  - ips-profile
```

### 10.4 Workflow Changes

**Current Workflow:**
```
Agent: "Deploy site 12"
→ Creates config at C:\ProgramData\Ulysses\config\blueprints\site-12\
```

**New Workflow:**
```
Agent: "Deploy site 3 for RetailCorp under Partner MSP Alpha"

1. Validate: Partner_MSP_Alpha exists
2. Validate: Customer_RetailCorp exists under partner
3. Read customer manifest for default features and BGP ASN range
4. Create: deployments/partners/Partner_MSP_Alpha/customers/Customer_RetailCorp/sites/site-003-branch/
5. Generate config with customer defaults + site-specific params
6. Log deployment to site-specific logs/ folder
7. Update customer manifest: sites: 4
```

**Site Lookup:**
```
Agent: "What's the config for RetailCorp site 2?"
→ Read: deployments/partners/Partner_MSP_Alpha/customers/Customer_RetailCorp/sites/site-002-branch/config/
```

**Partner Reporting:**
```
Agent: "How many sites deployed for Partner MSP Alpha?"
→ Parse: deployments/partners/Partner_MSP_Alpha/manifest.yaml
→ Result: "47 sites across 12 customers"
```

### 10.5 Migration from Current State

```
STEP 1: Create structure
    - Create deployments/lab/ and deployments/partners/ directories
    - Move existing site-07 through site-11 to deployments/lab/

STEP 2: Define lab as default partner
    - Lab deployments don't require partner/customer
    - Agent can omit partner/customer → defaults to lab/

STEP 3: Add partner/customer to blueprint wizard
    - BLOCK_0 asks: "Partner?" (optional, default=lab)
    - BLOCK_0 asks: "Customer?" (optional if partner=lab)
    - Wizard reads customer manifest for defaults

STEP 4: Update config-push to use new paths
    - Blueprint output path: deployments/{partner}/customers/{customer}/sites/{site_id}/config/
    - Trace output path: deployments/{partner}/customers/{customer}/sites/{site_id}/logs/

STEP 5: Create manifest management tools
    - create-partner: Initialize new partner container
    - create-customer: Initialize new customer under partner
    - list-deployments: Query by partner/customer/site
```

### 10.6 Benefits

| Benefit | Impact |
|---------|--------|
| **Customer Isolation** | Each customer's configs are separate, no cross-contamination |
| **Partner Reporting** | "Show all sites for Partner X" is a simple directory listing |
| **Template Inheritance** | Customer → Partner → Global template hierarchy |
| **Billing Integration** | Partner manifest has billing rates, easy to generate invoices |
| **Cleanup** | Delete test customer without affecting production |
| **Auditing** | All deployments for a customer in one place |
| **Multi-tenancy** | Partners can't see each other's customers |

---

## 11. Hub Deployment Workflows (NEW)

### 11.1 Single-Hub SD-WAN Deployment

**Use Case:** Deploy a single SD-WAN hub that terminates spoke VPN connections

**Blocks Required:** 20-29 (hub core infrastructure)

**Key Differences from Spoke:**
- No IPsec client config (hub is server, uses phase1-interface templates)
- BGP uses neighbor ranges instead of specific neighbors
- SD-WAN health-check monitors spokes, not hub-to-hub
- Firewall policies allow spoke-to-spoke traffic via hub

**Example Hub Config (Block 23: hub-ipsec-phase1-template.block):**
```
config vpn ipsec phase1-interface
    edit "SPOKE-TEMPLATE"
        set type dynamic
        set interface "wan1"
        set ike-version 2
        set local-gw 0.0.0.0
        set authmethod psk
        set psksecret {{PSK}}
        set proposal aes256-sha256
        set dpd on-idle
        set dhgrp 14
        set nattraversal enable
        set add-route disable
        set auto-discovery-sender enable
        set network-overlay enable
        set network-id {{NETWORK_ID}}
    next
end
```

**Hub Deployment Workflow:**
- Same BLOCK_0, BLOCK_1, BLOCK_2 (blueprint, provision, license)
- BLOCK_3 uses hub blocks (20-29) instead of spoke blocks (1-13)
- BLOCK_4 verifies hub health + at least 1 spoke connected

### 11.2 Dual-Hub SD-WAN Deployment

**Use Case:** Active-active dual-hub for redundancy and load balancing

**Blocks Required:** 20-29 (hub base) + 40-49 (dual-hub extensions)

**Architecture:**
```
              ┌─────────────┐           ┌─────────────┐
              │   HUB-1     │           │   HUB-2     │
              │ AS 65000    │───BGP─────│ AS 65000    │
              │ Priority 1  │  iBGP     │ Priority 2  │
              └──────┬──────┘           └──────┬──────┘
                     │                         │
                     │    ┌─────────────┐     │
                     └────┤   SPOKE-1   │─────┘
                          │  AS 65001   │
                          │ ADVPN: Both │
                          └─────────────┘
```

**Key Differences from Single-Hub:**
- Hub-to-hub iBGP peering (block 041)
- Route redistribution between hubs (block 042)
- Spokes connect to both hubs with priority (HUB-1 primary, HUB-2 backup)
- SD-WAN health-check monitors both hubs

**Example Dual-Hub Block (Block 041: dual-hub-bgp-failover.block):**
```yaml
---
block_id: 041
name: dual-hub-bgp-failover
display_name: "Dual-Hub iBGP Peering for Failover"
version: 1.0.0
category: core
vendor: fortinet
platform: fortigate
min_fortios: "7.4.0"

depends_on:
  - range: "20-26"
    reason: "Hub BGP base must exist before iBGP peering"

provides:
  - "dual-hub-ibgp"
  - "hub-to-hub-failover"

parameters:
  - name: PEER_HUB_LOOPBACK
    description: "Other hub's loopback IP for iBGP peering"
    type: ip_address
    required: true
  - name: PEER_HUB_ASN
    description: "Other hub's BGP ASN (same as local for iBGP)"
    type: integer
    default: 65000
---

config router bgp
    config neighbor
        edit "{{PEER_HUB_LOOPBACK}}"
            set remote-as {{PEER_HUB_ASN}}
            set description "iBGP to peer hub"
            set update-source "Hub-Lo"
            set route-reflector-client disable
        next
    end
end
```

### 11.3 Workflow: `/add-sdwan-hub`

**New Skill:** `/add-sdwan-hub` (similar to `/add-sdwan-site`)

**BLOCK_0: Hub Blueprint Wizard**
- Hub type: [Single-hub] [Dual-hub primary] [Dual-hub secondary]
- Hub ID: (e.g., 1 for primary, 2 for secondary)
- WAN interfaces: [wan1] [wan1, wan2 (dual-wan)]
- Expected spokes: (number for capacity planning)
- Network ID: (ADVPN overlay identifier)

**BLOCK_1: Hub Provision**
- Same VM provisioning as spoke (if KVM)
- Or physical device registration

**BLOCK_2: Hub License**
- Same FortiFlex flow

**BLOCK_3: Hub Configure**
- If single-hub: blocks 20-29
- If dual-hub: blocks 20-29, 40-42
- Atomic push via config-push/3.0.0

**BLOCK_4: Hub Verify**
- Hub interfaces UP
- BGP listening for spoke connections
- (If dual-hub) iBGP peering established with peer hub

---

## 12. Notes

- Block numbering is a convention, not a hard constraint. The resolver
  operates on declared dependencies, not numeric order. Numbers exist
  for human readability and namespace organization.
- The framework is designed to be vendor-extensible (Section 5, Phase 6)
  but the initial implementation targets FortiGate only.
- Blocks can depend on capabilities (provides field) instead of block IDs
  for loose coupling. Example: block 210 (security policy group) can
  depend on "webfilter-profile" capability instead of block 201 specifically.
  This allows substituting different web filter implementations.
- The ATOMIC_SPOKE_TEMPLATE.conf remains available as a fallback for
  simple deployments that don't need feature composition.
