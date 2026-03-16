# SOCaaS API Reference

## Overview

The SOCaaS (Security Operations Center as a Service) API provides programmatic access to Fortinet's managed security services platform. This API enables MSSP partners and customers to integrate SOCaaS capabilities into their workflows.

**Base URL:** `https://socaas.mss.fortinet.com`
**API Version:** v1
**Resource Base:** `/socaasAPI/v1/`

## Rate Limits

| Method | Limit | Window |
|--------|-------|--------|
| GET | 100 requests | per minute per IP |
| GET | 1,000 requests | per hour per IP |
| POST | 5 requests | per minute per IP |
| POST | 60 requests | per hour per IP |

---

## Authentication

All API requests require OAuth 2.0 Bearer token authentication.

### Get OAuth Token

**Endpoint:** `POST https://customerapiauth.fortinet.com/api/v1/oauth/token/`

**Request Body:**
```json
{
    "username": "<apiId value>",
    "password": "<password value>",
    "client_id": "socaas",
    "grant_type": "password"
}
```

**Response:**
```json
{
    "access_token": "v4vkjpAOm9685D6M6MxQBBsw03ss9M",
    "expires_in": 36000,
    "token_type": "Bearer",
    "scope": "openid",
    "refresh_token": "CtJcRtF4YeK4poMi94Vew0qjxMrxeb"
}
```

**Notes:**
- Token expires after `expires_in` seconds (default: 36000 = 10 hours)
- Use `refresh_token` for token renewal without re-authentication
- Include token in all subsequent requests: `Authorization: Bearer <access_token>`

### Refresh Token

**Endpoint:** `POST https://customerapiauth.fortinet.com/api/v1/oauth/token/`

**Request Body:**
```json
{
    "client_id": "socaas",
    "refresh_token": "<refresh_token>",
    "grant_type": "refresh_token"
}
```

---

## Alerts

### List Alerts

**Endpoint:** `GET /socaasAPI/v1/alert`

Retrieves alert list. Returns alerts where:
- Status is NOT: new, investigating, false positive, closed immature
- `escalated_to_incident` = yes
- SLA = missed or met

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| alert_id | integer | No | Filter by specific Alert ID (e.g., 62691) |
| created_date_from | string (RFC3339) | No | Filter alerts created from this date (e.g., `2025-10-01T00:00:00Z`) |
| created_date_to | string (RFC3339) | No | Filter alerts created up to this date (e.g., `2025-11-01T00:00:00Z`) |

**Example:**
```
GET /socaasAPI/v1/alert?created_date_from=2025-10-01T00:00:00Z&created_date_to=2025-11-01T00:00:00Z
```

**Response:**
```json
{
    "result": {
        "status": 0,
        "errorArr": [],
        "data": [
            {
                "uuid": "3a90b295-c110-4333-a361-469789cb5b16",
                "id": 43871,
                "name": "open api test 0003",
                "severity": "Medium",
                "type": "",
                "status": "Confirmed",
                "sla": "Met",
                "description": "open api test 0003",
                "closure_notes": "",
                "analysis_recommendation": "",
                "escalation_path": "",
                "affected_endpoint": "",
                "client_uuid": "b25a02ee-8423-42ec-ae15-5ee29ffaf910",
                "client_name": "fc-socaas-04@master.com",
                "fc_account_id": 1692344,
                "fc_client_name": "",
                "created_date": "1970-01-01T00:00:00Z",
                "modified_date": "2024-02-28T00:22:32.723408Z",
                "self_fc_account_id": 1692344,
                "mssp_fc_account_id": 1692344
            }
        ]
    }
}
```

**Alert List Fields:**

| Field | Type | Description |
|-------|------|-------------|
| uuid | string | Unique identifier for the alert |
| id | integer | Numeric alert ID |
| name | string | Alert title/name |
| severity | string | Severity level (Low, Medium, High, Critical) |
| status | string | Current status (Confirmed, InProgress, Completed, etc.) |
| sla | string | SLA status (Met, Missed) |
| type | string | Alert type |
| description | string | Detailed description |
| closure_notes | string | Notes added when closing |
| analysis_recommendation | string | SOC analyst recommendations |
| escalation_path | string | Escalation contact path |
| affected_endpoint | string | Affected system/endpoint |
| client_uuid | string | Client UUID |
| client_name | string | Client name |
| fc_account_id | integer | FortiCloud account ID |
| fc_client_name | string | FortiCloud client name |
| self_fc_account_id | integer | Self FortiCloud account ID |
| mssp_fc_account_id | integer | MSSP FortiCloud account ID |
| created_date | string | ISO 8601 creation timestamp |
| modified_date | string | ISO 8601 last modified timestamp |

