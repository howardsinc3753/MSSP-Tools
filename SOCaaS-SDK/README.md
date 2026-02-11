# SOCaaS Python SDK

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Python SDK for Fortinet SOCaaS (Security Operations Center as a Service) API.

> **For Fortinet MSSP Partners**: This SDK provides programmatic access to the SOCaaS platform for automation, integration, and custom tooling.

## Disclaimer
This script is provided for partner troubleshooting and diagnostic purposes only.

NOT an official Fortinet product - Not endorsed, tested, or maintained by Fortinet, Inc.
Use at your own risk - Test in lab environments before production deployment
No warranties - Provided "AS IS" without warranties of any kind
No liability - Neither the author nor Fortinet, Inc. shall be held liable for any damages, outages, or issues resulting from use of this code
By using this script, you agree to validate all outputs independently and assume full responsibility for its operation.

## Features

- **Alerts**: List, get details, update status, IOCs, events, endpoints
- **Alert Polling**: Background monitoring with webhook notifications to ServiceNow, Slack, Teams, PagerDuty
- **Service Requests**: List, create, track support tickets
- **Comments**: Add investigation notes to alerts and SRs
- **Reports**: List and download security reports
- **MSSP Client Management**: Multi-tenant client operations
- **File Downloads**: Download attachments and reports

## Installation

### From Source (Recommended)

```bash
git clone https://github.com/fortinet/socaas-sdk.git
cd socaas-sdk
pip install .
```

### Development Install

```bash
pip install -e ".[dev]"
```

### Manual Dependencies

```bash
pip install requests pyyaml
```

## Quick Start

```python
from socaas import SOCaaSClient

# Create client
client = SOCaaSClient(
    username="your-api-user-id",  # UUID from FortiCloud IAM
    password="your-api-password"
)

# List alerts
alerts = client.list_alerts()
print(f"Found {len(alerts)} alerts")

# Get alert details with IOCs
if alerts:
    alert = client.get_alert(alerts[0]['uuid'])
    print(f"Alert: {alert['name']}")
    print(f"IOCs: {len(alert.get('indicators', []))}")

# List MSSP clients
clients = client.list_clients()
for c in clients:
    print(f"Client: {c['client_name']}")
```

## Authentication

SOCaaS uses OAuth 2.0 Password Grant authentication with FortiCloud IAM.

### Method 1: Direct Credentials

```python
client = SOCaaSClient(
    username="YOUR-API-USER-UUID-FROM-FORTICLOUD-IAM",
    password="your-password"
)
```

### Method 2: Credential File

Create `credentials.yaml`:

```yaml
username: "YOUR-API-USER-UUID-FROM-FORTICLOUD-IAM"
password: "your-password"
```

```python
client = SOCaaSClient.from_credential_file("credentials.yaml")
```

### Method 3: Environment Variables

```bash
export SOCAAS_USERNAME="YOUR-API-USER-UUID-FROM-FORTICLOUD-IAM"
export SOCAAS_PASSWORD="your-password"
```

```python
client = SOCaaSClient.from_env()
```

## API Reference

### Alerts

```python
# List all alerts
alerts = client.list_alerts()

# List with date filter
alerts = client.list_alerts(
    created_date_from="2025-01-01T00:00:00Z",
    created_date_to="2025-12-31T23:59:59Z"
)

# Get alert details (includes IOCs, events, endpoints)
alert = client.get_alert("alert-uuid")

# Update alert status
client.update_alert_status(
    alert_uuid="alert-uuid",
    status="completed",  # or "inprogress"
    closure_notes="Investigation complete, false positive"
)

# Get alerts for specific client (MSSP)
client_alerts = client.get_alerts_by_client("client-uuid")
```

### Service Requests

```python
# List all service requests
srs = client.list_service_requests()

# Get service request details
sr = client.get_service_request("sr-uuid")

# Create service request
new_sr = client.create_service_request(
    title="Whitelist Request",
    request_type="whitelistrequest",
    notes="Please whitelist IP 192.168.1.100"
)
```

Service request types:
- `devicedecommissioning`
- `escalationmatrixupdate`
- `newmonitoringrequest`
- `newreportrequest`
- `portalaccess`
- `servicedecommissioning`
- `serviceenquiry`
- `technicalassitance`
- `whitelistrequest`
- `others`

### Comments

```python
# List comments on alert
comments = client.list_alert_comments("alert-uuid")

# Add comment to alert
client.create_alert_comment(
    alert_uuid="alert-uuid",
    content="Investigated - confirmed malicious"
)
```

