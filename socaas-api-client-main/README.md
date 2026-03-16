# SOCaaS API Client

Python client library for the Fortinet SOCaaS (Security Operations Center as a Service) API.

## Overview

This client provides programmatic access to SOCaaS services including:
- **Alerts** - View and manage security alerts
- **Comments** - Add comments to alerts and service requests
- **Service Requests** - Create and track support/change requests
- **File Downloads** - Download attachments and reports
- **MSSP Client Onboarding** - Onboard new clients (MSSP partners)

## Quick Start

### 1. Setup Environment

```bash
# Clone or copy this repository
cd socaas-api-client-main

# Install dependencies
pip install requests python-dotenv

# Copy environment template
copy .env.example .env    # Windows
cp .env.example .env      # Linux/Mac
```

### 2. Configure Credentials

Edit `.env` with your FortiCloud API credentials:

```env
USERNAME=your-api-user-id
PASSWORD=your-api-password
CLIENT_ID=socaas
BASE_URL=https://socaas.mss.fortinet.com
AUTH_URL=https://customerapiauth.fortinet.com/api/v1/oauth/token/
```

### 3. Test Connection

```bash
python main.py
```

Or use the example scripts:

```bash
python examples/list_alerts.py
python examples/list_service_requests.py
```

## Documentation

| Document | Description |
|----------|-------------|
| [docs/api_reference.md](docs/api_reference.md) | Complete API endpoint reference |
| [docs/authentication.md](docs/authentication.md) | OAuth authentication guide |

## Example Scripts

| Script | Description |
|--------|-------------|
| `examples/list_alerts.py` | List all alerts |
| `examples/get_alert_details.py` | Get details for a specific alert |
| `examples/list_service_requests.py` | List all service requests |
| `examples/create_service_request.py` | Create a new service request |
| `examples/add_comment.py` | Add comment to alert or service request |

## Basic Usage

```python
from SOCaaSClient import SOCaaSClient

client = SOCaaSClient(
    username="your-api-user-id",
    password="your-password",
    client_id="socaas",
    authentication_url="https://customerapiauth.fortinet.com/api/v1/oauth/token/",
    base_url="https://socaas.mss.fortinet.com"
)

# List alerts
alerts = client.request("GET", "/socaasAPI/v1/alert")
print(alerts)

# Get specific alert
alert = client.request("GET", "/socaasAPI/v1/alert/YOUR-ALERT-UUID")

# List service requests
requests = client.request("GET", "/socaasAPI/v1/service-request")
```

## Getting API Credentials

1. Log into [FortiCloud](https://support.fortinet.com)
2. Navigate to account settings
3. Generate API credentials for SOCaaS
4. Your username is the **API User ID** (UUID format)

See [docs/authentication.md](docs/authentication.md) for detailed instructions.

## Rate Limits

| Method | Limit |
|--------|-------|
| GET | 100/min, 1000/hour per IP |
| POST | 5/min, 60/hour per IP |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/socaasAPI/v1/alert` | GET | List alerts |
| `/socaasAPI/v1/alert/{uuid}` | GET | Get alert details |
| `/socaasAPI/v1/comment` | GET/POST | List or create comments |
| `/socaasAPI/v1/file` | GET | Download attachment/report |
| `/socaasAPI/v1/service-request` | GET/POST | List or create service requests |
| `/socaasAPI/v1/service-request/{uuid}` | GET | Get service request details |
| `/socaasAPI/v1/mssp-customer-onboarding` | POST | Create MSSP client onboarding |

See [docs/api_reference.md](docs/api_reference.md) for complete documentation.

## Project Structure

```
socaas-api-client-main/
├── SOCaaSClient.py      # Main client class
├── main.py              # Basic usage example
├── .env.example         # Environment template
├── docs/
│   ├── api_reference.md # API endpoint documentation
│   └── authentication.md # Auth guide
├── examples/
│   ├── list_alerts.py
│   ├── get_alert_details.py
│   ├── list_service_requests.py
│   ├── create_service_request.py
│   └── add_comment.py
└── README.md
```

## Requirements

- Python 3.7+
- `requests`
- `python-dotenv`

## License

Internal use - Fortinet MSSP Partner Tools
