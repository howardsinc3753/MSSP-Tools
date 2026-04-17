# FortiWeb 8.0 Security Baseline — 80/20 Rule

**Status:** DRAFT — needs Daniel's review before building tools
**Goal:** Cover 80% of web attacks with sensible defaults that won't break apps
**Philosophy:** Secure by default, exceptions by necessity

---

## Baseline Categories

### 1. Signatures — Known Attack Patterns
**API:** `cmdb/waf/signature`

The single biggest bang-for-buck. FortiGuard signatures catch known SQLi, XSS, RCE, LFI, etc.

| Setting | Baseline Value | Why |
|---------|---------------|-----|
| SQLi signatures (High/Critical) | **alert_deny** | #1 web attack vector |
| XSS signatures (High/Critical) | **alert_deny** | #2 web attack vector |
| Generic attacks (High/Critical) | **alert_deny** | RCE, LFI, command injection |
| Medium severity | **alert** (not deny) | Monitor first, promote to deny after tuning |
| Low/Informational | **alert** or disabled | Noise — don't block, don't alert-fatigue |
| FPM (False Positive Mitigation) | **enabled** | Lexical analysis reduces FP without weakening detection |
| FortiGuard auto-update | **enabled** | New CVE coverage within hours |

**Risk of breaking things:** Low for High/Critical sigs. Medium sigs need monitoring period.

---

### 2. Syntax Based Detection (SBD) — Evasion Defense
**API:** `cmdb/waf/syntax-based-attack-detection`

Catches obfuscated/encoded attacks that bypass pattern-matching signatures. Three detection engines:

| Setting | Baseline Value | Why |
|---------|---------------|-----|
| SQL SBD | **enabled, alert_deny** | Catches encoded SQLi (union-based, stacked, embedded, conditional, arithmetic, line comments, function-based) |
| XSS SBD | **enabled, alert_deny** | Catches encoded XSS (HTML tag, attribute, CSS, JS function, JS variable) |
| CMD Injection SBD | **enabled, alert_deny** | Catches shell command injection |
| Detection targets | **ARGS_NAMES, ARGS_VALUE, REQUEST_COOKIES** minimum | Standard Protection covers these |
| Profile to use | **Standard Protection** | Good coverage without scanning every header (Extended is more aggressive) |
| Block period | **600s** (default) | 10 min block after detection |

**Risk of breaking things:** Low with Standard Protection. Extended Protection scans User-Agent, Referer, all headers, and body — higher FP risk on first deploy.

**Recommendation:** Start with Standard Protection, graduate to Extended after 2-week monitoring.

---

### 3. TLS Configuration — Cipher Hardening
**API:** TBD (need to map SSL cipher endpoint)

| Setting | Baseline Value | Why |
|---------|---------------|-----|
| TLS 1.0 | **disabled** | Deprecated, POODLE/BEAST |
| TLS 1.1 | **disabled** | Deprecated |
| TLS 1.2 | **enabled** — AES-GCM suites only | Still needed for some clients |
| TLS 1.3 | **enabled** | Modern, all suites are strong by design |
| 3DES | **disabled** | Sweet32 attack |
| RC4 | **disabled** | Known broken |
| NULL/EXPORT ciphers | **disabled** | No encryption = no protection |
| CBC-mode ciphers | **disable if possible** | Lucky13, but some legacy needs them |
| Cipher group | **Mozilla-Intermediate** or custom equivalent | Vetted by Mozilla, updated regularly |
| Insecure renegotiation | **disabled** | SSL-DoS attack vector |

**Risk of breaking things:** Medium — some legacy clients (old Android, IE11) may fail. Test first.

---

### 4. HTTP Protocol Constraints
**API:** `cmdb/waf/http-protocol-parameter-restriction`

Limits on request structure. Prevents buffer overflow, smuggling, and oversized payload attacks.

| Setting | Baseline Value | Why |
|---------|---------------|-----|
| Max URL length | **8192** (8KB) | Blocks absurdly long URLs used for buffer overflow |
| Max header length | **8192** | Same reasoning |
| Max number of headers | **50** | Slowloris-style header flooding |
| Max body size | **Depends on app** | Partner app needs 50MB JSON — can't set too low |
| Max cookie header length | **8192** | Oversized cookie attacks |
| Max number of cookies | **64** | Cookie flooding |
| HTTP methods allowed | **GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD** | Block TRACE, TRACK, CONNECT |

**Risk of breaking things:** HIGH if body size is too restrictive. Must tune per-app.

---

### 5. Cookie Security
**API:** `cmdb/waf/cookie-security`

FortiWeb can enforce cookie attributes that the app server may not set.

| Setting | Baseline Value | Why |
|---------|---------------|-----|
| Secure flag | **enabled** | Cookies only over HTTPS |
| HttpOnly flag | **enabled** | Blocks JS access (XSS cookie theft) |
| SameSite | **Lax** | CSRF protection without breaking OAuth flows |
| Cookie tamper detection | **enabled** | FortiWeb signs cookies, rejects modifications |
| Cookie encryption | **optional** | Opaque values to client — nice but can break apps that read their own cookies |

