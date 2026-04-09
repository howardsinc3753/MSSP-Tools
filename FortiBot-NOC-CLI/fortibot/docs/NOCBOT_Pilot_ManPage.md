# NOC-BOT Pilot Manual

## What is FortiBot NOC-BOT?

NOC-BOT is an AI-powered CLI tool that gives Fortinet NOC engineers a conversational
interface to FortiGate firewall diagnostics. Ask questions in plain English, and NOC-BOT
uses Claude AI to select the right diagnostic tools, run them against your FortiGate, and
analyze the results.

**"I Monitor. And I Know Things."**

---

## Installation

```bash
# From the project directory
pip install -e .

# Or install from the wheel
pip install fortibot-noc
```

### Requirements

- Python 3.9+
- Network access to your FortiGate management interface (HTTPS)
- A FortiGate REST API token (created under System > Administrators)
- An Anthropic API key for AI features (sk-ant-...)
- SSH credentials (optional but recommended for advanced diagnostics)

---

## Quick Start

### Step 1: Install

Download `fortibot-noc.zip`, extract it, then run:

```bash
cd fortibot-noc
pip install .
```

After install, close and reopen your terminal. The `fortibot` command is now
available globally — you can run it from **any directory**.

### Step 2: Set Up Your FortiGate

```bash
fortibot init
```

The wizard walks you through everything:

1. **Claude API key** — Paste your `sk-ant-...` key (get from console.anthropic.com)
2. **FortiGate IP** — Management IP (must be reachable from your laptop)
3. **HTTPS port** — Usually 443 (press Enter for default)
4. **API token** — Your FortiGate REST API token (hidden input)
5. **SSH credentials** — Optional but recommended for advanced diagnostics

The wizard tests every connection as you go. When you see
**"Setup Complete!"**, you're done.

### Step 3: You're Back at Your Prompt — That's Normal!

After `fortibot init` finishes, you'll be back at your regular terminal prompt
(e.g., `PS C:\Users\you>` on Windows or `$` on Mac/Linux).

**This is expected.** NOC-BOT is configured and ready. Now just type commands.

### Step 4: Your First Command

Copy and paste this into your terminal:

```bash
fortibot ask "is this firewall healthy?"
```

NOC-BOT will:
1. Query your FortiGate (CPU, memory, disk, sessions, uptime)
2. Send the data to Claude AI for analysis
3. Print a plain English health report

You'll see tool names printing as they run, then the AI analysis.

### Step 5: Try More Commands

```bash
fortibot health-check                            # Quick health status (no AI)
fortibot ask "are any VPN tunnels down?"          # AI-powered VPN check
fortibot ask "any interface errors?"              # AI interface analysis
fortibot interfaces                               # Raw interface table
fortibot chat                                     # Interactive session (type "exit" to quit)
fortibot trace "10.1.1.5 to 10.2.2.10"           # Reachability diagnosis
fortibot run-all                                  # Full diagnostic report
```

> **Important:** Always wrap questions in quotes:
> `fortibot ask "your question here"`

---

## Available Commands

### Setup & Configuration

| Command | Description |
|---------|-------------|
| `fortibot init` | Interactive setup wizard |
| `fortibot add-device` | Add another FortiGate |
| `fortibot devices` | List configured devices |
| `fortibot remove-device <name>` | Remove a device |
| `fortibot use <name>` | Set the default device |

### AI-Powered

| Command | Description |
|---------|-------------|
| `fortibot ask "<question>"` | Ask NOC-BOT a question |
| `fortibot chat` | Interactive multi-turn chat |
| `fortibot trace "10.1.1.5 to 10.2.2.10"` | AI reachability diagnosis |

### Direct Diagnostics

| Command | Description |
|---------|-------------|
| `fortibot health-check` | CPU, memory, disk, sessions, uptime |
| `fortibot interfaces` | Interface status, errors, counters |
| `fortibot routing` | IPv4 routing table |
| `fortibot vpn` | IPsec VPN tunnel status |
| `fortibot ha` | HA cluster status and sync state |
| `fortibot sdwan` | SD-WAN health checks and SLA (SSH) |
| `fortibot firmware` | Firmware version and upgrade check |
| `fortibot sessions` | Active firewall sessions |
| `fortibot backup [--path /dir]` | Configuration backup |
| `fortibot ssh "<command>"` | Run a CLI command via SSH |
| `fortibot run-all` | Full diagnostic report |

