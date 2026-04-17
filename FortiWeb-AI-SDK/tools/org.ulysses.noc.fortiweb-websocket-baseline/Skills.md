# FortiWeb WebSocket Security Baseline Skills

## Purpose

Protects WebSocket connections used by Socket.IO, native WS, or other real-time frameworks. Without this, FortiWeb may mishandle WebSocket upgrades — breaking real-time features — or miss attacks hidden in WS frames.

## Why This Matters

Once an HTTP request upgrades to WebSocket (`Upgrade: websocket`), it becomes a persistent bidirectional channel. Attackers can hide SQLi, XSS, and command injection in WebSocket frames. Without WebSocket Security:
- FortiWeb might block the upgrade entirely (breaks Socket.IO)
- Attack signatures don't inspect WS frames
- No frame size limits → DoS via massive WS messages

## Architecture

```
Protection Profile
  └─ websocket-security-policy: BP-WebSocket-Protection
        │
        └─ Policy (container)
              └─ rule-list: [BP-WebSocket-Rule]
                    │
                    └─ Rule: BP-WebSocket-Rule
                          ├─ url: ^/.* (or ^/socket.io/)
                          ├─ block-websocket-traffic: disable (allow WS!)
                          ├─ enable-attack-signatures: enable
                          ├─ max-frame-size: 64 KB
                          ├─ max-message-size: 16 MB
                          ├─ allow-plain-text: enable
                          └─ allow-binary-text: enable (Socket.IO needs this)
```

## When to Use

- App uses Socket.IO, WebSocket, or SignalR
- "Real-time features are broken through FortiWeb"
- "Need to inspect WebSocket traffic"

## Actions

| Action | Mode | Purpose |
|--------|------|---------|
| `audit` | READ | Check if WS policy is attached and has rules |
| `apply` | WRITE | Create rule + policy + wire into profile |
| `status` | READ | Quick posture |

## Baseline Settings

| Setting | Baseline | Why |
|---------|----------|-----|
| `block-websocket-traffic` | **disable** | Allow WS (don't break real-time features!) |
| `enable-attack-signatures` | **enable** | Run WAF sigs inside WS frames |
| `max-frame-size` | 64 KB | Typical WS frame ceiling |
| `max-message-size` | 16 MB | Accommodates large fragmented messages |
| `allow-plain-text` | enable | Normal WS text frames |
| `allow-binary-text` | enable | Socket.IO binary protocol |
| `block-extensions` | disable | Allow compression extensions |
| `action` | `alert_deny` | Block + log on violation |

## Critical: Path Tuning

The default `^/.*` regex matches ALL paths. For production, narrow to the actual WS endpoint:

**Socket.IO default:** `^/socket\.io/`
**Custom path:** Match your app's specific WS endpoint

## Important GUI Step

Like JSON Protection, the rule must be **attached to the policy** via GUI:

**Web Protection > API Protection > WebSocket Security > `BP-WebSocket-Protection` > [edit] > Add `BP-WebSocket-Rule` to Rule List**

## Example Usage

```json
{"target_ip": "192.168.209.31", "action": "apply",
 "bp_prefix": "BP", "ws_path": "^/socket\\.io/"}
```

## Related

- `fortiweb-sqli-baseline` — Attack sigs ALSO run on WS frames (via enable-attack-signatures)
- `fortiweb-dos-baseline` — HTTP flood limits apply to WS upgrade requests
