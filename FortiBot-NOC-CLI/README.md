# FortiBot NOC-CLI

**AI-Powered FortiGate Diagnostics for MSSP & Partner Environments**

An agentic CLI tool that lets NOC engineers ask natural language questions about FortiGate firewall health. Claude AI orchestrates 15+ diagnostic tools in real time via REST API and SSH, analyzes the results, and delivers actionable findings.

```
You: "Is my firewall healthy?"

  > Step 1: Running health_check
    CPU: 12% | Mem: 45% | Sessions: 8,234  312ms
  > Step 2: Running interface_status
    24 up, 0 down, 0 with errors  287ms
  > Step 3: Running fortiguard_status
    11 services, all active  198ms

  NOC-BOT Analysis:
  Your FortiGate is in good shape. CPU and memory are well within
  normal range, all 24 interfaces are up with no errors, and all
  FortiGuard subscriptions are active...
```

## Quick Start

### Prerequisites

- Python 3.9+
- A FortiGate with REST API access (API token) -- see [API Token Setup](#fortigate-api-token-setup) below
- An Anthropic API key ([get one here](https://console.anthropic.com/))

### FortiGate API Token Setup

You need a REST API token from your FortiGate before starting. This takes ~2 minutes:

1. Log into FortiGate GUI
2. Go to **System > Administrators**
3. Click **Create New > REST API Admin**
   - **Username:** `fortibot-api`
   - **Admin Profile:** `super_admin_readonly` (or a custom read-only profile)
   - **Trusted Hosts:** Add your workstation's IP address
4. Click **OK** -- the API token is displayed **once**
5. **Copy the token immediately** -- you won't see it again

> **Tip:** If you don't see the REST API Admin option, your FortiGate may need HTTPS API access enabled under **System > Feature Visibility**.

### Install

```bash
cd FortiBot-NOC-CLI
pip install .
```

Or if you prefer installing dependencies manually:

```bash
pip install -r requirements.txt
```

### First Run

```bash
fortibot init
```

The setup wizard walks you through:
1. Enter your Anthropic API key (tested automatically)
2. Enter FortiGate IP, port, and API token (connection verified)
3. Optionally add SSH credentials (needed for SD-WAN, NPU, ping/traceroute)
4. Name your device

### Verify Everything Works

```bash
fortibot doctor
```

This checks Python, packages, API key validity, and FortiGate REST/SSH connectivity for all configured devices. Run this first if something isn't working.

### Start Asking Questions

```bash
# Single question
fortibot ask "Is my firewall healthy?"

# Interactive chat session
fortibot chat

# Direct tool commands
fortibot health-check
fortibot interfaces
fortibot vpn
fortibot routing
fortibot firmware

# Full diagnostic report
fortibot run-all

# Reachability diagnosis
fortibot trace "10.1.1.5 to 10.2.2.10"
```

## What It Does

NOC-BOT uses Claude's tool-use capability to run an **agentic workflow**. When you ask a question, Claude decides which diagnostic tools to run, executes them against your FortiGate in real time, and then analyzes all the data together.

### 15 Diagnostic Tools

| Tool | Method | What It Checks |
|------|--------|----------------|
| `health_check` | REST | CPU, memory, disk, sessions, uptime |
| `interface_status` | REST | Link state, speed, errors, counters |
| `routing_table` | REST | IPv4 routes with optional destination filter |
| `vpn_tunnels` | REST | IPsec tunnel status, traffic counters |
| `ha_status` | REST | HA mode, sync state, peer nodes |
| `firmware_check` | REST | Current version, available upgrades |
| `fortiguard_status` | REST | License expiry, service status |
| `session_table` | REST | Active sessions with filters |
| `config_backup` | REST | Full configuration export |
| `top_bandwidth` | REST | Top traffic consumers by source IP |
| `network_logs` | REST | Traffic and event log queries |
| `sdwan_status` | SSH | SD-WAN member, health-check, service status |
| `npu_offload` | SSH | NPU ASIC detection, offload percentage |
| `reachability_test` | Both | Route lookup + ping + traceroute |
| `ssh_command` | SSH | Any read-only CLI command |

### Safety Guardrails

The SSH tool blocks destructive commands:
- `execute factoryreset`, `execute reboot`, `execute shutdown`
- `config system admin`, `config firewall`, `config vpn`
- `set password`, `diagnose sys kill`, `diagnose debug reset`

## Multi-Device Support

Manage multiple FortiGates and switch between them:

```bash
# Add devices
fortibot add-device --name dc-primary --ip 10.0.1.1 --port 443 --token <token>
fortibot add-device --name branch-047 --ip 10.0.2.1 --port 443 --token <token>

# List configured devices
fortibot devices

# Switch default device
fortibot use branch-047

# Query a specific device
fortibot ask "Check VPN tunnels" --device dc-primary
```

## Configuration

### Config File

Device credentials are stored in `~/.fortibot/config.yaml` with owner-only permissions (0600):

```yaml
claude_api_key: sk-ant-api03-...
default_device: production-fw
devices:
  production-fw:
    ip: 192.168.1.1
    port: 443
    api_token: your-fortigate-api-token
    ssh_user: admin
    ssh_pass: your-ssh-password
    ssh_port: 22
```

### Environment Variables

For CI/CD, automation, or secure environments, use environment variables instead of the config file:

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Claude API key (overrides config file) |
| `FORTIBOT_MODEL` | Claude model (default: `claude-sonnet-4-20250514`) |

```bash
# Example: use environment variables
export ANTHROPIC_API_KEY="sk-ant-api03-..."
export FORTIBOT_MODEL="claude-haiku-4-5-20251001"  # Faster, cheaper
fortibot ask "Quick health check"
```

### Model Options & Cost Expectations

| Model | Speed | Approx. Cost per Query | Best For |
|-------|-------|------------------------|----------|
| `claude-haiku-4-5-20251001` | Fast | ~$0.003 | Quick checks, high volume |
| `claude-sonnet-4-20250514` | Balanced | ~$0.01-0.03 | Default, best value |
| `claude-opus-4-20250514` | Thorough | ~$0.05-0.15 | Complex multi-device diagnosis |

> **Typical monthly cost:** A NOC running ~50 queries/day with Sonnet costs roughly **$15-45/month**. Use Haiku for high-volume automated checks to keep costs under **$5/month**.

## Output Formats

```bash
# Rich terminal UI (default)
fortibot ask "Check health"

# Quiet mode (answer only, no workflow trace)
fortibot ask "Check health" --quiet

# JSON output (for scripting and automation)
fortibot ask "Check health" --json-output

# Pipe to jq for processing
fortibot ask "Check health" --json-output | jq '.workflow[].tool'
```

## Use Cases for Partners

### Morning Health Check
```bash
fortibot ask "Give me a morning health check - CPU, memory, interfaces, VPN tunnels, and FortiGuard status"
```

### Troubleshooting Reachability
```bash
fortibot trace "10.1.1.5 to 10.2.2.10"
# Runs: route lookup, interface check, ping, traceroute
```

### SD-WAN SLA Investigation
```bash
fortibot ask "Show me SD-WAN health check results and any SLA violations"
```

### VPN Tunnel Down
```bash
fortibot ask "Which VPN tunnels are down and what are the remote gateways?"
```

### Firmware Audit
```bash
fortibot ask "What firmware am I running and are there critical patches available?"
```

### Configuration Backup
```bash
fortibot backup --path /backups/
# Saves: hostname_serial_YYYYMMDD_HHMMSS.conf
```

### Full Diagnostic Report
```bash
fortibot run-all
# Runs: health, interfaces, VPN, HA, firmware, FortiGuard
```

## Building on This Framework

This CLI is designed to be extended. Here's how to add your own tools:

### Add a Custom Tool

1. Create a new file in `fortibot/tools/`:

```python
# fortibot/tools/my_custom_check.py
def run(device: dict, **kwargs) -> dict:
    """My custom diagnostic check."""
    base = f"https://{device['ip']}:{device['port']}"
    headers = {"Authorization": f"Bearer {device['api_token']}"}

    # Your REST API call here
    import requests
    resp = requests.get(
        f"{base}/api/v2/monitor/...",
        headers=headers, verify=False, timeout=15
    )

    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}

    data = resp.json().get("results", {})
    return {"success": True, "my_field": data}
```

2. Register it in `fortibot/tool_registry.py`:

```python
from fortibot.tools import my_custom_check

# Add to TOOLS list:
{
    "name": "my_custom_check",
    "description": "Runs my custom diagnostic check on the FortiGate",
    "function": my_custom_check.run,
    "requires_ssh": False,
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}
```

3. Claude will automatically discover and use the new tool when relevant.

### Customize the AI Persona

Edit the `SYSTEM_PROMPT` in `fortibot/ai.py` to change how NOC-BOT behaves:

```python
SYSTEM_PROMPT = """\
You are [YOUR BRAND], an expert AI assistant for Fortinet FortiGate...
When asked about SD-WAN, always check health-checks AND SLA status...
Always recommend opening a TAC case for firmware bugs...
"""
```

## Future Enhancements

These features are on the roadmap for future releases:

- **Scheduled Diagnostics** -- Cron-style health checks (e.g., "run health check every 4 hours") with alerting on threshold violations
- **Device Groups** -- Batch commands across 10+ FortiGates (e.g., `fortibot ask "Check VPN tunnels" --group all-branches`)
- **Report Export** -- Generate PDF/CSV/HTML diagnostic reports for management and compliance
- **Audit Logging** -- Structured logs (JSON/syslog) of who ran what, when, from where -- critical for MSSP compliance
- **Secrets Manager Integration** -- Support for HashiCorp Vault, AWS Secrets Manager, or OS keyring instead of plaintext config file

Contributions welcome! See the [Contributing](#contributing) section below.

## All Commands

| Command | Description |
|---------|-------------|
| `fortibot init` | Interactive setup wizard |
| `fortibot doctor` | Verify config, API keys, and device connectivity |
| `fortibot ask "<question>"` | AI-powered query |
| `fortibot chat` | Interactive AI chat session |
| `fortibot health-check` | CPU, memory, disk, sessions |
| `fortibot interfaces` | Interface status and errors |
| `fortibot routing` | IPv4 routing table |
| `fortibot vpn` | IPsec VPN tunnel status |
| `fortibot ha` | HA cluster status |
| `fortibot sdwan` | SD-WAN health (requires SSH) |
| `fortibot firmware` | Firmware version + upgrades |
| `fortibot sessions` | Active firewall sessions |
| `fortibot backup [--path]` | Configuration backup |
| `fortibot ssh "<cmd>"` | Execute CLI command via SSH |
| `fortibot run-all` | Full diagnostic report |
| `fortibot trace "A to B"` | Reachability diagnosis |
| `fortibot devices` | List configured devices |
| `fortibot use <name>` | Switch default device |
| `fortibot add-device` | Add a FortiGate |
| `fortibot remove-device` | Remove a device |
| `fortibot man` | View the pilot manual |

## Requirements

```
click>=8.0           # CLI framework
rich>=13.0           # Rich terminal UI
anthropic>=0.40.0    # Claude AI SDK
paramiko>=3.0        # SSH client
requests>=2.28       # REST API calls
pyyaml>=6.0          # Config file
cryptography>=41.0   # TLS for SSH
```

## Security Notes

- On Linux/macOS, config file permissions are set to `0600` (owner-only). On Windows, the file inherits your user profile permissions
- SSH passwords and API tokens are stored in plaintext in `~/.fortibot/config.yaml` -- for production environments, use the `ANTHROPIC_API_KEY` env var and consider integrating with your organization's secrets manager
- SSL verification is disabled for FortiGate REST API calls (`verify=False`) because most FortiGates use self-signed certificates
- Destructive SSH commands are blocked by regex-based guardrails
- All diagnostic data is sent to Claude API for analysis -- review Anthropic's data handling policy for your compliance requirements

## Troubleshooting

**First step for any issue:** run `fortibot doctor` -- it tests everything and tells you exactly what's broken.

| Error | Fix |
|-------|-----|
| `No device configured` | Run `fortibot init` |
| `Claude API key not configured` | Run `fortibot init` or set `ANTHROPIC_API_KEY` env var |
| `Connection refused` | Check FortiGate IP/port, firewall rules, API admin trusted hosts |
| `401 Unauthorized` | API token expired or invalid -- regenerate on FortiGate |
| `SSH authentication failed` | Check username/password, verify SSH access is enabled |
| `SD-WAN check failed` | SD-WAN requires SSH credentials -- add via `fortibot init` |
| `NPU check shows N/A` | Model may not have dedicated NPU, or SSH not configured |

## Full Manual

```bash
fortibot man
```

Or read the [Pilot Manual](fortibot/docs/NOCBOT_Pilot_ManPage.md) directly.

## License

MIT License - See [LICENSE](LICENSE)
