# FortiWeb SQLi Protection — Baseline Specification

**Status:** DRAFT
**Covers:** SQL Injection protection across all FortiWeb layers
**API Version:** v2.0

---

## FortiWeb SQLi Defense Layers

FortiWeb has **4 layers** that work together for SQL injection protection. All must be configured correctly for the 80/20 posture.

```
Request arrives
  │
  ├─ Layer 1: SIGNATURES — Pattern matching known SQLi payloads
  │    API: GET/PUT  cmdb/waf/signature?mkey=<profile>
  │    Monitor: waf/signature.advanced.search (search sigs)
  │             waf/signature.advanced.signature (per-sig config)
  │             waf/signature.advanced.signature.falsepositivemitigation
  │             waf/signature.advanced.signature.status
  │
  ├─ Layer 2: SBD — Syntax Based Detection (grammar parsing)
  │    API: GET/PUT  cmdb/waf/syntax-based-attack-detection?mkey=<profile>
  │    Detects: stacked queries, embedded queries, conditionals,
  │             arithmetic ops, line comments, function-based
  │
  ├─ Layer 3: PARAMETER VALIDATION — Positive security (input rules)
  │    API: GET/POST/PUT/DELETE  cmdb/waf/parameter-validation-rule
  │         GET/POST/PUT/DELETE  cmdb/waf/input-rule
  │    Monitor: waf/parameter-validation.parameter-list
  │
  ├─ Layer 4: PROTECTION PROFILE — Ties it all together
  │    API: GET/PUT  cmdb/waf/web-protection-profile.inline-protection?mkey=<profile>
  │    Fields: signature-rule, syntax-based-attack-detection,
  │            parameter-validation-rule
  │
  └─ MONITORING:
       Attack logs: log/logaccess.attack
       Sig details: log/logaccess.attackdetail.signatureid
       OWASP map:   log/logaccess.owasp_mapping_obj
```

---

## API Endpoint Index — SQLi

### Configuration APIs (cmdb, base: /api/v2.0/cmdb)

| # | Endpoint | Methods | Purpose |
|---|----------|---------|---------|
| 1 | `/waf/signature` | GET POST PUT DELETE | Signature profiles (main classes, disabled sigs, alert-only, FPM) |
| 2 | `/waf/signature_update_policy` | GET PUT | FortiGuard signature auto-update settings |
| 3 | `/waf/syntax-based-attack-detection` | GET POST PUT DELETE | SBD profiles (SQL/XSS/CMD detection engines) |
| 4 | `/waf/parameter-validation-rule` | GET POST PUT DELETE | Parameter validation policies |
| 5 | `/waf/input-rule` | GET POST PUT DELETE | Individual input rules (per-URL/parameter) |
| 6 | `/waf/web-protection-profile.inline-protection` | GET POST PUT DELETE | Protection profiles (wires sig+SBD+param together) |
| 7 | `/waf/exclude-url` | GET POST PUT DELETE | URL exceptions (bypass scanning for specific paths) |
| 8 | `/waf/base-signature-disable` | GET POST PUT DELETE | Globally disabled signatures |
| 9 | `/waf/staged_signature_list` | GET POST PUT DELETE | Staged signatures pending deployment |

### Monitor APIs (base: /api/v2.0)

| # | Endpoint | Purpose |
|---|----------|---------|
| 10 | `/waf/signature.advanced.search` | Search signature database |
| 11 | `/waf/signature.advanced.signature` | Per-signature config details |
| 12 | `/waf/signature.advanced.signature.status` | Sig enabled/disabled status |
| 13 | `/waf/signature.advanced.signature.alertonly` | Sig alert-only status |
| 14 | `/waf/signature.advanced.signature.falsepositivemitigation` | FPM status per sig |
| 15 | `/waf/signature.advanced.signature.exception` | Per-sig exceptions |
| 16 | `/waf/signature.advanced.details` | Detailed sig info (CVE, description) |
| 17 | `/waf/signature.update.list` | Pending signature updates |
| 18 | `/waf/signatures` | Full signature listing |
| 19 | `/log/logaccess.attack` | Attack log (SQLi hits show here) |
| 20 | `/log/logaccess.attackdetail.signatureid` | Attack detail by signature ID |

---

## Current State — Lab FortiWeb (192.168.209.31)

### Signature Profiles (10 predefined)

| Profile | Sensitivity | Sigs Disabled | Alert-Only | FPM Disabled |
|---------|------------|---------------|------------|--------------|
| Standard Protection | 4 | 0 | 0 | 0 |
| Extended Protection | 4 | 0 | 0 | 0 |
| Alert Only | 4 | 0 | 0 | 0 |
| Exchange 2013/2016/2019 | 4 | 0 | 0 | 0 |
| SharePoint 2013/2016 | 4 | 0 | 0 | 0 |
| WordPress | 4 | 0 | 0 | 0 |
| Drupal | 4 | 0 | 0 | 0 |

### SBD Profiles (3 predefined)

| Profile | SQL Engines | Actions | Detection Targets |
|---------|------------|---------|-------------------|
| **Standard Protection** | All 6 SQL engines enabled | alert_deny | ARGS_NAMES, ARGS_VALUE, REQUEST_COOKIES |
| **Extended Protection** | All 6 SQL engines enabled | alert_deny | + USER_AGENT, REFERER, OTHER_HEADERS, BODY |
| **Alert Only** | All 6 SQL engines enabled | alert (no block) | ARGS_NAMES, ARGS_VALUE, REQUEST_COOKIES |

