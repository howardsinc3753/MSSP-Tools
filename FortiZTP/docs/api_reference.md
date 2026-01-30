# FortiZTP API Reference

## FortiZTP API Overview

The FortiZTP API allows programmatic management of Zero Touch Provisioning for Fortinet devices.

**Base URL:** `https://fortiztp.forticloud.com/public/api/v2`

**Authentication:** OAuth 2.0 via FortiCloud IAM

## Authentication

### Getting an Access Token

```http
POST https://customerapiauth.fortinet.com/api/v1/oauth/token/
Content-Type: application/json

{
    "username": "YOUR-API-USER-ID",
    "password": "YOUR-API-PASSWORD",
    "client_id": "fortiztp",
    "grant_type": "password"
}
```

**Response:**
```json
{
    "access_token": "eyJ...",
    "token_type": "Bearer",
    "expires_in": 3600
}
```

### Using the Token

Include the token in all API requests:

```http
Authorization: Bearer eyJ...
```

---

## Devices API

### List All Devices

```http
GET /devices
```

**Response:**
```json
{
    "devices": [
        {
            "deviceSN": "FGT60F1234567890",
            "deviceType": "FortiGate",
            "platform": "FGT60F",
            "provisionStatus": "provisioned",
            "provisionTarget": "FortiManager",
            "fortiManagerOid": 123,
            "scriptOid": 456
        }
    ]
}
```

### Get Device Status

```http
GET /devices/{deviceSN}
```

### Provision Device

```http
PUT /devices/{deviceSN}
Content-Type: application/json

{
    "deviceType": "FortiGate",
    "provisionStatus": "provisioned",
    "provisionTarget": "FortiManager",
    "fortiManagerOid": 123,
    "externalControllerIp": "192.168.1.100",
    "scriptOid": 456
}
```

**Required Fields:**
- `deviceType`: FortiGate, FortiAP, FortiSwitch, FortiExtender
- `provisionStatus`: provisioned, unprovisioned

**Optional Fields:**
- `provisionTarget`: FortiManager, FortiGateCloud, FortiEdgeCloud, ExternalController
- `region`: FortiCloud region
- `fortiManagerOid`: FortiManager OID
- `scriptOid`: Bootstrap script OID
- `useDefaultScript`: boolean
- `externalControllerSn`: External controller serial
- `externalControllerIp`: External controller IP
- `firmwareProfile`: Firmware profile name

---

## Scripts API

### List Scripts

```http
GET /setting/scripts
```

**Response:**
```json
{
    "data": [
        {
            "oid": 456,
            "name": "Branch-Bootstrap",
            "updateTime": 1234567890000
        }
    ]
}
```

### Get Script Content

```http
GET /setting/scripts/{oid}/content
```

**Response:**
```json
{
    "content": "config system global\n    set hostname \"FGT\"\nend"
}
```

### Create Script

```http
POST /setting/scripts
Content-Type: application/json

{
    "name": "New-Script"
}
```

**Response:**
```json
{
    "oid": 789
}
```

### Upload Script Content

```http
PUT /setting/scripts/{oid}/content
Content-Type: application/json

{
    "content": "config system global\n    set hostname \"FGT\"\nend"
}
```

### Delete Script

```http
DELETE /setting/scripts/{oid}
```

---

## FortiManagers API

### List FortiManagers

```http
GET /setting/fortimanagers
```

**Response:**
```json
{
    "fortiManagers": [
        {
            "oid": 123,
            "sn": "FMG-VM1234567890",
            "ip": "192.168.1.100",
            "scriptOid": 456,
            "updateTime": 1234567890000
        }
    ]
}
```

---

## Error Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 204 | No Content (Success) |
| 400 | Bad Request - Check required fields |
| 401 | Unauthorized - Invalid or expired token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Device or resource doesn't exist |
| 500 | Server Error |

---

## Rate Limits

The FortiZTP API has rate limits. If you receive 429 responses, implement exponential backoff.

Recommended:
- Max 10 requests/second
- Max 1000 requests/hour

---

## SDK Usage

See the main README.md for Python SDK usage examples.