### Other

| Command | Description |
|---------|-------------|
| `fortibot man` | This manual |
| `fortibot --version` | Show version |

All device-specific commands support `--device <name>` to target a specific device
instead of the default.

---

## Example Use Cases

### 1. Morning Health Check

```bash
fortibot health-check
fortibot ask "Give me a morning health summary. Check CPU, memory, interfaces, and VPN tunnels."
```

### 2. Investigate Interface Errors

```bash
fortibot interfaces
fortibot ask "Are there any interfaces with errors? Which ones have the most?"
```

### 3. Diagnose Reachability Issues

When someone reports "Host A can't reach Host B":

```bash
fortibot trace "10.1.1.5 to 10.2.2.10"
```

Or ask NOC-BOT:

```bash
fortibot ask "10.1.1.5 can't reach 10.2.2.10, what's wrong?"
```

NOC-BOT will automatically:
- Check the routing table for the destination
- Check interface status on the egress interface
- Run ping from the FortiGate
- Run traceroute from the FortiGate
- Analyze all results and explain where the break is

### 4. Check VPN Tunnel Status

```bash
fortibot vpn
fortibot ask "Are all VPN tunnels up? Which ones are down?"
```

### 5. Audit Firmware Versions

```bash
fortibot firmware
fortibot ask "Is my firmware current? Are there any patches I should apply?"
```

### 6. SD-WAN SLA Troubleshooting

```bash
fortibot sdwan
fortibot ask "Are any SD-WAN health checks failing? What's the latency on my WAN links?"
```

### 7. Review Security Events

```bash
fortibot ask "Show me recent system events. Any security alerts?"
fortibot ssh "diagnose sys session stat"
```

---

## Tips for Asking Good Questions

NOC-BOT works best when you are specific:

**Good:**
- "What is the CPU utilization and are there any interfaces with errors?"
- "10.1.1.5 can't reach 10.2.2.10 -- diagnose the issue"
- "Are any VPN tunnels down? If so, which remote gateways are affected?"
- "Is the FortiGuard AV subscription about to expire?"

**Less Helpful:**
- "Is everything OK?" (too vague -- be specific about what to check)
- "Fix my firewall" (NOC-BOT diagnoses, it does not make changes)

---

## Troubleshooting

### "No device configured"

Run `fortibot init` to set up your first device.

### "Claude API key not configured"

Run `fortibot init` and enter your Anthropic API key (starts with sk-ant-).

### "Cannot connect to FortiGate"

Check:
1. Is the IP address correct?
2. Is the HTTPS management port correct (default 443)?
3. Can you reach the FortiGate from this machine? (`curl -k https://IP:PORT`)
4. Is the API token valid and not expired?

### "SSH authentication failed"

Check:
1. Is the SSH username correct?
2. Is the SSH password correct?
3. Is SSH enabled on the FortiGate? (`config system admin` > `set ssh-public-key ...`)
4. Is the SSH port correct (default 22)?
5. Is there a firewall rule allowing SSH from your IP?

### "API token rejected (401)"

The API token may be:
- Expired or revoked
- Scoped to a different trusted host
- Missing the required admin profile permissions

Create a new token under **System > Administrators** with at least read access
to the APIs you need.

---

## Configuration

Configuration is stored at `~/.fortibot/config.yaml` with 0600 permissions.

The file contains:
- Claude API key
- Device entries (IP, port, API token, SSH credentials)
- Default device setting

---

## Security Notes

- SSL verification is disabled by default (FortiGate self-signed certs).
- Config file permissions are set to owner-only (0600).
- Destructive SSH commands (reboot, factoryreset, etc.) are blocked.
- API tokens and passwords are stored in plaintext in the config file.
  For production use, consider using a secrets manager.

---

*FortiBot NOC-BOT v0.1.0 -- "I Monitor. And I Know Things."*
