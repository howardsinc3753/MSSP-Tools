"""
Shared Constants (NFR-012-B)
============================

Single source of truth for values used by multiple components.
NEVER duplicate these values - always import from here.

Used by:
- src/master_node/routers/keys.py
- src/publisher_node/config.py
- src/publisher_node/registry.py
- src/subscriber_node/secure_executor.py

Documentation:
- NFR: docs/NFRs/NFR-012-B-AI-CODER-GOVERNANCE.md
- Schema: docs/specs/REDIS-SCHEMA.md

Author: Rocky Linux Trust Anchor (AI)
Version: 1.0.0
Created: 2025-12-20
"""

from pathlib import Path


# =============================================================================
# KEY FILE NAMING
# =============================================================================
PUBLIC_KEY_FILENAME = "public.pem"
PRIVATE_KEY_FILENAME = "private.pem"
KEY_VERSION_FILENAME = "key_version.txt"
KEY_METADATA_FILENAME = "key_metadata.json"


# =============================================================================
# CRYPTOGRAPHY
# =============================================================================
SIGNING_ALGORITHM = "RSA-2048-PKCS1v15-SHA256"
KEY_SIZE_BITS = 2048
HASH_ALGORITHM = "SHA-256"


# =============================================================================
# REDIS KEY PATTERNS
# =============================================================================
# Tool storage (hash)
REDIS_TOOL_PREFIX = "tool:"
REDIS_TOOL_MANIFEST_FIELD = "manifest_json"  # Field name in hash

# Tool indexes (sets)
REDIS_TOOLS_ALL_SET = "tools:all"
REDIS_TOOLS_STATUS_PREFIX = "tools:status:"  # e.g., tools:status:certified
REDIS_TOOLS_DOMAIN_PREFIX = "tools:domain:"  # e.g., tools:domain:noc

# Signature storage (strings)
REDIS_SIGNATURE_SUFFIX = ":signature"
REDIS_CODE_HASH_SUFFIX = ":code_hash"
REDIS_SIGNING_PAYLOAD_SUFFIX = ":signing_payload"
REDIS_SIGNED_AT_SUFFIX = ":signed_at"
REDIS_SIGNED_BY_KEY_SUFFIX = ":signed_by_key"

# Code storage (strings)
REDIS_CODE_PYTHON_SUFFIX = ":code:python"
REDIS_SKILLS_SUFFIX = ":skills"
REDIS_MANIFEST_SUFFIX = ":manifest"

# Status storage (strings)
REDIS_STATUS_SUFFIX = ":status"
REDIS_SUBMITTED_AT_SUFFIX = ":submitted_at"
REDIS_CERTIFIED_AT_SUFFIX = ":certified_at"
REDIS_CERTIFIED_BY_SUFFIX = ":certified_by"


# =============================================================================
# TOOL STATUS VALUES
# =============================================================================
STATUS_PENDING = "pending"
STATUS_CERTIFIED = "certified"
STATUS_REJECTED = "rejected"
STATUS_DEPRECATED = "deprecated"


# =============================================================================
# RUNBOOK REDIS KEY PATTERNS (NFR-014)
# =============================================================================
REDIS_RUNBOOK_PREFIX = "runbook:"
REDIS_RUNBOOKS_ALL_SET = "runbooks:all"
REDIS_RUNBOOKS_STATUS_PREFIX = "runbooks:status:"
REDIS_RUNBOOKS_DOMAIN_PREFIX = "runbooks:domain:"
REDIS_RUNBOOK_STEPS_SUFFIX = ":steps"
REDIS_RUNBOOK_MANIFEST_HASH_SUFFIX = ":manifest_hash"


# =============================================================================
# SOLUTION PACK REDIS KEY PATTERNS (NFR-014)
# =============================================================================
REDIS_SOLUTION_PACK_PREFIX = "solution_pack:"
REDIS_SOLUTION_PACKS_ALL_SET = "solution_packs:all"
REDIS_SOLUTION_PACKS_STATUS_PREFIX = "solution_packs:status:"
REDIS_SOLUTION_PACKS_CATEGORY_PREFIX = "solution_packs:category:"


# =============================================================================
# INSTALLATION TRACKING REDIS KEY PATTERNS (NFR-014)
# =============================================================================
REDIS_INSTALLATION_PREFIX = "installation:"


