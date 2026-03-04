# FortiGate CLI Execute - Skills Guide

## Tool Identity
- **Canonical ID:** `org.ulysses.noc.fortigate-cli-execute/1.0.0`
- **Domain:** noc
- **Intent:** provision
- **Vendor:** fortinet

## When to Use This Tool

### Primary Use Cases

1. **Apply FortiFlex License** - Device is newly provisioned, no API user yet
2. **Initial Device Configuration** - Configure interfaces, routes before API setup
3. **Set Admin Password** - First-time login password configuration
4. **Execute Commands** - Any CLI command not supported by REST API

### vs. fortigate-ssh Tool

| Feature | fortigate-cli-execute | fortigate-ssh |
|---------|----------------------|---------------|
| Auth Method | Password | SSH Key |
| Command Types | Read + Write | Read-only |
| Use Case | Initial setup | Diagnostics |
| Config Blocks | Yes | No |
| Execute Commands | Yes | No |

**Use this tool when:**
- Device has no API user configured yet
- Need to run `execute vm-license`
- Need to run `config system interface` blocks
- fortigate-ssh returns "Command not allowed"

**Use fortigate-ssh when:**
- Device is already onboarded with SSH keys
- Running diagnostic commands (get, diagnose, show)
- Need read-only access

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `target_ip` | string | Yes | - | FortiGate management IP |
| `commands` | array | Yes | - | List of CLI commands to execute |
| `username` | string | No | "admin" | SSH username |
| `password` | string | No | - | SSH password |
| `ssh_port` | integer | No | 22 | SSH port |
| `timeout` | integer | No | 30 | Command timeout (seconds) |
| `use_shell` | boolean | No | true | Use interactive shell |
| `interactive_responses` | object | No | {} | Prompt → response map |

## Example Usage

### Apply FortiFlex License

```json
{
  "target_ip": "10.0.0.40",
  "username": "admin",
  "password": "FG@dm!n2026!",
  "commands": [
    "execute vm-license FA2EA590BC6F885E05F1"
  ],
  "interactive_responses": {
    "(y/n)": "y"
  }
}
```

### Configure Interface

```json
{
  "target_ip": "10.0.0.40",
  "username": "admin",
  "password": "FG@dm!n2026!",
  "commands": [
    "config system interface",
    "edit port1",
    "set mode static",
    "set ip 10.0.0.40 255.255.255.0",
    "set allowaccess ping https ssh http",
    "next",
    "end"
  ],
  "interactive_responses": {
    "(y/n)": "y"
  }
}
```

### Configure Static Route

```json
{
  "target_ip": "10.0.0.40",
  "username": "admin",
  "password": "admin",
  "commands": [
    "config router static",
    "edit 1",
    "set gateway 10.0.0.62",
    "set device port1",
    "next",
    "end"
  ]
}
```

### Configure BGP

```json
{
  "target_ip": "10.0.0.40",
  "username": "admin",
  "password": "FG@dm!n2026!",
  "commands": [
    "config router bgp",
    "set as 65000",
    "set router-id 172.16.0.4",
    "config neighbor",
    "edit 172.16.255.252",
    "set remote-as 65000",
    "set update-source Spoke_Lo",
    "next",
    "end",
    "config network",
    "edit 1",
    "set prefix 172.16.0.4 255.255.255.255",
    "next",
    "end",
    "end"
  ]
}
```

### Set Hostname

```json
{
  "target_ip": "10.0.0.40",
  "username": "admin",
  "password": "admin",
  "commands": [
    "config system global",
    "set hostname FG-Spoke-04",
    "end"
  ]
}
```

## Response Format

### Success

```json
{
  "success": true,
  "target_ip": "10.0.0.40",
  "commands_executed": 3,
  "results": [
    {
      "command": "config system interface",
      "output": "FG-Spoke-04 (interface) #",
      "success": true
    },
    {
      "command": "edit port1",
      "output": "FG-Spoke-04 (port1) #",
      "success": true
    },
    {
      "command": "end",
      "output": "FG-Spoke-04 #",
      "success": true
    }
  ]
}
```

### Error

```json
{
  "success": false,
  "target_ip": "10.0.0.40",
  "error": "Authentication failed for admin@10.0.0.40"
}
```

## Interactive Prompts

FortiGate CLI may prompt for confirmation. Use `interactive_responses` to auto-answer:

| Prompt | Common Response | Use Case |
|--------|-----------------|----------|
| `(y/n)` | `y` | Interface change, license apply, reboot |
| `Do you want to continue?` | `y` | Destructive operations |
| `New Password:` | `newpass123` | First-time password change |

## Credential Loading

The tool attempts to load credentials in this order:

1. **Parameters** - `password` provided directly
2. **Config file** - `~/.config/mcp/fortigate_credentials.yaml`
3. **Fallback path** - `C:/ProgramData/Ulysses/config/fortigate_credentials.yaml`

## Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Authentication failed` | Wrong password | Verify credentials |
| `Connection refused` | SSH not enabled | Enable SSH on management interface |
| `Connection timeout` | Network issue | Check routing to target |
| `Command syntax error` | Invalid CLI command | Check FortiOS CLI syntax |

## Security Considerations

- This tool executes **write commands** - use with caution
- Passwords are transmitted over SSH (encrypted)
- Consider using fortigate-onboard to create API user for subsequent operations
- Avoid storing passwords in plain text

## Related Tools

- `fortigate-ssh` - Read-only SSH commands (uses key auth)
- `fortigate-onboard` - Create API user and register device
- `fortigate-api-token-create` - Create API token via session auth

## Workflow Integration

Typical use in SD-WAN provisioning:

```
1. kvm-fortios-provision     → Create VM
2. fortigate-cli-execute     → Apply license, configure IP
3. fortigate-onboard         → Create API user
4. fortigate-sdwan-spoke-template → Deploy SD-WAN config
```
