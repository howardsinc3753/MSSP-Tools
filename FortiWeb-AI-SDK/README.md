# FortiWeb AI SDK

Python SDK and tool collection for automating FortiWeb 8.0+ configuration and monitoring via REST API. Built for MSSP / Sales Engineering workflows — audit partner deployments, apply security baselines, and deploy hardened server policies without clicking through the GUI.

## What's Inside

```
FortiWeb-AI-SDK/
├── sdk/                 # Shared REST API client (fortiweb_client.py)
├── tools/               # Self-contained tools (manifest + Python + Skills.md)
├── docs/                # API reference + baseline specifications
└── API_reference/       # FortiWeb 8.0 Swagger JSON (config + monitor)
```

Each tool follows the Trust Anchor tool format — one folder per tool with:
- `manifest.yaml` — tool metadata, parameters, schema, capabilities
- `<tool-name>.py` — Python implementation with `main(context)` entry point
- `Skills.md` — AI guidance (purpose, when to use, examples, error handling)
- `config/` — local credentials (gitignored)

## Tool Inventory

| Tool | Purpose |
|------|---------|
| `fortiweb-api-token` | Manage REST API admin accounts |
| `fortiweb-sqli-baseline` | Signatures + SBD for SQL injection protection |
| `fortiweb-cookie-baseline` | Cookie security (sign, Secure, HttpOnly, SameSite) |
| `fortiweb-tls-baseline` | TLS cipher hardening (Mozilla-Intermediate equivalent) |
| `fortiweb-dos-baseline` | HTTP/Layer 4 flood prevention with bot CAPTCHA |
| `fortiweb-ipintel-baseline` | FortiGuard IP reputation (monitor-then-block workflow) |
| `fortiweb-json-baseline` | JSON validation for REST API endpoints |
| `fortiweb-websocket-baseline` | WebSocket security (Socket.IO, native WS) |
| `fortiweb-server-policy` | Full server policy stack (VIP + VServer + Pool + Policy) |

## Tool Pattern

Every tool exposes the same three actions:

| Action | Mode | What It Does |
|--------|------|-------------|
| `audit` | READ | Check current config against baseline, report findings |
| `apply` | WRITE | Create best-practice objects and wire into protection profile |
| `status` | READ | One-line posture summary |

## Quick Start

### 1. Set up credentials

Copy the credential template to a gitignored location:

```yaml
# ~/.config/mcp/fortiweb_credentials.yaml
devices:
  my-fortiweb:
    host: "<fortiweb-ip>"
    username: "admin"
    password: "<admin-password>"
    verify_ssl: false

default_lookup:
  "<fortiweb-ip>": my-fortiweb
```

The SDK searches these paths in order:
1. `~/.config/mcp/fortiweb_credentials.yaml` (primary)
2. `~/AppData/Local/mcp/fortiweb_credentials.yaml` (Windows)
3. `C:/ProgramData/mcp/fortiweb_credentials.yaml` (Windows system)
4. `/etc/mcp/fortiweb_credentials.yaml` (Linux/Mac system)
5. `C:/ProgramData/Ulysses/config/fortiweb_credentials.yaml` (Ulysses platform)

### 2. Run a tool directly

```bash
python tools/org.ulysses.noc.fortiweb-sqli-baseline/org.ulysses.noc.fortiweb-sqli-baseline.py
```

Or import the main function:

```python
import importlib.util
spec = importlib.util.spec_from_file_location("sqli", "tools/org.ulysses.noc.fortiweb-sqli-baseline/org.ulysses.noc.fortiweb-sqli-baseline.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

result = mod.main({
    "target_ip": "<fortiweb-ip>",
    "action": "audit",
    "profile_name": "Inline Standard Protection"
})
```

### 3. Deployment workflow

```
1. fortiweb-sqli-baseline      → apply  (creates BP-SQLi-Signatures + BP-SQLi-Protection)
2. fortiweb-cookie-baseline    → apply  (creates BP-Cookie-Security, wires in)
3. fortiweb-dos-baseline       → apply  (creates DoS rules, wires in)
4. fortiweb-tls-baseline       → apply  (creates BP-TLS-Hardened cipher group)
5. fortiweb-ipintel-baseline   → apply-monitor   (enable in monitor mode)
6. fortiweb-json-baseline      → apply  (REST API protection)
7. fortiweb-websocket-baseline → apply  (if app uses WebSockets)
8. fortiweb-server-policy      → apply  (the keystone — ties everything to real traffic)
```

## Authentication

FortiWeb 8.0 uses **stateless Base64-encoded credential headers** — no login/logout endpoints.

```python
Authorization: <base64({"username":"admin","password":"pass","vdom":"root"})>
```

The SDK handles this transparently. See [docs/API-Reference.md](docs/API-Reference.md) for protocol details.

## Security Baseline

See [docs/Security-Baseline-DRAFT.md](docs/Security-Baseline-DRAFT.md) for the full "80/20 rule" baseline — the minimum configuration that stops 80% of real-world attacks without breaking the application.

Specific SQLi details in [docs/SQLi-Baseline.md](docs/SQLi-Baseline.md).

## Known Limitations

- **Sub-table API limitation:** Some FortiWeb REST endpoints accept sub-table arrays in POST/PUT bodies but don't persist them (http-header-security-list, vserver vip-list, server-pool pserver-list, json/websocket rule-list on policies). Tools create the container object; final linkage requires GUI. Each tool's `apply` response lists the GUI steps needed.
- **Predefined profiles are read-only** — tools create custom profiles with `BP-` prefix (configurable).
- **Signature profile wizard** returns HTTP 500 + errcode 1 but actually succeeds. Tools handle this quirk.

## Requirements

- Python 3.10+
- `pyyaml` (only runtime dependency)
- FortiWeb 8.0.x with REST API enabled

No `requests`, no `httpx` — standard library `urllib` only. Keeps the tools portable and dependency-free.

## Contributing

Each tool is self-contained. To add a new baseline:

1. Copy an existing tool directory (e.g., `org.ulysses.noc.fortiweb-cookie-baseline`)
2. Rename, update manifest.yaml with new canonical_id
3. Update the Python `main()` logic and baseline values
4. Write Skills.md with purpose, parameters, examples
5. QA test all 3 actions (audit/apply/status) against a lab device

## License

Part of the MSSP-SE-Tools collection. See parent repo for license details.
