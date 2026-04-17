# FortiWeb SQLi Baseline Skills

## Purpose

Audit and enforce SQL Injection best-practice configuration on FortiWeb 8.0+ devices. Ensures the three defense layers (signatures, SBD, protection profile wiring) are correctly configured for the 80/20 security baseline.

FortiWeb protects against SQLi with three layers:
1. **Signatures** — Pattern-match known SQLi payloads (FortiGuard-updated)
2. **Syntax Based Detection (SBD)** — Grammar-parsing catches obfuscated/encoded SQLi
3. **Protection Profile** — Wires signatures + SBD together and binds to server policy

All three must be configured correctly. This tool audits and fixes gaps.

## When to Use This Tool

**Use this tool when the user asks:**
- "Check SQLi protection on FortiWeb"
- "Is SQL injection blocking enabled?"
- "Audit WAF signature configuration"
- "Set up SQLi best practices"
- "Create a hardened FortiWeb profile"
- "Are SBD engines enabled?"
- "Review FortiWeb security posture"

**Do NOT use this tool for:**
- TLS/cipher configuration (use fortiweb-tls-baseline)
- Cookie security (use fortiweb-cookie-baseline)
- DoS protection (use fortiweb-dos-baseline)
- FortiGate operations (use fortigate-* tools)

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `target_ip` | string | Yes | - | FortiWeb management IP |
| `action` | string | Yes | - | `audit`, `apply`, or `status` |
| `profile_name` | string | No | Inline Standard Protection | Profile to audit (audit/status) |
| `bp_prefix` | string | No | BP | Prefix for objects created by apply |
| `timeout` | integer | No | 30 | Request timeout in seconds |

## Actions

### `audit` — Read-only baseline check

Runs 10+ checks against the baseline. Safe to run anytime.

**Checks performed:**
1. Signature profile attached to protection profile
2. SQL Injection class enabled + alert_deny + FPM on
3. XSS class enabled + alert_deny + FPM on
4. Generic Attacks class enabled + alert_deny
5. Known Exploits class enabled + alert_deny
6. No signatures downgraded to alert-only
7. FPM not disabled for any signatures
8. FortiGuard auto-update enabled
9. SBD profile attached to protection profile
10. All 6 SQL SBD engines enabled at alert_deny
11. SQL detection targets include ARGS_NAMES + ARGS_VALUE + COOKIES
12. SQL detection templates include SINGLE_QUOTE + DOUBLE_QUOTE + AS_IS
13. Attack log accessible

### `apply` — Create best-practice configuration

Creates two objects:
1. **`{prefix}-SQLi-Signatures`** — Signature profile with all DBs + common web servers configured via wizard
2. **`{prefix}-SQLi-Protection`** — Protection profile with sig + SBD wired together

After creation, runs audit on the new profile to verify.

**Important:** The created protection profile must be manually assigned to a server policy to become active. This tool does NOT modify server policies.

### `status` — Quick posture summary

Returns a one-line posture assessment: GOOD, PARTIAL, or WEAK.

## Baseline Definition

### Signatures (alert_deny = block + log)

| Class | Action | FPM | Why |
|-------|--------|-----|-----|
| SQL Injection (030000000) | alert_deny | enabled | #1 web attack |
| Cross Site Scripting (010000000) | alert_deny | enabled | #2 web attack |
| Generic Attacks (050000000) | alert_deny | enabled | RCE, LFI, command injection |
| Known Exploits (090000000) | alert_deny | disabled | CVE-specific attacks |
| Trojans (070000000) | alert | - | Monitor, don't block |
| Information Disclosure (080000000) | alert | - | Monitor, don't block |

### SBD Engines (all 6 must be enabled at alert_deny)

| Engine | What it catches |
|--------|----------------|
| Stacked Queries | `; DROP TABLE` patterns |
| Embedded Queries | Nested SELECT inside INSERT/UPDATE |
| Condition Based | `OR 1=1`, `AND 1=0` |
| Arithmetic Operation | `1+1`, math-based probing |
| Line Comments | `--`, `#` comment-based evasion |
| Function Based | `CONCAT()`, `CHAR()` function abuse |

## Example Usage

### Audit current config
```json
{"target_ip": "192.168.209.31", "action": "audit"}
```

### Audit a specific profile
```json
{"target_ip": "192.168.209.31", "action": "audit", "profile_name": "Inline Extended Protection"}
```

### Apply best practice
```json
{"target_ip": "192.168.209.31", "action": "apply", "bp_prefix": "Thrive"}
```
Creates: `Thrive-SQLi-Signatures` + `Thrive-SQLi-Protection`

### Quick status
```json
{"target_ip": "192.168.209.31", "action": "status"}
```

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| Profile not found | Wrong profile_name | Check available profiles via status |
| Already exists | apply ran twice | Delete existing objects or use different prefix |
| Permission denied | Tried to modify predefined profile | Use apply to create custom profile |
| Connection failed | Network issue | Check path to FortiWeb |

## Related Tools

- `org.ulysses.noc.fortiweb-api-token` — Manage API access
- `org.ulysses.noc.fortiweb-tls-baseline` — TLS/cipher hardening (planned)
- `org.ulysses.noc.fortiweb-cookie-baseline` — Cookie security (planned)
- `org.ulysses.noc.fortiweb-dos-baseline` — DoS protection (planned)