**Risk of breaking things:** Medium — cookie signing can conflict with app-managed cookies. Need to identify which cookies the app controls vs which FortiWeb should protect.

---

### 6. HTTP Security Headers (Response Injection)
**API:** TBD (may be in waf/http-header-security or server-policy level)

FortiWeb can inject security headers into responses even if the app doesn't set them.

| Header | Baseline Value | Why |
|--------|---------------|-----|
| X-Content-Type-Options | **nosniff** | Prevents MIME-type sniffing |
| X-Frame-Options | **SAMEORIGIN** | Clickjacking protection |
| X-XSS-Protection | **1; mode=block** | Legacy browser XSS filter |
| Strict-Transport-Security | **max-age=31536000; includeSubDomains** | Force HTTPS for 1 year |
| Content-Security-Policy | **App-specific** | Must be tuned per app — too strict breaks things |
| Referrer-Policy | **strict-origin-when-cross-origin** | Limits referer leakage |

**Risk of breaking things:** Low for all except CSP. CSP requires app-specific tuning.

---

### 7. DoS Protection
**API:** `cmdb/waf/http-connection-flood-check-rule` + others

| Setting | Baseline Value | Why |
|---------|---------------|-----|
| HTTP connection flood | **enabled, alert_deny** | Blocks connection-based DoS |
| Connection threshold | **500** (tune per app) | Default 100 is too low for production apps |
| HTTP request rate limit | **enabled** | Blocks request flooding |
| TCP SYN flood | **enabled** (if available at network layer) | Layer 4 DoS |
| Block period | **600s** | Temporary ban on offenders |
| Share IP detection | **enabled** | Adjust thresholds for NAT/shared IPs |

**Risk of breaking things:** HIGH if thresholds are too low. Must baseline normal traffic first.

---

### 8. Alert Email / Logging
**API:** `cmdb/log/email-policy` + `cmdb/log/trigger-policy` + `cmdb/log/syslog-policy`

| Setting | Baseline Value | Why |
|---------|---------------|-----|
| Alert email | **configured** | Someone needs to know when attacks happen |
| Alert severity | **High and Critical only** | Avoid inbox flood |
| SMTP transport | **SMTPS or STARTTLS** | Never send alerts in cleartext |
| Syslog forwarding | **enabled** to SIEM | Central visibility |
| Attack log storage | **enabled, local + remote** | Forensic evidence |
| Trigger policy | **bound to server policy** | Triggers only fire if attached |

**Risk of breaking things:** None — observability only. Zero risk of blocking traffic.

---

### 9. FortiGuard Subscription
**API:** `cmdb/system/fortiguard`

| Setting | Baseline Value | Why |
|---------|---------------|-----|
| Auto-update | **enabled** | New sigs for new CVEs |
| Anycast | **enabled** | Fastest update server |
| DB integrity auto-recover | **enabled** | Self-heal corrupted sig DB |
| Subscription active | **verify** | Expired sub = no updates = stale protection |

**Risk of breaking things:** None.

---

## Proposed SDK Tool Structure

One tool per baseline category, each with two modes:

1. **`audit`** — Read current config, compare to baseline, report gaps (READ-ONLY, safe)
2. **`apply`** — Push baseline settings to the device (WRITE, requires confirmation)

| Tool Name | Baseline Category |
|-----------|-------------------|
| `fortiweb-baseline-signatures` | #1 Signatures |
| `fortiweb-baseline-sbd` | #2 Syntax Based Detection |
| `fortiweb-baseline-tls` | #3 TLS/Cipher hardening |
| `fortiweb-baseline-http-constraints` | #4 HTTP Protocol Constraints |
| `fortiweb-baseline-cookie-security` | #5 Cookie Security |
| `fortiweb-baseline-headers` | #6 HTTP Security Headers |
| `fortiweb-baseline-dos` | #7 DoS Protection |
| `fortiweb-baseline-alerting` | #8 Email/Syslog/Logging |
| `fortiweb-baseline-fortiguard` | #9 FortiGuard Status |

Plus one meta-tool:
| `fortiweb-baseline-audit` | Runs ALL audit checks, produces a single report card |

---

## Traffic Flow — When to Apply What

```
Client Request
  │
  ├─ TCP SYN flood check          (#7 DoS)
  ├─ TLS negotiation              (#3 TLS)
  ├─ HTTP protocol validation     (#4 Constraints)
  ├─ Signature scan               (#1 Signatures)
  ├─ SBD scan                     (#2 SBD)
  ├─ Cookie validation            (#5 Cookies)
  ├─ [ML / Bot detection]         (future — not in 80/20)
  │
  ├─► Backend server
  │
  ├─ Response headers injected    (#6 Headers)
  ├─ Cookie attributes enforced   (#5 Cookies)
  └─► Client Response
```

---

## Open Questions for Daniel

1. Should the baseline be a single "FortiWeb Security Baseline" profile, or per-category tools that compose?
2. Do we want a `--dry-run` flag that shows what WOULD change, or is `audit` mode sufficient?
3. Should the baseline doc live in the SDK repo or in a separate best-practices repo?
4. For partners: should the tool generate a PDF/HTML report card they can show their customers?
5. Should we version the baseline (v1.0, v1.1) so partners know which standard they're measured against?