# =============================================================================
# RUNBOOK EXECUTION TRACKING REDIS KEY PATTERNS (NFR-014)
# =============================================================================
REDIS_EXECUTION_PREFIX = "execution:"
REDIS_EXECUTIONS_ALL_SET = "executions:all"
REDIS_EXECUTIONS_RUNBOOK_PREFIX = "executions:runbook:"  # e.g., executions:runbook:{id}
REDIS_EXECUTIONS_STATUS_PREFIX = "executions:status:"  # e.g., executions:status:completed


# =============================================================================
# API ENDPOINTS
# =============================================================================
TRUST_ANCHOR_PORT = 8000
RAG_SERVER_PORT = 8001
A2A_SERVER_PORT = 8002  # NFR-013
CHROMADB_TOOL_ROUTER_PORT = 8003  # NFR-020: Semantic Tool Router ChromaDB
SESSION_MANAGER_PORT = 8005  # NFR-021: AI Agent Hive Session Manager
REDIS_PORT = 6379

# =============================================================================
# CHROMADB CONFIGURATION (NFR-020)
# =============================================================================
CHROMADB_HOST = "localhost"  # Can be overridden by environment
CHROMADB_API_VERSION = "v2"  # ChromaDB REST API version
TOOL_ROUTER_COLLECTION = "tool-router"
RUNBOOK_ROUTER_COLLECTION = "runbook-router"

# =============================================================================
# ADMIN/DEV GUI TOOLS
# =============================================================================
REDIS_COMMANDER_PORT = 8081  # Redis GUI viewer
DATASETTE_PORT = 8082  # TRTP training data viewer


# =============================================================================
# DNS INFRASTRUCTURE (NFR-015)
# =============================================================================
COREDNS_PORT = 53  # CoreDNS server (standard DNS port, bound to 10.0.0.100)
DNS_ZONES = ["hive", "ep", "user", "svc", "bond"]  # Ulysses internal zones

# Zone descriptions:
#   hive - AI Agents (aria.hive, marcus.hive)
#   ep   - Endpoints/Machines (ep-win-001.ep, ep-linux-001.ep)
#   user - User identities (daniel.user)
#   svc  - Services (trust-anchor.svc, a2a.svc, rag.svc)
#   bond - Bond-scoped discovery (bond-2024-0847.bond)

# DNS Redis key patterns
REDIS_DNS_PREFIX = "dns:"
REDIS_DNS_A_PREFIX = "dns:a:"           # A records: dns:a:aria.hive
REDIS_DNS_AAAA_PREFIX = "dns:aaaa:"     # AAAA records (IPv6)
REDIS_DNS_CNAME_PREFIX = "dns:cname:"   # CNAME records
REDIS_DNS_SRV_PREFIX = "dns:srv:"       # SRV records: dns:srv:_a2a._tcp.aria.hive
REDIS_DNS_TXT_PREFIX = "dns:txt:"       # TXT records
REDIS_DNS_ZONE_PREFIX = "dns:zone:"     # Zone indexes: dns:zone:hive
REDIS_DNS_IDENTITY_PREFIX = "dns:identity:"  # Identity cross-ref: dns:identity:AGENT-aria.hive

# DNS TTL defaults (seconds)
DNS_TTL_AGENT = 120      # Agents: 2x heartbeat interval
DNS_TTL_ENDPOINT = 300   # Endpoints: stable machines
DNS_TTL_SERVICE = 3600   # Services: core infrastructure
DNS_TTL_DEFAULT = 60     # Default TTL

# DNS Zone Sync Configuration (NFR-015)
DNS_SYNC_PORT = 8004                          # Zone Sync daemon API port
DNS_SYNC_POLL_INTERVAL = 5                    # Polling interval in seconds
DNS_SYNC_STALE_CHECK_INTERVAL = 60            # Stale check interval in seconds
DNS_SYNC_STALE_MULTIPLIER = 2.0               # Stale threshold = TTL * multiplier
DNS_SYNC_RELOAD_DEBOUNCE = 5                  # Min seconds between CoreDNS reloads
DNS_ZONES_DIR = "/var/lib/ulysses/dns/zones"  # Zone file output directory
DNS_CHANGES_CHANNEL = "dns:changes"           # Redis pub/sub channel for changes


