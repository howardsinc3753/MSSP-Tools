# FortiGate SSH Skills

## How to Call

Use this tool when:
- User needs to run CLI diagnostic commands on FortiGate
- REST API doesn't provide the needed information
- User needs real-time CLI output (sniffer, debug, etc.)
- Troubleshooting requires CLI-only commands

**Example prompts:**
- "Run get system status on the firewall"
- "Show routing table via SSH"
- "Capture packets on port1"
- "Check session table on 192.168.1.1"
- "Run diagnose sys top on the FortiGate"

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `target_ip` | string | Yes | FortiGate management IP address |
| `command` | string | Yes | CLI command to execute (must be allowed) |
| `provision_user` | boolean | No | Auto-provision tron-cli user (default: true) |
| `trusthost` | string | No | Allowed source network "IP NETMASK" (default: 0.0.0.0 0.0.0.0) |
| `ssh_port` | integer | No | SSH port (default: 22) |
| `timeout` | integer | No | Timeout in seconds (default: 30) |
| `verify_ssl` | boolean | No | Verify SSL for REST API (default: false) |

## Allowed Commands

For security, only these command patterns are allowed:

### Get Commands
- `get system status`
- `get system performance status`
- `get system interface [name]`
- `get router info routing-table all`
- `get router info routing-table details <dest>`
- `get system arp`
- `get system session list`
- `get system session status`
- `get vpn ipsec tunnel summary`
- `get vpn ssl monitor`
- `get firewall policy`
- `get log memory filter`

### Diagnose Commands (Read-Only)
- `diagnose sys session stat`
- `diagnose sys session list`
- `diagnose netlink interface list`
- `diagnose ip arp list`
- `diagnose hardware deviceinfo nic <interface>`
- `diagnose debug crashlog read`
- `diagnose sys top [interval]`
- `diagnose sniffer packet <interface> <filter> <count> [time]`

### Execute Commands (Read-Only)
- `execute ping <host>`
- `execute ping-options <options>`
- `execute traceroute <host>`
- `execute telnet <host> <port>`
- `execute ssh <host>`

## How It Works

1. **Key Management**: Tool generates RSA-4096 keypair at `~/.config/mcp/keys/` on first use
2. **User Provisioning**: Auto-creates `tron-cli` admin user on FortiGate via REST API
3. **SSH Connection**: Connects with public key authentication (no passwords)
4. **Command Execution**: Runs allowed commands and returns output

## First-Time Setup

On first execution:
1. RSA-4096 keypair is generated automatically
2. `tron-cli` user is created on FortiGate with the public key
3. SSH connection is established

Subsequent calls reuse the existing key and user.

## Good Use Cases

- "Get system status on 192.168.1.1"
- "Run diagnose sniffer packet port1 'host 10.0.0.1' 10"
- "Check VPN tunnel status via CLI"
- "Ping 8.8.8.8 from the FortiGate"
- "Show active sessions on the firewall"

## Bad Use Cases

- Configuration changes (blocked by allowlist)
- Commands requiring interactive input
- Long-running debug commands (use timeout parameter)
- Commands not in the allowlist (will be blocked)

## Example

**User:** Check system status on FortiGate 10.0.0.62

**Tool Call:**
```python
fortigate_ssh(
    target_ip="10.0.0.62",
    command="get system status"
)
```

**Response:**
```json
{
  "success": true,
  "target_ip": "10.0.0.62",
  "command": "get system status",
  "output": "Version: FortiGate-100F v7.4.1...",
  "exit_status": 0,
  "ssh_user": "tron-cli",
  "user_provisioned": false,
  "key_path": "/home/user/.config/mcp/keys/tron_cli_rsa"
}
```

## Error Handling

| Error | Meaning | Suggestion |
|-------|---------|------------|
| `Command not allowed` | Command blocked by allowlist | Use an allowed command |
| `SSH authentication failed` | Key mismatch | Run with provision_user=true |
| `No API credentials` | Can't provision user | Configure fortigate_credentials.yaml |
| `Connection timeout` | Network issue | Check connectivity, increase timeout |
| `paramiko not installed` | Missing dependency | Run: pip install paramiko |
| `cryptography not installed` | Missing dependency | Run: pip install cryptography |

## Security Notes

- **No passwords stored**: Uses RSA-4096 public key authentication
- **Command allowlist**: Only read-only diagnostic commands permitted
- **Auto-provisioning**: Creates dedicated `tron-cli` user (not shared credentials)
- **Trusthost restriction**: Limit SSH source to specific networks

## Key Storage

Keys are stored at:
- Private key: `~/.config/mcp/keys/tron_cli_rsa`
- Public key: `~/.config/mcp/keys/tron_cli_rsa.pub`

Directory permissions: 700 (Unix only)
Private key permissions: 600 (Unix only)

## Prerequisites

1. **Python packages**: paramiko, cryptography, pyyaml
2. **FortiGate credentials**: API token in `~/.config/mcp/fortigate_credentials.yaml`
3. **Network access**: HTTPS (443) for provisioning, SSH (22) for commands

## Related Tools

- `fortigate-health-check` - Quick health metrics via REST API
- `fortigate-interface-status` - Interface details via REST API
- `fortigate-routing-table` - Routing via REST API
- `fortigate-session-table` - Session table via REST API
