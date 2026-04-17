# FortiWeb Cookie Security Baseline Skills

## Purpose

Audit and enforce cookie security best-practice on FortiWeb 8.0+ devices. Ensures cookies are protected from tampering, theft, injection, and replay attacks. Covers three areas:

1. **Cookie Security Policy** — Signing/encryption, Secure/HttpOnly/SameSite flags
2. **Session Cookie** — FortiWeb's cookiesession1 for session affinity and tracking
3. **Bot Mitigation** — Classifies bot-injected vs legitimate cookies

## When to Use This Tool

**Use this tool when the user asks:**
- "Check cookie security on FortiWeb"
- "Are cookies protected from tampering?"
- "Is HttpOnly/Secure/SameSite set?"
- "Set up cookie best practices"
- "Validate session affinity cookies"
- "Are bot cookies being handled?"
- "Review CSRF cookie protections"

**Do NOT use this tool for:**
- SQL injection protection (use fortiweb-sqli-baseline)
- TLS/cipher configuration (use fortiweb-tls-baseline)
- DoS protection (use fortiweb-dos-baseline)

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `target_ip` | string | Yes | - | FortiWeb management IP |
| `action` | string | Yes | - | `audit`, `apply`, or `status` |
| `profile_name` | string | No | Inline Standard Protection | Profile to audit |
| `bp_prefix` | string | No | BP | Prefix for created objects |

## Actions

### `audit` — Read-only baseline check

Checks performed:

| # | Check | Baseline | Why |
|---|-------|----------|-----|
| 1 | Cookie policy attached | Must exist | No policy = no protection |
| 2 | Security mode | **signed** | Detects cookie tampering |
| 3 | Secure flag | **enable** | Cookies only sent over HTTPS |
| 4 | HttpOnly flag | **enable** | Blocks JS access (XSS mitigation) |
| 5 | SameSite enabled | **enable** | Enables SameSite attribute |
| 6 | SameSite value | **Lax** | CSRF protection, won't break OAuth |
| 7 | Action | **alert_deny** | Block + log on tampering |
| 8 | Block period | **600** | 10 min temporary ban |
| 9 | Severity | **High** | Proper log classification |
| 10 | Suspicious cookies | **Never** | Reject unrecognized cookies |
| 11 | Cookie exceptions | **0** | No exceptions unless justified |
| 12 | Session cookie | **enable** | FortiWeb session tracking |
| 13 | Bot mitigation | **attached** | Bot cookie classification |

### `apply` — Create best-practice configuration

Creates:
1. **`{prefix}-Cookie-Security`** — Cookie security policy with baseline settings
2. Wires it into the best available protection profile (prefers BP-SQLi-Protection)
3. Enables session cookie (cookiesession1) if not already on
4. Attaches "Predefined - Bot Mitigation" if no bot policy wired

**Important:** The apply action will find and wire into the BP-SQLi-Protection profile if it exists (created by the SQLi baseline tool). This keeps all baseline configs in one profile.

### `status` — Quick posture summary

Returns GOOD, PARTIAL, or WEAK:
- **GOOD**: Cookie policy with signing + Secure + HttpOnly
- **PARTIAL**: Policy exists but missing key flags
- **WEAK**: No cookie policy attached

## Baseline Rationale

### Why Signed (not Encrypted)?
- **Signed** = FortiWeb adds an HMAC signature. If the cookie is modified, the signature won't match and FortiWeb rejects it. The cookie value is still readable.
- **Encrypted** = Cookie value is opaque to the client. More secure but can break apps that read their own cookies client-side.
- **Baseline: signed** — safer default that catches tampering without breaking functionality.

### Why SameSite=Lax (not Strict)?
- **Strict** = Cookie never sent on cross-site requests. Breaks OAuth redirects, SSO, and links from email.
- **Lax** = Cookie sent on top-level navigation (clicking a link) but NOT on cross-site POST/iframe/AJAX. Blocks CSRF attacks.
- **None** = No restriction (requires Secure flag). Only use if the app needs cross-site cookie access.
- **Baseline: Lax** — prevents CSRF without breaking standard auth flows.

### Session Cookie (cookiesession1)
FortiWeb can inject its own `cookiesession1` cookie for:
- **Session affinity** — Keeps a user on the same backend server in a pool
- **Session tracking** — Enables per-session security features (user tracking, threat scoring)
- **Cookie security** — The cookie security policy operates on this session context

Without the session cookie, cookie signing/tamper detection has no session context to validate against.

### Bot Mitigation
FortiWeb classifies bots by signature (known bot database). Bot-injected cookies behave differently from browser cookies. The bot mitigation policy:
- Blocks known malicious bots (DoS bots, spam bots, trojans, scanners)
- Allows known search engines (Google, Bing) to bypass
- Classifies crawlers at alert_deny

## Example Usage

### Audit current config
```json
{"target_ip": "192.168.209.31", "action": "audit"}
```

### Apply best practice (wires into BP-SQLi-Protection if exists)
```json
{"target_ip": "192.168.209.31", "action": "apply", "bp_prefix": "BP"}
```

### Quick status
```json
{"target_ip": "192.168.209.31", "action": "status"}
```

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| Profile not found | Wrong profile_name | Check available profiles |
| Already exists | apply ran twice | Delete existing or use different prefix |
| Permission denied | Tried to modify predefined profile | Use apply with a custom profile |
| No writable profile | Only predefined profiles exist | Run SQLi baseline apply first |

## Related Tools

- `org.ulysses.noc.fortiweb-sqli-baseline` — SQL injection baseline (run first)
- `org.ulysses.noc.fortiweb-tls-baseline` — TLS/cipher hardening (planned)
- `org.ulysses.noc.fortiweb-dos-baseline` — DoS protection (planned)
- `org.ulysses.noc.fortiweb-headers-baseline` — HTTP security headers (planned)
