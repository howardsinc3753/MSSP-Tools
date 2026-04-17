# FortiWeb DoS Prevention Baseline Skills

## Purpose

Audit and enforce DoS prevention best-practice on FortiWeb 8.0+. Protects against HTTP/Layer4 flood attacks with production-safe thresholds that block attackers without impacting legitimate users.

## FortiWeb DoS Architecture

```
Application-Layer DoS Prevention Policy
  ├── HTTP Connection Flood Rule      (concurrent HTTP connections per IP)
  ├── HTTP Request Flood Rule         (requests per session — with bot confirmation)
  ├── Layer 4 Access Limit Rule       (new L4 connections per IP per second)
  ├── Layer 4 Connection Flood Rule   (total concurrent L4 connections per IP)
  └── Layer 3 Fragment Protection     (IP fragment reassembly attacks)
```

The prevention policy is attached to the protection profile via `application-layer-dos-prevention`.

## When to Use This Tool

**Use this tool when the user asks:**
- "Check DoS protection on FortiWeb"
- "Are flood protections enabled?"
- "Set up DDoS best practices"
- "What are the connection thresholds?"
- "Is Layer 4 protection on?"
- "Review rate limiting config"

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `target_ip` | string | Yes | - | FortiWeb management IP |
| `action` | string | Yes | - | `audit`, `apply`, or `status` |
| `profile_name` | string | No | Inline Standard Protection | Profile to audit |
| `bp_prefix` | string | No | BP | Prefix for created objects |

## Baseline Thresholds

| Rule | Setting | Baseline | Predefined Default | Why |
|------|---------|----------|-------------------|-----|
| HTTP Connection Flood | threshold | **500** | 100 | 100 too low for production — blocks legitimate users behind NAT |
| HTTP Connection Flood | action | **alert_deny** | alert_deny | Block + log |
| HTTP Request Flood | session limit | **1000** | 500 | API apps need higher limits (SPAs make many requests) |
| HTTP Request Flood | action | **block-period** | block-period | Temp ban (not permanent deny) |
| HTTP Request Flood | bot-confirmation | **enable** | disable | Challenge suspicious clients with CAPTCHA first |
| HTTP Request Flood | bot-recognition | **captcha** | disabled | Human verification before blocking |
| L4 Access Limit | standalone IP | **1000** | 500 | Per-IP new connection rate |
| L4 Access Limit | shared IP | **2000** | 1000 | Higher for NAT/shared IPs |
| L4 Connection Flood | threshold | **500** | 255 | Total concurrent connections per IP |
| L3 Fragment | protection | **enable** | disable | Fragment reassembly attacks |
| All rules | block-period | **600s** | 0-600 | 10 min temporary ban |
| All rules | severity | **High** | High | Proper log classification |

### Why Higher Thresholds Than Defaults?

The predefined defaults (100 connections, 500 requests) are aggressive. In production:
- **SPA/React apps** make 50+ concurrent API calls on page load
- **NAT/shared IPs** aggregate many users behind one IP
- **WebSocket** connections are long-lived (Socket.IO)
- **API clients** may burst requests legitimately

Setting thresholds too low causes false positives — blocking real users is worse than letting some attack traffic through. Start higher, tune down based on attack log data.

## Actions

### `audit` — Read-only check

Checks:
1. DoS prevention policy attached to protection profile
2. HTTP session-based prevention enabled
3. Layer 4 prevention enabled
4. Layer 3 fragment protection enabled
5. Each rule's thresholds vs baseline
6. Actions set to block (not just alert)
7. Thresholds not below minimum safe values

### `apply` — Create hardened configuration

Creates 5 objects:
1. `{prefix}-ConnFlood` — HTTP connection flood rule
2. `{prefix}-ReqFlood` — HTTP request flood rule (with bot confirmation)
3. `{prefix}-L4Access` — Layer 4 access limit rule
4. `{prefix}-L4ConnFlood` — Layer 4 connection flood rule
5. `{prefix}-DoS-Prevention` — Prevention policy wiring all 4 rules

Auto-wires into `BP-SQLi-Protection` if it exists.

### `status` — Quick posture

Returns GOOD/PARTIAL/WEAK plus blocked IP count.

## Example Usage

### Audit
```json
{"target_ip": "192.168.209.31", "action": "audit", "profile_name": "BP-SQLi-Protection"}
```

### Apply
```json
{"target_ip": "192.168.209.31", "action": "apply", "bp_prefix": "BP"}
```

### Status
```json
{"target_ip": "192.168.209.31", "action": "status"}
```

## Related Tools

- `org.ulysses.noc.fortiweb-sqli-baseline` — SQL injection baseline
- `org.ulysses.noc.fortiweb-cookie-baseline` — Cookie security baseline
- `org.ulysses.noc.fortiweb-tls-baseline` — TLS/cipher hardening
