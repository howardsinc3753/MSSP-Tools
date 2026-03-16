# SOCaaS API Authentication Guide

## Overview

The SOCaaS API uses OAuth 2.0 for authentication. You need API credentials from FortiCloud to access the API.

## Prerequisites

1. **FortiCloud Account** with SOCaaS service enabled
2. **API User Credentials** (API ID and Password) from FortiCloud

## Getting API Credentials

1. Log into [FortiCloud](https://support.fortinet.com)
2. Navigate to your account settings
3. Generate API credentials for SOCaaS access
4. Note down your:
   - **API User ID** (UUID format: `XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`)
   - **API Password**

## Authentication Flow

```
┌─────────────┐     POST /oauth/token/      ┌──────────────────┐
│   Client    │ ─────────────────────────►  │  FortiCloud Auth │
│             │   username, password,       │                  │
│             │   client_id, grant_type     │                  │
│             │ ◄─────────────────────────  │                  │
│             │   access_token,             │                  │
│             │   refresh_token             │                  │
└─────────────┘                             └──────────────────┘
       │
       │  Authorization: Bearer <access_token>
       ▼
┌──────────────────┐
│   SOCaaS API     │
│   Endpoints      │
└──────────────────┘
```

## Getting an Access Token

**Auth URL:** `https://customerapiauth.fortinet.com/api/v1/oauth/token/`

### Using cURL

```bash
curl -X POST "https://customerapiauth.fortinet.com/api/v1/oauth/token/" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "YOUR_API_USER_ID",
    "password": "YOUR_API_PASSWORD",
    "client_id": "socaas",
    "grant_type": "password"
  }'
```

### Using PowerShell

```powershell
$body = @{
    username   = "YOUR_API_USER_ID"
    password   = "YOUR_API_PASSWORD"
    client_id  = "socaas"
    grant_type = "password"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "https://customerapiauth.fortinet.com/api/v1/oauth/token/" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body

$token = $response.access_token
Write-Host "Access Token: $token"
```

### Using Python

```python
import requests

AUTH_URL = "https://customerapiauth.fortinet.com/api/v1/oauth/token/"

payload = {
    "username": "YOUR_API_USER_ID",
    "password": "YOUR_API_PASSWORD",
    "client_id": "socaas",
    "grant_type": "password"
}

response = requests.post(AUTH_URL, json=payload)
response.raise_for_status()

data = response.json()
access_token = data["access_token"]
refresh_token = data["refresh_token"]
expires_in = data["expires_in"]

print(f"Access Token: {access_token}")
print(f"Expires in: {expires_in} seconds")
```

## Token Response

```json
{
    "access_token": "v4vkjpAOm9685D6M6MxQBBsw03ss9M",
    "expires_in": 36000,
    "token_type": "Bearer",
    "scope": "openid",
    "refresh_token": "CtJcRtF4YeK4poMi94Vew0qjxMrxeb"
}
```

| Field | Description |
|-------|-------------|
| access_token | Bearer token for API requests |
| expires_in | Token lifetime in seconds (default: 36000 = 10 hours) |
| token_type | Always "Bearer" |
| scope | OAuth scope |
| refresh_token | Token for obtaining new access tokens |

## Using the Access Token

Include the token in the `Authorization` header for all API requests:

```
Authorization: Bearer v4vkjpAOm9685D6M6MxQBBsw03ss9M
```

### Example API Request

```bash
curl -X GET "https://socaas.mss.fortinet.com/socaasAPI/v1/alert" \
  -H "Authorization: Bearer v4vkjpAOm9685D6M6MxQBBsw03ss9M"
```

## Refreshing Tokens

When your access token expires, use the refresh token to get a new one without re-entering credentials:

```bash
curl -X POST "https://customerapiauth.fortinet.com/api/v1/oauth/token/" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "socaas",
    "refresh_token": "CtJcRtF4YeK4poMi94Vew0qjxMrxeb",
    "grant_type": "refresh_token"
  }'
```

## Token Management Best Practices

1. **Cache tokens** - Don't request a new token for every API call
2. **Track expiry** - Store `expires_in` and refresh before expiration
3. **Handle 401 errors** - Automatically refresh token on 401 responses
4. **Secure storage** - Never hardcode credentials; use environment variables or secure vaults

### Example Token Manager (Python)

```python
import time
import requests

class TokenManager:
    def __init__(self, username, password, client_id="socaas"):
        self.username = username
        self.password = password
        self.client_id = client_id
        self.auth_url = "https://customerapiauth.fortinet.com/api/v1/oauth/token/"
        self.token = None
        self.refresh_token = None
        self.token_expiry = 0

    def get_token(self):
        """Get valid access token, refreshing if needed."""
        if self._is_token_valid():
            return self.token

        if self.refresh_token:
            try:
                return self._refresh()
            except:
                pass  # Fall back to full auth

        return self._authenticate()

    def _is_token_valid(self):
        """Check if current token is still valid (with 5 min buffer)."""
        return self.token and time.time() < (self.token_expiry - 300)

    def _authenticate(self):
        """Perform full authentication."""
        payload = {
            "username": self.username,
            "password": self.password,
            "client_id": self.client_id,
            "grant_type": "password"
        }
        response = requests.post(self.auth_url, json=payload)
        response.raise_for_status()

        data = response.json()
        self.token = data["access_token"]
        self.refresh_token = data.get("refresh_token")
        self.token_expiry = time.time() + data.get("expires_in", 36000)

        return self.token

    def _refresh(self):
        """Refresh the access token."""
        payload = {
            "client_id": self.client_id,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token"
        }
        response = requests.post(self.auth_url, json=payload)
        response.raise_for_status()

        data = response.json()
        self.token = data["access_token"]
        self.refresh_token = data.get("refresh_token", self.refresh_token)
        self.token_expiry = time.time() + data.get("expires_in", 36000)

        return self.token
```

## Environment Variables

Recommended approach for storing credentials:

**.env file:**
```
SOCAAS_USERNAME=62A1AFE0-0119-46FB-8AC8-9D2D04315BEE
SOCAAS_PASSWORD=your-password-here
SOCAAS_CLIENT_ID=socaas
SOCAAS_BASE_URL=https://socaas.mss.fortinet.com
SOCAAS_AUTH_URL=https://customerapiauth.fortinet.com/api/v1/oauth/token/
```

**Usage in Python:**
```python
import os
from dotenv import load_dotenv

load_dotenv()

username = os.getenv("SOCAAS_USERNAME")
password = os.getenv("SOCAAS_PASSWORD")
```

## Troubleshooting

### "Invalid credentials given"

- Verify API User ID is correct (should be UUID format)
- Confirm password is correct
- Check that your FortiCloud account has SOCaaS API access enabled

### "Token expired"

- Token has exceeded `expires_in` duration
- Use refresh_token to get a new access token
- If refresh fails, perform full authentication

### 403 Forbidden

- Your account may not have permission for the requested resource
- MSSP accounts need proper client association
- Contact Fortinet support to verify permissions