---

### Get Alert Details

**Endpoint:** `GET /socaasAPI/v1/alert/{alertuuid}`

Returns detailed information for a specific alert including related alerts, assets, attachments, endpoints, events, forensic analysis, and indicators.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| alertuuid | string (UUID) | Yes | Alert UUID |

**Response:**
```json
{
    "result": {
        "status": 0,
        "errorArr": [],
        "data": {
            "uuid": "3a90b295-c110-4333-a361-469789cb5b16",
            "id": 43871,
            "name": "open api test 0003",
            "severity": "Medium",
            "status": "Confirmed",
            "sla": "Met",
            "type": "",
            "description": "<p>open api test 0003</p>",
            "closure_notes": "",
            "analysis_recommendation": "",
            "escalation_path": "",
            "affected_endpoint": "",
            "detected_date": "2024-02-28T00:00:00Z",
            "escalation_date": "2024-02-28T00:22:32Z",
            "created_date": "2024-02-28T00:00:00Z",
            "modified_date": "2024-02-28T00:22:32.723408Z",
            "client_uuid": "b25a02ee-8423-42ec-ae15-5ee29ffaf910",
            "client_name": "fc-socaas-04@master.com",
            "fc_account_id": 1692344,
            "alerts": [],
            "assets": [],
            "attachments": [],
            "endpoints": [],
            "events": [],
            "event_users": [],
            "forensic_analysis": [],
            "indicators": []
        }
    }
}
```

**Nested Objects:**

#### alerts (Related Alerts)
```json
{
    "uuid": "string",
    "id": 0,
    "name": "string",
    "severity": "string",
    "status": "string",
    "type": "string",
    "affected_endpoint": "string",
    "client_uuid": "string",
    "modified_date": "string"
}
```

#### assets
```json
{
    "uuid": "string",
    "id": 0,
    "hostname": "string",
    "device_sn": "string",
    "device_platform": "string",
    "location": "string",
    "criticality": "string",
    "description": "string",
    "is_sase": true,
    "client_uuid": "string"
}
```

#### attachments
```json
{
    "portal_uuid": "string",
    "fsr_uuid": "string",
    "name": "string",
    "description": "string",
    "created_date": "string",
    "file": {
        "portal_uuid": "string",
        "fsr_uuid": "string",
        "filename": "string",
        "content_type": "string",
        "size": 0,
        "upload_date": "string"
    }
}
```

#### endpoints
```json
{
    "uuid": "string",
    "id": 0,
    "hostname": "string",
    "ip": "string",
    "mac_address": "string",
    "operating_system": "string",
    "criticality": "string",
    "fct_uid": "string",
    "client_uuid": "string"
}
```

#### events
```json
{
    "uuid": "string",
    "id": 0,
    "name": "string",
    "type": "string",
    "severity": "string",
    "status": "string",
    "source_ip": "string",
    "destination_ip": "string",
    "hostname": "string",
    "domain_name": "string",
    "url": "string",
    "file_name": "string",
    "file_hash": "string",
    "threat_name": "string",
    "threat_id": "string",
    "threat_category": "string",
    "threat_severity": "string",
    "threat_action": "string",
    "cve": "string",
    "service": "string",
    "device_type": "string",
    "source_device_id": "string",
    "source_device_name": "string",
    "sender_email": "string",
    "recipient_email": "string",
    "http_referer": "string",
    "http_xff": "string",
    "resolved_ip": "string",
    "is_sase": true,
    "client_uuid": "string",
    "event_created_date": "string",
    "event_updated_date": "string"
}
```

#### event_users
```json
{
    "username": "string",
    "client_uuid": "string"
}
```