> **Note**: The `tag` parameter must be an empty string (default). The SOCaaS API returns `InvalidRequest` for non-empty tag values.
> Service request comments may return HTTP 500 due to an API limitation; alert comments are supported.

Example script:

```bash
python examples/manage_comments.py
```

### Clients (MSSP)

```python
# List managed clients
clients = client.list_clients()
for c in clients:
    print(f"{c['client_name']}: {c['client_uuid']}")
```

### Reports

```python
from socaas import SOCaaSClient
from socaas.files import FileManager

# List reports
reports = client.list_reports()

# Download report
file_mgr = FileManager(client)
file_data = file_mgr.download_report("file-portal-uuid")
file_mgr.save(file_data, "report.pdf")
```

### Alert Polling & Webhooks

Monitor SOCaaS for new alerts and send notifications to external systems.

```bash
# Test with webhook.site
python examples/alert_poller.py --webhook-url https://webhook.site/your-uuid

# ServiceNow integration
python examples/alert_poller.py \
    --webhook-url https://instance.service-now.com/api/now/table/incident \
    --format servicenow \
    --header "Authorization: Basic YOUR-CREDS"

# Continuous polling (every 5 minutes)
python examples/alert_poller.py --webhook-url URL --interval 300
```

Supported destinations:
- **webhook.site** - Testing
- **ServiceNow** - Create incidents
- **Slack** - Channel notifications
- **Microsoft Teams** - Channel cards
- **PagerDuty** - Trigger incidents
- **Custom REST API** - Any endpoint

See [docs/webhook-integration.md](docs/webhook-integration.md) for full setup guides.

## Rate Limits

- **GET endpoints**: 100 requests per minute
- **POST endpoints**: 5 requests per minute

The SDK handles authentication token refresh automatically.

> **Note**: Pagination is not currently implemented. The API returns all results in a single response. For very large datasets, use date filtering.

## Error Handling

Exceptions are defined in `socaas/client.py` and exported from the package:

```python
from socaas import SOCaaSClient, AuthenticationError, APIError, SOCaaSError

try:
    client = SOCaaSClient(username="...", password="...")
    alerts = client.list_alerts()
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
except APIError as e:
    print(f"API error: {e}")
except SOCaaSError as e:
    print(f"SOCaaS error: {e}")  # Base exception
```

## Debug Mode

Enable debug logging:

```python
client = SOCaaSClient(username="...", password="...")
client.debug = True

# Now API calls will print debug info
alerts = client.list_alerts()
# [SOCaaS] Authenticating to https://customerapiauth.fortinet.com/...
# [SOCaaS] GET https://socaas.mss.fortinet.com/socaasAPI/v1/alert
```

## Getting API Credentials

1. Log into [FortiCloud](https://support.fortinet.com)
2. Navigate to **IAM** > **API Users**
3. Create a new API user with **SOCaaS permissions**
4. Note the **User ID** (UUID format) and **Password**

The User ID is in UUID format like: `YOUR-API-USER-UUID-FROM-FORTICLOUD-IAM`

**Store credentials securely using one of these methods:**
- Environment variables (`SOCAAS_USERNAME`, `SOCAAS_PASSWORD`)
- Credential file (`credentials.yaml`) - **never commit this file**
- Secrets manager in production

## Security

> **NEVER commit credentials to version control.**

The `.gitignore` file excludes `credentials.yaml` and `.env` files. Always verify before committing.

## Project Structure

```
socaas-sdk/
  socaas/                    # Main package (flat layout, no src/)
    __init__.py              # Exports: SOCaaSClient, exceptions, managers
    client.py                # SOCaaSClient + exception classes
    alerts.py                # AlertManager
    service_requests.py      # ServiceRequestManager
    clients.py               # ClientManager (MSSP)
    comments.py              # CommentManager
    reports.py               # ReportManager
    files.py                 # FileManager
  docs/
    webhook-integration.md   # ServiceNow, Slack, Teams, PagerDuty setup
  examples/
    alert_poller.py          # Background polling with webhooks
    list_alerts.py           # List alerts example
    get_alert_details.py     # Get alert details example
    list_clients.py          # List MSSP clients example
    create_service_request.py # Create SR example
    manage_comments.py       # Add/list comments on alerts and SRs
  pyproject.toml             # Primary packaging (pip install .)
  requirements.txt           # Dev/test only - use pyproject.toml for install
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

MIT License - See [LICENSE](LICENSE) for details.

## Related Resources

- [FortiCloud Portal](https://support.fortinet.com)
- [SOCaaS Portal](https://socaas.mss.fortinet.com)
- [Fortinet Developer Network](https://fndn.fortinet.net/)
