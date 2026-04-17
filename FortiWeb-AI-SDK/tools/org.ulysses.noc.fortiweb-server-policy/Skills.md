# FortiWeb Server Policy Builder Skills

## Purpose

Creates the full server policy stack on FortiWeb — the keystone that activates all your baseline security controls for actual traffic inspection. Without a server policy, all protection profile settings are dormant.

## Architecture

```
Client traffic
  │
  ▼
Virtual Server (listens on VIP:port)
  │
  ├─ TLS termination (uses Cipher Group)
  │
  ├─ Traffic inspection (uses Web Protection Profile)
  │     │
  │     ├─ Signatures + SBD + Cookie + DoS + all baseline controls
  │     │
  │     └─ allow → continue
  │
  ▼
Server Pool (load balance backend members)
  │
  ▼
Backend Server (Rocky Linux app)
```

## Dependency Stack

| Order | Object | Purpose |
|-------|--------|---------|
| 1 | **VIP** | The IPv4 address FortiWeb listens on |
| 2 | **Virtual Server** | Binds one or more VIPs |
| 3 | **Server Pool** | Contains backend server members |
| 4 | **Backend Member (pserver)** | Actual Rocky Linux IP:port |
| 5 | **Server Policy** | Ties VServer + Pool + Protection Profile + TLS together |

## When to Use

- "Create a FortiWeb server policy"
- "Deploy FortiWeb in front of an app"
- "Wire the protection profile to actual traffic"
- "Set up reverse proxy to my Rocky Linux server"
- "Audit existing server policies"

## Actions

| Action | Mode | Purpose |
|--------|------|---------|
| `audit` | READ | Check existing policies for best practice (TLS, profile attached, monitor mode, etc.) |
| `apply` | WRITE | Create full stack (VIP + VServer + Pool + Policy) |
| `status` | READ | List all server policies and their wiring |
| `delete` | WRITE | Remove policy + all dependencies (reverse order) |

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `target_ip` | string | Yes | - | FortiWeb management IP |
| `action` | string | Yes | - | audit/apply/status/delete |
| `policy_name` | string | No | BP-WebApp-Policy | Server policy name |
| `vip_address` | string | For apply | - | FortiWeb listening IP (e.g., 192.168.209.100) |
| `vip_interface` | string | No | port1 | FortiWeb interface hosting the VIP |
| `backend_ip` | string | For apply | - | Rocky Linux app server IP |
| `backend_port` | integer | No | 80 | Backend server port |
| `https_enabled` | boolean | No | false | Enable HTTPS on FortiWeb side |
| `certificate_name` | string | If HTTPS | - | FortiWeb local certificate name |
| `cipher_group` | string | No | - | Cipher group (e.g., BP-TLS-Hardened) |
| `protection_profile` | string | No | BP-SQLi-Protection | Inline protection profile |
| `bp_prefix` | string | No | BP | Prefix for created objects |

## Example Usage

### Deploy HTTP reverse proxy (initial testing)
```json
{
  "target_ip": "192.168.209.31",
  "action": "apply",
  "vip_address": "192.168.209.100",
  "backend_ip": "192.168.209.50",
  "backend_port": 3000
}
```

Creates: BP-VIP + BP-VServer + BP-Pool + BP-WebApp-Policy
All baseline controls active on HTTP:80

### Deploy HTTPS with TLS hardening (production)
```json
{
  "target_ip": "192.168.209.31",
  "action": "apply",
  "vip_address": "192.168.209.100",
  "backend_ip": "192.168.209.50",
  "backend_port": 3000,
  "https_enabled": true,
  "certificate_name": "thrive-cert",
  "cipher_group": "BP-TLS-Hardened"
}
```

Creates same stack but with:
- HTTPS listener on :443
- HTTP→HTTPS redirect
- TLS 1.2+1.3 only
- BP-TLS-Hardened cipher group
- SSL renegotiation blocked

### Audit existing policies
```json
{"target_ip": "192.168.209.31", "action": "audit"}
```

Checks:
- Protection profile attached
- Not in monitor mode (monitor mode = log only, no blocking)
- Using cipher group (vs inline settings)
- TLS 1.0/1.1 disabled
- SSL renegotiation disabled

### Status of all policies
```json
{"target_ip": "192.168.209.31", "action": "status"}
```

### Delete a deployed policy
```json
{"target_ip": "192.168.209.31", "action": "delete", "bp_prefix": "BP"}
```
Deletes in reverse dependency order: policy → pool → vserver → vip

## Manual GUI Steps After Apply

Due to FortiWeb REST API sub-table limitations, two linkages need GUI completion:

1. **Server Objects > Virtual Server > [VServer name] > Add VIP**
   - Select the created VIP from the dropdown

2. **Server Objects > Server Pool > [Pool name] > Add Member**
   - Confirm backend IP and port
   - Set status: enable, weight: 1

After these two GUI actions, traffic inspection is live.

## Preflight Checks (tool validates before creating)

- `protection_profile` must exist (run baseline tools first)
- `vip_interface` must be a valid FortiWeb interface
- Object names don't already exist
- If HTTPS, certificate is specified

## Related Tools

- `fortiweb-sqli-baseline` + all baseline tools — **must run first** to create the protection profile
- `fortiweb-tls-baseline` — creates cipher groups referenced here
- `fortiweb-api-token` — API access setup
