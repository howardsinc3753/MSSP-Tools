# SOCaaS Webhook Integration Guide

This guide shows how to set up the SOCaaS Alert Poller to send notifications to various destinations.

## Quick Start: Test with webhook.site

The fastest way to test the alert poller:

### Step 1: Get a Test Webhook URL

1. Go to [webhook.site](https://webhook.site)
2. Copy your unique URL (e.g., `https://webhook.site/bf4c54f2-...`)
3. Keep the page open to see incoming webhooks

### Step 2: Set Up Credentials

```bash
cd socaas-sdk
cp credentials.yaml.template credentials.yaml
```

Edit `credentials.yaml`:

```yaml
username: "YOUR-FORTICLOUD-API-USER-ID"   # UUID format
password: "YOUR-API-PASSWORD"
```

### Step 3: Run the Poller

```bash
cd examples

# First run - establishes baseline count
python alert_poller.py --webhook-url https://webhook.site/YOUR-UUID

# Second run - detects new alerts and sends webhook
python alert_poller.py --webhook-url https://webhook.site/YOUR-UUID
```

### Step 4: Verify Webhook Delivery

Check webhook.site - you should see the JSON payload with alert details.

---

## Destination: ServiceNow

Create incidents in ServiceNow when new SOCaaS alerts are detected.

### Prerequisites

- ServiceNow instance with REST API access
- User with `incident_manager` or equivalent role
- Basic auth credentials (or OAuth token)

### Setup

1. **Get your ServiceNow credentials**:
   - Instance URL: `https://YOUR-INSTANCE.service-now.com`
   - Username and password with API access
   - Base64 encode: `echo -n 'username:password' | base64`

2. **Run the poller**:

```bash
python alert_poller.py \
    --webhook-url "https://YOUR-INSTANCE.service-now.com/api/now/table/incident" \
    --format servicenow \
    --header "Authorization: Basic YOUR-BASE64-CREDENTIALS" \
    --header "Accept: application/json"
```

### Field Mapping

| SOCaaS Field | ServiceNow Field | Notes |
|--------------|------------------|-------|
| `alert.name` | `short_description` | Prefixed with `[SOCaaS]` |
| `alert.description` | `description` | Full alert description |
| `alert.severity` | `impact` | Critical=1, High=2, Medium=2, Low=3 |
| `alert.category` | `subcategory` | Alert category |
| `alert.client_name` | `u_client_name` | Custom field (may need to create) |
| `alert.uuid` | `u_socaas_alert_uuid` | Custom field for tracking |

### Custom Field Setup (Optional)

To store SOCaaS-specific data, create custom fields in ServiceNow:

1. Navigate to **System Definition > Dictionary**
2. Create fields on `incident` table:
   - `u_socaas_alert_uuid` (String, 50 chars)
   - `u_client_name` (String, 100 chars)

### Scripted REST API (Advanced)

For full control over field mapping, create a Scripted REST API in ServiceNow:

1. Navigate to **System Web Services > Scripted REST APIs**
2. Create new API with custom resource
3. In the script, transform the SOCaaS payload to your incident format
4. Use the Scripted REST endpoint as your webhook URL

---

## Destination: Slack

Send alert notifications to a Slack channel.

### Prerequisites

- Slack workspace admin access
- Incoming Webhooks app installed

### Setup

1. **Create Incoming Webhook**:
   - Go to [Slack API > Apps](https://api.slack.com/apps)
   - Create new app or select existing
   - Enable **Incoming Webhooks**
   - Click **Add New Webhook to Workspace**
   - Select channel and authorize
   - Copy webhook URL

2. **Run the poller**:

```bash
python alert_poller.py \
    --webhook-url "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXX" \
    --format slack
```

### Sample Slack Message

```
:red_circle: *New SOCaaS Alert*
*Suspicious PowerShell Activity*
Severity: High | Status: Inprogress
Client: Acme Corp
UUID: `abc123-def456-...`
```

### Rich Formatting (Slack Blocks)

For more advanced formatting, modify the `build_slack_payload()` function in `alert_poller.py` to use [Slack Block Kit](https://api.slack.com/block-kit).

---

## Destination: Microsoft Teams

Send alert cards to a Teams channel.

### Prerequisites

- Microsoft Teams admin access
- Ability to create Incoming Webhook connector

### Setup

1. **Create Incoming Webhook**:
   - Open Teams channel
   - Click **...** > **Connectors**
   - Find **Incoming Webhook** and click **Configure**
   - Name it (e.g., "SOCaaS Alerts")
   - Copy webhook URL

2. **Run the poller**:

```bash
python alert_poller.py \
    --webhook-url "https://YOUR-TENANT.webhook.office.com/webhookb2/..." \
    --format teams
```

### Sample Teams Card

The poller sends a MessageCard with:
- Color-coded by severity (Critical=Red, High=Orange, etc.)
- Alert name as title
- Facts table with severity, status, client, category

### Adaptive Cards (Advanced)

For richer formatting, use Power Automate:

1. Create Flow triggered by HTTP request
2. Parse the generic webhook JSON
3. Build Adaptive Card with your desired layout
4. Post to Teams channel

---

## Destination: PagerDuty

Trigger PagerDuty incidents for critical alerts.

### Prerequisites

- PagerDuty account
- Service with Events API v2 integration

### Setup

1. **Create Integration**:
   - In PagerDuty, go to **Services > [Your Service] > Integrations**
   - Add **Events API v2** integration
   - Copy the **Integration Key** (routing key)

2. **Run the poller**:

```bash
python alert_poller.py \
    --webhook-url "https://events.pagerduty.com/v2/enqueue" \
    --format pagerduty \
    --pagerduty-key "YOUR-INTEGRATION-KEY"
```

### Features

- Automatic deduplication using `dedup_key`
- Severity mapping: Critical=critical, High=error, Medium=warning, Low=info
- Client name as component for grouping

---

## Destination: Custom REST API

Send to any REST endpoint.

### Generic JSON Payload

```bash
python alert_poller.py \
    --webhook-url "https://your-api.com/webhooks/socaas" \
    --format generic \
    --header "Authorization: Bearer YOUR-TOKEN" \
    --header "X-Custom-Header: value"
```

### Payload Structure

```json
{
  "event_type": "new_socaas_alert",
  "timestamp": "2025-02-03T14:30:00+00:00",
  "source": "socaas-alert-poller",
  "alert_count": {
    "current": 85,
    "previous": 84,
    "new_alerts": 1
  },
  "alert": {
    "uuid": "abc123-def456-...",
    "id": 12345,
    "name": "Suspicious PowerShell Activity",
    "status": "Inprogress",
    "severity": "High",
    "category": "Malware",
    "client_name": "Acme Corp",
    "created_datetime": "2025-02-03T14:25:00Z",
    "description": "PowerShell executed encoded command...",
    "recommendations": "Isolate endpoint, review logs",
    "ioc_count": 5,
    "sample_iocs": [
      {"type": "hash_sha256", "value": "a1b2c3..."},
      {"type": "ip", "value": "192.168.1.100"}
    ],
    "endpoint_count": 1,
    "hostnames": ["WORKSTATION-01"]
  }
}
```

### Customizing the Payload

Edit the `build_generic_payload()` function in `examples/alert_poller.py` to modify fields.

---

## Continuous Polling

Run the poller continuously with automatic state management.

### Polling Modes

| Mode | Command | Description |
|------|---------|-------------|
| Single check | `python alert_poller.py --webhook-url URL` | Check once, exit |
| 1-minute interval | `--interval 60` | Poll every minute |
| 5-minute interval | `--interval 300` | Poll every 5 minutes |
| Limited polls | `--interval 60 --max-polls 10` | Poll 10 times, then exit |

### State Persistence

The poller stores state in `examples/.alert_poller_state.json`:

```json
{"last_known_count": 84}
```

This allows the poller to detect new alerts even when restarted.

To reset and re-establish baseline:

```bash
python alert_poller.py --reset-state --webhook-url URL
```

### Running as a Service

**Linux (systemd)**:

```ini
# /etc/systemd/system/socaas-poller.service
[Unit]
Description=SOCaaS Alert Poller
After=network.target

[Service]
Type=simple
User=socaas
WorkingDirectory=/opt/socaas-sdk/examples
ExecStart=/usr/bin/python3 alert_poller.py --webhook-url https://your-endpoint.com --interval 300
Restart=always

[Install]
WantedBy=multi-user.target
```

**Windows (Task Scheduler)**:

1. Open Task Scheduler
2. Create Basic Task
3. Trigger: At startup (or schedule)
4. Action: Start a program
   - Program: `python`
   - Arguments: `alert_poller.py --webhook-url https://your-endpoint.com --interval 300`
   - Start in: `C:\path\to\socaas-sdk\examples`

**Docker**:

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY . .
RUN pip install .
CMD ["python", "examples/alert_poller.py", "--webhook-url", "${WEBHOOK_URL}", "--interval", "300"]
```

---

## Troubleshooting

### Common Issues

**"Authentication failed"**
- Verify credentials in `credentials.yaml`
- Ensure API user has SOCaaS permissions in FortiCloud IAM

**"Webhook failed: 401 Unauthorized"**
- Check your destination authentication
- For ServiceNow: verify Basic auth header is correctly base64-encoded

**"Webhook failed: 403 Forbidden"**
- Check destination firewall/security rules
- Verify API permissions

**"No new alerts detected" but alerts exist**
- The poller compares counts, not individual alerts
- Run with `--reset-state` to re-establish baseline

### Debug Mode

Enable verbose output:

```bash
python alert_poller.py --webhook-url URL --debug
```

---

## Rate Limits

- SOCaaS API: 100 GET requests per minute
- Recommended polling interval: 60+ seconds
- Avoid polling more frequently than every 30 seconds

---

## Related Documentation

- [README.md](../README.md) - SDK overview and installation
- [examples/](../examples/) - More usage examples
- [FortiCloud IAM](https://support.fortinet.com) - API credential setup
