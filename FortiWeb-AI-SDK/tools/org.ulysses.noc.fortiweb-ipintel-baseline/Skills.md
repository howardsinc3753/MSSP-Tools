# FortiWeb IP Intelligence Baseline Skills

## Purpose

Enables FortiGuard IP reputation lookups on FortiWeb. Blocks known-bad source IPs (botnets, phishing hosts, spam sources) at Layer 7 before they can even attempt SQLi/XSS/DoS.

## Architecture

IP Intelligence requires **three** things to work:
1. **Global flag** — master on/off switch
2. **Category actions** — what to do per threat type
3. **Profile toggle** — enable per protection profile

All three must be set. The tool handles all three.

## When to Use

- "Enable IP reputation blocking"
- "Block known-bad IPs"
- "Check if FortiGuard threat intel is active"
- "Are we blocking Tor/botnets?"

## Actions

| Action | Mode | What It Does |
|--------|------|--------------|
| `audit` | READ | Check all 3 layers, report gaps |
| `apply-monitor` | WRITE | Enable everything at **alert only** (safe day-one) |
| `apply-block` | WRITE | Enable, block Botnet/Phishing/Spam, alert-only for Anonymous Proxy/Tor |
| `status` | READ | Quick posture summary |

## Baseline Strategy (2-phase rollout)

**Week 1 — Monitor mode (`apply-monitor`):**
All 6 categories at `alert` only. No blocking. Review logs to establish baseline — see if legitimate traffic triggers categories.

**Week 2+ — Block mode (`apply-block`):**
- **Botnet** → `alert_deny` (never legitimate)
- **Phishing** → `alert_deny` (never legitimate)
- **Spam** → `alert_deny` (never legitimate)
- **Anonymous Proxy** → `alert` (VPN users often legit)
- **Tor** → `alert` (Tor users sometimes legit — journalists, privacy-conscious)
- **Others** → `alert` (generic low-confidence)

## Why Anonymous Proxy/Tor Stay At Alert

Blocking Tor and VPN users can block:
- Corporate users on WFH VPNs
- Journalists / dissidents
- Legitimate privacy-conscious customers
- Users in countries with restrictive internet

Monitor first. If you see zero legitimate traffic from these categories over 2 weeks, promote to block. Otherwise keep at alert and rely on behavior-based blocking (DoS, signatures) to catch actual attacks.

## Example Usage

```json
{"target_ip": "192.168.209.31", "action": "apply-monitor", "profile_name": "BP-SQLi-Protection"}
```

```json
{"target_ip": "192.168.209.31", "action": "audit", "profile_name": "BP-SQLi-Protection"}
```

## Related Tools

- `fortiweb-dos-baseline` — DoS prevention (complementary — IP Intel blocks known bad, DoS catches behavior)
- `fortiweb-sqli-baseline` — SQLi signatures (complementary — Intel blocks source, SQLi blocks payload)
