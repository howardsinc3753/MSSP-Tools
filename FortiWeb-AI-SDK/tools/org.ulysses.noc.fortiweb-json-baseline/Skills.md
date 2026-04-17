# FortiWeb JSON Protection Baseline Skills

## Purpose

Validates JSON request bodies against structural limits and runs WAF attack signatures inside JSON values. Essential for REST APIs — without this, SQLi/XSS hidden in JSON body bypass traditional param-based WAF checks.

## Architecture

```
Protection Profile
  └─ json-validation-policy: BP-JSON-Protection
        │
        └─ Policy: BP-JSON-Protection
              ├─ enable-attack-signatures: enable
              └─ input-rule-list: [BP-JSON-Rule, ...]
                    │
                    └─ Rule: BP-JSON-Rule
                          ├─ request-file: ^/.*  (or /api/*)
                          ├─ json-limits: enable
                          ├─ max depth: 32
                          ├─ max keys: 1000
                          ├─ max body: 10MB
                          └─ action: alert_deny
```

## When to Use

- "Is JSON protection enabled?"
- "Validate API request bodies"
- "Protect REST endpoints"
- "Check JSON depth / size limits"

## Actions

| Action | Mode | Purpose |
|--------|------|---------|
| `audit` | READ | Check all 3 layers (profile, policy, rule) |
| `apply` | WRITE | Create rule + policy + wire into profile |
| `status` | READ | Quick posture |

## Baseline Values

| Limit | Default | Why |
|-------|---------|-----|
| `json-data-size` | 10 MB | Reasonable API body ceiling |
| `object-depth` | 32 | Blocks deeply nested JSON attacks (DoS via parser) |
| `key-number` | 1000 | Total keys per JSON document |
| `key-size` | 1024 | Max length of a single key |
| `value-size` | 10 KB | Max single value size |
| `value-number` | 10000 | Max total values |

## Important GUI Step

The rule must be **attached to the policy** via GUI after creation:

**Web Protection > API Protection > JSON Protection > `BP-JSON-Protection` > [edit] > Add `BP-JSON-Rule` to Input Rule List**

This sub-table linkage isn't reliably settable via REST API.

## Example Usage

```json
{"target_ip": "192.168.209.31", "action": "apply",
 "bp_prefix": "BP", "max_body_kb": 10240, "max_depth": 32}
```

Tuning for specific app:
```json
{"target_ip": "192.168.209.31", "action": "apply",
 "max_body_kb": 51200, "max_depth": 50, "max_keys": 5000}
```

## Related

- `fortiweb-sqli-baseline` — Signatures also run via JSON (complementary)
- Future: `fortiweb-openapi-baseline` — OpenAPI/Swagger enforcement