#### forensic_analysis
```json
{
    "uuid": "string",
    "id": 0,
    "endpoint": "string",
    "status": "string",
    "requested_by": "string",
    "forensic_sr_id": "string",
    "forensic_sr_url": "string",
    "client_uuid": "string",
    "created_date": "string",
    "modified_date": "string"
}
```

#### indicators (IOCs)
```json
{
    "uuid": "string",
    "id": 0,
    "type": "string",
    "value": "string",
    "ioc_category": "string",
    "ioc_rating_confidence": "string",
    "enrichment_status": "string",
    "anti_virus_category": "string",
    "web_filter_category": "string",
    "spam_category": ["string"],
    "kill_chain_phases": ["string"]
}
```

---

### Update Alert Status

**Endpoint:** `POST /socaasAPI/v1/alert/{alertuuid}`

Updates the status and/or closure notes of an alert.

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| alertuuid | string (UUID) | Yes | Alert UUID |

**Request Body:**
```json
{
    "param": {
        "data": {
            "status": "inprogress",
            "closure_notes": "Investigation ongoing"
        }
    }
}
```

**Valid Status Values:**
- `inprogress` - Alert is being investigated
- `completed` - Alert investigation complete

**Note:** Cannot change status from 'Completed' to other statuses (returns InvalidRequest error code 14).

**Response:**
```json
{
    "result": {
        "status": 0,
        "errorArr": [],
        "data": true
    }
}
```

---

### Get Alerts by Client

**Endpoint:** `GET /socaasAPI/v1/alert/client/{clientuuid}`

Retrieves all alerts for a specific client. Useful for MSSPs managing multiple clients.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| clientuuid | string (UUID) | Yes | Client UUID |

**Response:**
```json
{
    "result": {
        "status": 0,
        "errorArr": [],
        "data": [
            {
                "uuid": "3a90b295-c110-4333-a361-469789cb5b16",
                "id": 43871,
                "name": "open api test 0003",
                "severity": "Medium",
                "type": "",
                "status": "Confirmed",
                "sla": "Met",
                "description": "open api test 0003",
                "closure_notes": "",
                "analysis_recommendation": "",
                "escalation_path": "",
                "affected_endpoint": "",
                "client_uuid": "b25a02ee-8423-42ec-ae15-5ee29ffaf910",
                "client_name": "fc-socaas-04@master.com",
                "fc_account_id": 1692344,
                "fc_client_name": "",
                "created_date": "1970-01-01T00:00:00Z",
                "modified_date": "2024-02-28T00:22:32.723408Z",
                "self_fc_account_id": 1692344,
                "mssp_fc_account_id": 1692344
            }
        ]
    }
}
```

---

## Comments

### List Comments

**Endpoint:** `GET /socaasAPI/v1/comment`

Returns a list of comments for a specific alert or service request.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| module | string | Yes | Module type: `alerts` or `service_request` |
| uuid | string (UUID) | Yes | UUID of the alert or service request |

**Example:**
```
GET /socaasAPI/v1/comment?module=alerts&uuid=3a90b295-c110-4333-a361-469789cb5b16
```

**Response:**
```json
{
    "result": {
        "status": 0,
        "errorArr": [],
        "data": [
            {
                "content": "comment from portal UI",
                "tag": "",
                "create_user": "fc-socaas-04@master.com",
                "created_date": "2024-03-06T19:39:55.411706Z"
            }
        ]
    }
}
```

**Comment Fields:**

| Field | Type | Description |
|-------|------|-------------|
| content | string | Comment text |
| tag | string | Optional tag/label |
| create_user | string | User who created the comment |
| created_date | string | ISO 8601 creation timestamp |

---

### Create Comment

**Endpoint:** `POST /socaasAPI/v1/comment`