SQL SBD engines: stacked-queries, embedded-queries, condition-based, arithmetic-operation, line-comments, function-based

### Protection Profiles — What's Wired

| Profile | Signature Rule | SBD | Param Validation |
|---------|---------------|-----|-----------------|
| **Inline Standard Protection** | Standard Protection | **EMPTY** | EMPTY |
| **Inline Extended Protection** | Extended Protection | Extended Protection | EMPTY |
| **Inline Alert Only** | Alert Only | Alert Only | EMPTY |
| Exchange/SharePoint/WP/Drupal | Matching sig profile | **EMPTY** | EMPTY |

**Key finding:** "Inline Standard Protection" has signatures but **NO SBD attached**. This is a gap — signatures alone miss obfuscated SQLi.

---

## Baseline — What "Good" Looks Like for SQLi

### Layer 1: Signatures

| Setting | Baseline Value | API Field |
|---------|---------------|-----------|
| Profile to use | Custom or "Standard Protection" | `signature-rule` on protection profile |
| SQLi sigs (High/Critical) | **alert_deny** | `main_class_list` — SQL Injection class enabled |
| FPM | **enabled** (not in fpm_disable_list) | `fpm_disable_list` should NOT contain SQLi sigs |
| Sensitivity | **3 or 4** | `sensitivity-level` |
| FortiGuard auto-update | **enabled** | `cmdb/waf/signature_update_policy` |

### Layer 2: SBD

| Setting | Baseline Value | API Field |
|---------|---------------|-----------|
| Profile to use | "Standard Protection" minimum | `syntax-based-attack-detection` on protection profile |
| All 6 SQL engines | **enabled** | `sql-stacked-queries-status` through `sql-function-based-status` |
| Action | **alert_deny** | `sql-*-action` |
| Severity | **High** | `sql-*-severity` |
| Threat weight | **severe** | `sql-*-threat-weight` |
| Block period | **600s** | `sql-*-block-period` |
| Detection targets | ARGS_NAMES + ARGS_VALUE + REQUEST_COOKIES minimum | `detection-target-sql` |
| SQL templates | SINGLE_QUOTE + DOUBLE_QUOTE + AS_IS | `sql-detection-template` |

### Layer 3: Parameter Validation (optional — positive security)

| Setting | Baseline Value | Notes |
|---------|---------------|-------|
| Policy | Created per-app | Define allowed input types for sensitive params |
| JSON support | **enabled** | For REST APIs with JSON bodies |
| Block unknown params | **disabled** (initially) | Too aggressive for day-one — enable after learning |
| Action | **alert** (initially), then **alert_deny** | Monitor-then-enforce |

### Layer 4: Protection Profile Wiring

| Setting | Baseline Value |
|---------|---------------|
| `signature-rule` | Must reference a sig profile with SQLi enabled |
| `syntax-based-attack-detection` | Must reference an SBD profile (NOT empty) |
| `parameter-validation-rule` | Optional but recommended for high-value endpoints |

---

## SDK Tool: `org.ulysses.noc.fortiweb-sqli-baseline`

### Actions

| Action | Mode | What it does |
|--------|------|-------------|
| `audit` | READ | Check all 4 layers, report gaps against baseline |
| `apply-sbd` | WRITE | Attach SBD profile to protection profile |
| `apply-signatures` | WRITE | Configure signature profile for SQLi best practice |
| `status` | READ | Show current SQLi protection state in human-readable format |

### Audit Checks

```
CHECK 1: Signature profile has SQLi class enabled (not in sub_class_disable_list)
CHECK 2: SQLi sigs are alert_deny, not just alert (not in alert_only_list)
CHECK 3: FPM is enabled for SQLi sigs (not in fpm_disable_list)
CHECK 4: FortiGuard sig updates are enabled
CHECK 5: SBD profile is attached to protection profile (not empty string)
CHECK 6: All 6 SQL SBD engines are enabled
CHECK 7: SQL SBD action is alert_deny (not just alert)
CHECK 8: SQL detection targets include ARGS_NAMES + ARGS_VALUE + REQUEST_COOKIES
CHECK 9: SQL detection templates include all 3 (SINGLE_QUOTE, DOUBLE_QUOTE, AS_IS)
CHECK 10: Protection profile references correct signature + SBD profiles
```

### Example Audit Output

```json
{
  "success": true,
  "target_ip": "192.168.209.31",
  "action": "audit",
  "profile": "Inline Standard Protection",
  "score": "6/10",
  "findings": [
    {"check": 1, "status": "PASS", "detail": "SQLi signatures enabled in Standard Protection"},
    {"check": 2, "status": "PASS", "detail": "No SQLi sigs in alert-only list"},
    {"check": 3, "status": "PASS", "detail": "FPM enabled (no SQLi sigs in fpm_disable_list)"},
    {"check": 4, "status": "WARN", "detail": "Signature auto-update status not verified"},
    {"check": 5, "status": "FAIL", "detail": "SBD profile NOT attached — syntax-based-attack-detection is empty"},
    {"check": 6, "status": "N/A",  "detail": "Skipped — no SBD profile attached"},
    {"check": 7, "status": "N/A",  "detail": "Skipped — no SBD profile attached"},
    {"check": 8, "status": "N/A",  "detail": "Skipped — no SBD profile attached"},
    {"check": 9, "status": "N/A",  "detail": "Skipped — no SBD profile attached"},
    {"check": 10, "status": "FAIL", "detail": "Protection profile missing SBD reference"}
  ],
  "recommendation": "Attach 'Standard Protection' SBD to 'Inline Standard Protection' profile"
}
```