# =============================================================================
# PKI INFRASTRUCTURE (NFR-013)
# =============================================================================
PKI_CA_DIR = "/opt/ulysses/pki/ca"
PKI_CERTS_DIR = "/opt/ulysses/pki/certs"
PKI_PRIVATE_DIR = "/opt/ulysses/pki/private"
PKI_CSR_DIR = "/opt/ulysses/pki/csr"

# Certificate validity (days)
PKI_ROOT_CA_VALIDITY_DAYS = 3650    # 10 years
PKI_INT_CA_VALIDITY_DAYS = 1825     # 5 years
PKI_CERT_VALIDITY_DAYS = 365        # 1 year
PKI_SHORT_CERT_VALIDITY_DAYS = 90   # 90 days for high-rotation certs

# Redis PKI key patterns
REDIS_PKI_PREFIX = "pki:"
REDIS_PKI_CERT_PREFIX = "pki:cert:"     # Certificate storage
REDIS_PKI_CSR_PREFIX = "pki:csr:"       # CSR storage
REDIS_PKI_REVOKED_SET = "pki:revoked"   # Revoked certificate set


# =============================================================================
# AI AGENT HIVE REDIS KEY PATTERNS (NFR-021, NFR-022C-A)
# =============================================================================
REDIS_HIVE_PREFIX = "hive:"
REDIS_HIVE_AGENT_PREFIX = "hive:agent:"           # Agent storage: hive:agent:{agent_id}
REDIS_HIVE_AGENTS_ALL_SET = "hive:agents:all"     # Set of all agent IDs
REDIS_HIVE_SKILL_AGENTS_PREFIX = "hive:skill:"    # Skill-to-agents index: hive:skill:{skill}:agents
REDIS_HIVE_ENDPOINT_AGENTS_PREFIX = "hive:endpoint:"  # Endpoint-to-agents: hive:endpoint:{id}:agents

# NFR-022C-A: Skill Registry Enhancement
REDIS_HIVE_SKILLS_ALL_SET = "hive:skills:all"     # Set of all skill IDs (dynamic)
REDIS_HIVE_SKILL_METADATA_PREFIX = "hive:skill:"  # Skill metadata: hive:skill:{skill}:metadata

# NFR-022C-B: Skill Wrapper Tool Keys
REDIS_HIVE_SKILL_TOOL_MAPPING = "hive:skill:{skill}:tool_id"  # Maps skill to generated tool ID


# =============================================================================
# CREDENTIAL PATHS (Gap-3 Standardization)
# =============================================================================
# Environment variable for credential path override
FORTIGATE_CREDS_PATH_ENV = "FORTIGATE_CREDS_PATH"

# Standard credential file names
FORTIGATE_CREDS_FILENAME = "fortigate_credentials.yaml"
HYPERVISOR_CREDS_FILENAME = "hypervisor_credentials.yaml"
FORTICLOUD_CREDS_FILENAME = "forticloud_credentials.yaml"

# Credential search order (first match wins)
# 1. Environment variable (if set)
# 2. User MCP config (primary)
# 3. User AppData/Local (Windows secondary)
# 4. System-wide (ProgramData or /etc)
def get_credential_paths(filename: str = FORTIGATE_CREDS_FILENAME) -> list:
    """Get ordered list of credential file paths to search.

    Returns paths in priority order - first existing file wins.
    """
    import os
    paths = []

    # Priority 1: Environment variable override
    env_path = os.environ.get(FORTIGATE_CREDS_PATH_ENV)
    if env_path:
        paths.append(Path(env_path))

    # Priority 2: User MCP config (PRIMARY - MCP server standard)
    paths.append(Path.home() / ".config" / "mcp" / filename)

    # Platform-specific paths
    if os.name == 'nt':
        # Windows: User AppData
        paths.append(Path.home() / "AppData" / "Local" / "mcp" / filename)
        # Windows: System-wide (Ulysses legacy)
        paths.append(Path("C:/ProgramData/Ulysses/config") / filename)
        # Windows: System-wide (MCP standard)
        paths.append(Path("C:/ProgramData/mcp") / filename)
    else:
        # Linux/Mac: System-wide
        paths.append(Path("/etc/mcp") / filename)

    return paths