Creates a comment for an alert or service request.

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
    "param": {
        "data": {
            "content": "string",
            "related": "alerts",
            "related_uuid": "string",
            "tag": "string"
        }
    }
}
```

**Request Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| content | string | Yes | Comment text |
| related | string | Yes | Module: `alerts` or `service_request` |
| related_uuid | string (UUID) | Yes | UUID of the alert or service request |
| tag | string | No | Optional tag/label |

**Example (Alert Comment):**
```json
{
    "param": {
        "data": {
            "content": "Investigation in progress - checking logs",
            "related": "alerts",
            "related_uuid": "3a90b295-c110-4333-a361-469789cb5b16",
            "tag": ""
        }
    }
}
```

**Example (Service Request Comment):**
```json
{
    "param": {
        "data": {
            "content": "Request update - waiting for customer response",
            "related": "service_request",
            "related_uuid": "04ad3519-e1a2-438f-b2b5-1299ea32893c",
            "tag": ""
        }
    }
}
```

**Response:**
```json
{
    "result": {
        "status": 0,
        "errorArr": [],
        "data": {
            "content": "Investigation in progress - checking logs",
            "tag": "",
            "create_user": "APIuser(93f11d7d-fef2-48ad-98d5-2917833a9133)",
            "modify_user": "APIuser(93f11d7d-fef2-48ad-98d5-2917833a9133)",
            "created_date": "2024-03-06T19:44:39.731200048Z",
            "modified_date": "2024-03-06T19:44:39.731200145Z"
        }
    }
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| content | string | Comment text |
| tag | string | Tag/label |
| create_user | string | User who created the comment |
| modify_user | string | User who last modified |
| created_date | string | ISO 8601 creation timestamp |
| modified_date | string | ISO 8601 modification timestamp |

---

## File Downloads

### Download Attachment or Report

**Endpoint:** `GET /socaasAPI/v1/file`

Downloads an attachment or report file. Returns file content as byte array.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| module | string | Yes | `attachment` or `report` |
| file-portal-uuid | string (UUID) | Yes | File portal UUID |

**Example (Attachment):**
```
GET /socaasAPI/v1/file?module=attachment&file-portal-uuid=2b3f59cf-5043-467c-b2db-641ad11adcd0
```

**Example (Report):**
```
GET /socaasAPI/v1/file?module=report&file-portal-uuid=21a43dj3-5043-467c-b2db-641ad11adcd0
```

**Response:**
```json
{
    "result": {
        "status": 0,
        "errorArr": [],
        "data": {
            "filename": "screenshot.png",
            "content_type": "image/png",
            "file_content": [137, 80, 78, 71, ...]
        }
    }
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| filename | string | Original filename |
| content_type | string | MIME type (e.g., `image/png`, `application/pdf`) |
| file_content | integer[] | File content as byte array |

**Note:** `file_content` is returned as a byte array (array of integers 0-255). To save the file, convert the byte array to binary data.

**Python Example:**
```python
import json

response = client.request("GET", "/socaasAPI/v1/file",
    params={"module": "attachment", "file-portal-uuid": "your-uuid"})

data = response["result"]["data"]
filename = data["filename"]
content = bytes(data["file_content"])

with open(filename, "wb") as f:
    f.write(content)
```

---

## Service Requests

### List Service Requests

**Endpoint:** `GET /socaasAPI/v1/service-request`

Returns a list of all service requests.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Parameters:** None

**Response:**
```json
{
    "result": {
        "status": 0,
        "errorArr": [],
        "data": [
            {
                "uuid": "04ad3519-e1a2-438f-b2b5-1299ea32893c",
                "id": 161404,
                "portal_uuid": "04ad3519-e1a2-438f-b2b5-1299ea32893c",
                "fsr_uuid": "edb5985b-de79-4345-8c58-b6681e7ce60a",
                "name": "test",
                "description": "test",
                "notification": "test@test.com",
                "status": "New",
                "type": "Portal Access",
                "closure_notes": "",
                "complete_date": "1970-01-01T00:00:00Z",
                "created_date": "2024-02-26T19:50:44.218694Z",
                "modified_date": "2024-02-27T00:00:06.716512Z",
                "client_uuid": "b25a02ee-8423-42ec-ae15-5ee29ffaf910",
                "client_name": "fc-socaas-04@master.com",
                "fc_account_id": 1692344,
                "fc_client_name": "",
                "self_fc_account_id": 1692344,
                "mssp_account_id": 1692344
            }
        ]
    }
}
```

**Service Request List Fields:**

| Field | Type | Description |
|-------|------|-------------|
| uuid | string | Unique identifier |
| id | integer | Numeric request ID |
| portal_uuid | string | Portal UUID |
| fsr_uuid | string | FSR UUID |
| name | string | Request title |
| description | string | Request details |
| notification | string | Email for notifications |
| status | string | Current status |
| type | string | Request type |
| closure_notes | string | Notes when closed |
| complete_date | string | Completion timestamp |
| created_date | string | Creation timestamp |
| modified_date | string | Last modified timestamp |
| client_uuid | string | Client UUID |
| client_name | string | Client name |
| fc_account_id | integer | FortiCloud account ID |
| fc_client_name | string | FortiCloud client name |
| self_fc_account_id | integer | Self FortiCloud account ID |
| mssp_account_id | integer | MSSP account ID |

---

### Get Service Request Details

**Endpoint:** `GET /socaasAPI/v1/service-request/{uuid}`

Returns detailed information for a specific service request.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| uuid | string (UUID) | Yes | Service Request UUID |

**Response:**
```json
{
    "result": {
        "status": 0,
        "errorArr": [],
        "data": {
            "uuid": "04ad3519-e1a2-438f-b2b5-1299ea32893c",
            "id": 161404,
            "name": "test",
            "description": "test",
            "translatedName": "",
            "translatedDescription": "",
            "notification": "test@test.com",
            "status": 0,
            "type": 0,
            "closureNotes": "",
            "completedDate": "1970-01-01T00:00:00Z",
            "portalCreateDate": "2024-02-26T19:50:44.218694Z",
            "portalModifyDate": "2024-02-27T00:00:06.716512Z",
            "portalCreateUser": "",
            "portalModifyUser": "",
            "fsruuid": "edb5985b-de79-4345-8c58-b6681e7ce60a",
            "fsrcreateDate": "",
            "fsrmodifyDate": "",
            "fsrcreateUser": "",
            "fsrmodifyUser": "",
            "archiveDate": "",
            "deletionDate": "",
            "client": "b25a02ee-8423-42ec-ae15-5ee29ffaf910",
            "clientName": "fc-socaas-04@master.com",
            "companyName": "",
            "tenant": "",
            "fcaccountID": 1692344,
            "fcclientName": "",
            "selfFCAccountID": 1692344,
            "msspfcaccountID": 1692344,
            "visibleToCustomer": true
        }
    }
}
```

**Note:** The details endpoint uses camelCase field names (e.g., `clientName`, `closureNotes`) unlike the list endpoint which uses snake_case.

---

### Create Service Request

**Endpoint:** `POST /socaasAPI/v1/service-request`

Creates a new service request.

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
    "param": {
        "data": {
            "title": "Request Title",
            "type": "whitelistrequest",
            "notes": "Request description here",
            "notification": "user@example.com",
            "client_name": "client_name",
            "translated_title": "",
            "translated_notes": "",
            "attachment_files": [
                {
                    "filename": "screenshot.png",
                    "content_type": "image/png",
                    "file_content": [137, 80, 78, 71, ...]
                }
            ]
        }
    }
}
```

**Request Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| title | string | Yes | Request title |
| type | string | Yes | Request type (see values below) |
| notes | string | Yes | Request description |
| notification | string | No | Email for notifications |
| client_name | string | MSSP only | Client name (required for MSSPs with multiple clients) |
| translated_title | string | No | Translated title |
| translated_notes | string | No | Translated notes |
| attachment_files | array | No | File attachments |

**Service Request Type Values:**

| Value | Display Name |
|-------|--------------|
| `devicedecommissioning` | Device Decommissioning |
| `escalationmatrixupdate` | Escalation Matrix Update |
| `newmonitoringrequest` | New Monitoring Request |
| `newreportrequest` | New Report Request |
| `portalaccess` | Portal Access |
| `servicedecommissioning` | Service Decommissioning |
| `serviceenquiry` | Service Enquiry |
| `technicalassitance` | Technical Assistance |
| `whitelistrequest` | Whitelist Request |
| `others` | Others |

**Response:**
```json
{
    "result": {
        "status": 0,
        "errorArr": [],
        "data": {
            "id": -1,
            "portal_uuid": "ba1a1ca4-25e7-4a69-803c-9a4bfc72d9df",
            "fsr_uuid": "00000000-0000-0000-0000-000000000000",
            "name": "Request Title",
            "status": {
                "@id": "string",
                "itemValue": "New",
                "listName": "string",
                "orderIndex": 0,
                "uuid": "string"
            },
            "type": {
                "@id": "string",
                "itemValue": "Whitelist Request",
                "listName": "string",
                "orderIndex": 0,
                "uuid": "string"
            },
            "description": "Request description here",
            "notification": "user@example.com",
            "attachments": [...]
        }
    }
}
```

---

### Get Service Requests by Client

**Endpoint:** `GET /socaasAPI/v1/service-request/client/{clientuuid}`

Returns all service requests for a specific client. Useful for MSSPs managing multiple clients.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| clientuuid | string (UUID) | Yes | Client UUID |

**Response:**
Same format as List Service Requests.

---

## Reports

### List Reports

**Endpoint:** `GET /socaasAPI/v1/report`

Returns a list of all available reports.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Parameters:** None

**Response:**
```json
{
    "result": {
        "status": 0,
        "errorArr": [],
        "data": [
            {
                "category": "Monthly",
                "client_name": "fc-socaas-04@master.com",
                "client_uuid": "b25a02ee-8423-42ec-ae15-5ee29ffaf910",
                "file": {
                    "portal_uuid": "21a43dj3-5043-467c-b2db-641ad11adcd0",
                    "filename": "SOCaaS_Monthly_Report_2024-02.pdf",
                    "content_type": "application/pdf",
                    "upload_date": "2024-03-01T00:00:00Z"
                }
            }
        ]
    }
}
```

**Report Fields:**

| Field | Type | Description |
|-------|------|-------------|
| category | string | Report category (e.g., Monthly, Quarterly) |
| client_name | string | Client name |
| client_uuid | string | Client UUID |
| file | object | File information |
| file.portal_uuid | string | File portal UUID (use with `/file` endpoint to download) |
| file.filename | string | Report filename |
| file.content_type | string | MIME type |
| file.upload_date | string | Upload timestamp |

**Downloading Reports:**

Use the `file.portal_uuid` with the File Download endpoint:
```
GET /socaasAPI/v1/file?module=report&file-portal-uuid=21a43dj3-5043-467c-b2db-641ad11adcd0
```

---

### Get Reports by Client

**Endpoint:** `GET /socaasAPI/v1/report/client/{clientuuid}`

Returns all reports for a specific client.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| clientuuid | string (UUID) | Yes | Client UUID |

**Response:**
Same format as List Reports.

---

## MSSP Clients

### List Clients

**Endpoint:** `GET /socaasAPI/v1/client`

Returns a list of all clients managed by the MSSP.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Parameters:** None

**Response:**
```json
{
    "result": {
        "status": 0,
        "errorArr": [],
        "data": [
            {
                "client_uuid": "b25a02ee-8423-42ec-ae15-5ee29ffaf910",
                "client_name": "fc-socaas-04@master.com",
                "modify_date": "2024-02-28T00:22:32.723408Z"
            }
        ]
    }
}
```

**Client Fields:**

| Field | Type | Description |
|-------|------|-------------|
| client_uuid | string | Client unique identifier |
| client_name | string | Client name |
| modify_date | string | Last modification timestamp |

---

## MSSP Client Onboarding

### Get Pre-Onboarding Information

**Endpoint:** `GET /socaasAPI/v1/mssp-onboarding-info`

Returns pre-onboarding information required for successful MSSP client onboarding. Use this data when creating onboarding requests.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Parameters:** None

**Response:**
```json
{
    "result": {
        "status": 0,
        "errorArr": [],
        "data": [
            {
                "clients": ["existing_client_1", "existing_client_2"],
                "assets": [
                    {
                        "serial_number": "FGVM4VTM25090051",
                        "client_name": "existing_client_1",
                        "client_uuid": "b25a02ee-8423-42ec-ae15-5ee29ffaf910",
                        "fc_description": "FortiGate VM",
                        "is_vdom": true,
                        "vdom": ["root", "vdom1"]
                    }
                ],
                "fortiAnalyzer_cloud_location": [
                    "US West (N. California)",
                    "US East (N. Virginia)",
                    "Europe (Frankfurt)",
                    "Europe (Ireland)",
                    "Asia Pacific (Sydney)",
                    "Asia Pacific (Tokyo)",
                    "Asia Pacific (Singapore)"
                ],
                "country_soc_fazs": [
                    {
                        "country": "US",
                        "collector": [
                            {
                                "name": "US-Collector-1",
                                "region": "us-west",
                                "public_FQDN": "collector-us.fortinet.com",
                                "advanced_mode": false
                            }
                        ]
                    }
                ],
                "existing_contacts": [
                    {
                        "name": "SOC Team Lead",
                        "team_emails": "soc@example.com",
                        "primary_phone": "+1 555-555-5555",
                        "backup_phone": "",
                        "is_default": true
                    }
                ]
            }
        ]
    }
}
```

**Response Fields:**

| Field | Description |
|-------|-------------|
| clients | Existing client names. New clients must use different names. |
| assets | Available assets to onboard. If `is_vdom` is true, asset is already onboarded as VDOM. |
| fortiAnalyzer_cloud_location | Available FAZ Cloud locations for `log_collection.faz_cloud_location` |
| country_soc_fazs | Country-specific SOC FAZ collectors for `log_collection.collector` |
| existing_contacts | Existing contacts that can be used in escalation paths |

**Asset Object:**

| Field | Type | Description |
|-------|------|-------------|
| serial_number | string | Device serial number |
| client_name | string | Associated client name |
| client_uuid | string | Associated client UUID |
| fc_description | string | FortiCloud description |
| is_vdom | boolean | True if already onboarded as VDOM |
| vdom | array | Existing VDOM names (for VDOM assets, use different value) |

---

### Create Onboarding Request

**Endpoint:** `POST /socaasAPI/v1/mssp-customer-onboarding`

Creates a new MSSP client onboarding request. Ensures clients and devices are correctly onboarded with proper logging, monitoring, and escalation configurations.

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
    "param": {
        "data": {
            "client_name": "new_client_1",
            "notification": "client1@fortinet.com",
            "notes": "New client onboarding request",
            "devices": [
                {
                    "serial_number": "FGVM4VTM25090051",
                    "hostname": "fw-client1",
                    "location": "HQ",
                    "description": "Main firewall",
                    "ha_mode": false,
                    "master": "",
                    "is_vdom": true,
                    "vdom": "client1_vdom"
                }
            ],
            "log_collection": {
                "faz_deployment": "FortiAnalyzer Cloud",
                "faz_cloud_location": "US East (N. Virginia)",
                "on_premises_faz_location": "",
                "estimated_log_rate": 0,
                "collector": {
                    "name": "",
                    "region": "",
                    "public_FQDN": ""
                }
            },
            "monitoring_subnet": [
                {
                    "type": "include",
                    "name": "Production",
                    "criticality": "Critical",
                    "subnet": "10.0.0.0/24"
                },
                {
                    "type": "exclude",
                    "name": "Guest Network",
                    "criticality": "Low",
                    "subnet": "192.168.100.0/24"
                }
            ],
            "contacts": [
                {
                    "name": "IT Manager",
                    "team_emails": "it@client1.com",
                    "primary_phone": "+1 555-555-5555",
                    "backup_phone": "+1 555-555-5556",
                    "is_default": true
                }
            ],
            "escalation_paths": [
                {
                    "name": "Critical Systems",
                    "primary_contact": "IT Manager",
                    "secondary_contact": "",
                    "included_subnets": [
                        {"name": "Production", "subnet": "10.0.0.0/24"}
                    ],
                    "excluded_subnets": [],
                    "included_devices": []
                }
            ]
        }
    }
}
```

**Request Field Details:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| client_name | string | Yes | Must be different from existing client names (check `/mssp-onboarding-info`) |
| notification | string | No | Notification email |
| notes | string | No | Additional notes |
| devices | array | Yes | Devices to onboard |
| log_collection | object | Conditional | Required for non-onboarded assets only |
| monitoring_subnet | array | Yes | Subnets to monitor |
| contacts | array | Yes | Contact information |
| escalation_paths | array | Yes | Escalation configurations |

**Device Object:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| serial_number | string | Yes | Device serial number |
| hostname | string | No | Device hostname |
| location | string | No | Physical location |
| description | string | No | Description |
| ha_mode | boolean | No | High availability mode |
| master | string | No | HA master device (if applicable) |
| is_vdom | boolean | No | True if onboarding as VDOM |
| vdom | string | Conditional | VDOM name (required if `is_vdom` is true) |

**Log Collection Object:**

| Field | Type | Description |
|-------|------|-------------|
| faz_deployment | string | `FortiAnalyzer Cloud` or `On-premises` |
| faz_cloud_location | string | Cloud location (from `/mssp-onboarding-info`) |
| on_premises_faz_location | string | On-premises FAZ location |
| estimated_log_rate | integer | Estimated logs per second |
| collector | object | SOC FAZ collector (from `/mssp-onboarding-info`) |

**Monitoring Subnet Object:**

| Field | Type | Values | Description |
|-------|------|--------|-------------|
| type | string | `include`, `exclude` | Include or exclude from monitoring |
| name | string | - | Subnet name/label |
| criticality | string | `Critical`, `High`, `Medium`, `Low` | Criticality level |
| subnet | string | - | Subnet in CIDR or range format |

**Contact Object:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Contact name |
| team_emails | string | Yes | Email address(es) |
| primary_phone | string | Yes | Primary phone number |
| backup_phone | string | No | Backup phone number |
| is_default | boolean | No | Default contact flag |

**Escalation Path Object:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Escalation path name |
| primary_contact | string | Yes | Name from contacts or existing_contacts |
| secondary_contact | string | No | Name from contacts or existing_contacts |
| included_subnets | array | No | Subnets to include (default: all) |
| excluded_subnets | array | No | Subnets to exclude (default: none) |
| included_devices | array | No | Device serial numbers (default: all) |

**Response:**
```json
{
    "result": {
        "status": 0,
        "errorArr": [],
        "data": {
            "status": "success",
            "service_request_uuid": "123e4567-e89b-12d3-a456-426614174000"
        }
    }
}
```

---

## Response Format

All API responses follow a consistent format:

```json
{
    "result": {
        "status": 0,
        "errorArr": [],
        "data": { ... }
    }
}
```

| Field | Type | Description |
|-------|------|-------------|
| status | integer | 0 = success, non-zero = error |
| errorArr | array | List of error messages (empty on success) |
| data | object/array | Response data |

---

## Error Handling

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid or expired token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |

### Error Response Example

```json
{
    "result": {
        "status": 1,
        "errorArr": ["Invalid credentials given."],
        "data": null
    }
}
```

---

## Quick Reference

### Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| **Authentication** | | |
| POST | `/oauth/token/` | Get/refresh OAuth token |
| **Alerts** | | |
| GET | `/socaasAPI/v1/alert` | List alerts (with optional filters) |
| GET | `/socaasAPI/v1/alert/{uuid}` | Get alert details |
| POST | `/socaasAPI/v1/alert/{uuid}` | Update alert status |
| GET | `/socaasAPI/v1/alert/client/{clientuuid}` | List alerts by client |
| **Comments** | | |
| GET | `/socaasAPI/v1/comment` | List comments |
| POST | `/socaasAPI/v1/comment` | Create comment |
| **Files** | | |
| GET | `/socaasAPI/v1/file` | Download attachment/report |
| **Service Requests** | | |
| GET | `/socaasAPI/v1/service-request` | List service requests |
| GET | `/socaasAPI/v1/service-request/{uuid}` | Get service request details |
| POST | `/socaasAPI/v1/service-request` | Create service request |
| GET | `/socaasAPI/v1/service-request/client/{clientuuid}` | List service requests by client |
| **Reports** | | |
| GET | `/socaasAPI/v1/report` | List reports |
| GET | `/socaasAPI/v1/report/client/{clientuuid}` | List reports by client |
| **MSSP Clients** | | |
| GET | `/socaasAPI/v1/client` | List clients |
| **MSSP Onboarding** | | |
| GET | `/socaasAPI/v1/mssp-onboarding-info` | Get pre-onboarding information |
| POST | `/socaasAPI/v1/mssp-customer-onboarding` | Create client onboarding request |
