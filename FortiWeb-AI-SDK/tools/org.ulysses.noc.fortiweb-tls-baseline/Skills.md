# FortiWeb TLS Cipher Baseline Skills

## Purpose

Audit and enforce TLS/cipher best-practice on FortiWeb 8.0+. Identifies weak protocols, weak ciphers, and insecure renegotiation across cipher groups and server policies.

## When to Use This Tool

**Use this tool when the user asks:**
- "Check TLS configuration on FortiWeb"
- "Are weak ciphers enabled?"
- "Is TLS 1.0 or 1.1 still on?"
- "Harden the SSL/TLS config"
- "Create a secure cipher group"
- "Check for 3DES/RC4/NULL ciphers"
- "Is insecure renegotiation disabled?"

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `target_ip` | string | Yes | - | FortiWeb management IP |
| `action` | string | Yes | - | `audit`, `apply`, or `status` |
| `bp_prefix` | string | No | BP | Prefix for created objects |

## Baseline

### Protocols
| Protocol | Status | Why |
|----------|--------|-----|
| TLS 1.0 | **disabled** | POODLE, BEAST attacks |
| TLS 1.1 | **disabled** | Deprecated, no modern use |
| TLS 1.2 | **enabled** | AES-GCM suites only |
| TLS 1.3 | **enabled** | All suites strong by design |

### Weak Ciphers (FAIL if present)
| Pattern | Risk |
|---------|------|
| DES-CBC3 (3DES) | Sweet32 attack |
| RC4 | Known broken |
| NULL | No encryption |
| EXPORT | 40/56-bit keys |
| SEED | Legacy, not recommended |

### CBC-Mode Ciphers (WARN)
CBC ciphers are vulnerable to Lucky13 but some legacy clients need them. Tool warns but doesn't fail.

### Baseline TLS 1.2 Ciphers (9 suites)
```
ECDHE-ECDSA-AES256-GCM-SHA384
ECDHE-RSA-AES256-GCM-SHA384
DHE-RSA-AES256-GCM-SHA384
ECDHE-ECDSA-CHACHA20-POLY1305
ECDHE-RSA-CHACHA20-POLY1305
DHE-RSA-CHACHA20-POLY1305
ECDHE-ECDSA-AES128-GCM-SHA256
ECDHE-RSA-AES128-GCM-SHA256
DHE-RSA-AES128-GCM-SHA256
```

### Server Policy Checks
- `ssl-noreg=enable` — Disables insecure renegotiation (SSL-DoS prevention)
- `use-ciphers-group=enable` — References a cipher group (recommended over inline)
- `http-to-https=enable` — Redirects HTTP to HTTPS

## Architecture

TLS config lives in two places on FortiWeb:

1. **Cipher Groups** — Reusable objects at `Server Objects > SSL Ciphers`
   - Predefined: Mozilla-Modern (TLS 1.3 only), Mozilla-Intermediate (TLS 1.2+1.3)
   - Custom: User-created groups
2. **Server Policies** — Per-policy TLS settings at `Policy > Server Policy`
   - Can reference a cipher group (`use-ciphers-group=enable`)
   - Or have inline TLS settings (`tls-v10`, `ssl-cipher`, etc.)

The tool audits both. Apply creates a custom cipher group ready to reference.

## Example Usage

### Audit all cipher configs
```json
{"target_ip": "192.168.209.31", "action": "audit"}
```

### Create hardened cipher group
```json
{"target_ip": "192.168.209.31", "action": "apply", "bp_prefix": "BP"}
```
Creates `BP-TLS-Hardened` — assign to server policy via `ssl-ciphers-group`.

### Quick status
```json
{"target_ip": "192.168.209.31", "action": "status"}
```

## Related Tools

- `org.ulysses.noc.fortiweb-sqli-baseline` — SQL injection baseline
- `org.ulysses.noc.fortiweb-cookie-baseline` — Cookie security baseline
- `org.ulysses.noc.fortiweb-dos-baseline` — DoS protection (planned)
