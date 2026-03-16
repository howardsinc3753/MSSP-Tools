# SOCaaS API Error Codes

## Overview

This document describes the error codes returned by the SOCaaS API. Understanding these codes helps with troubleshooting and building robust integrations.

---

## Authentication Errors

### AuthorizationError (Code: 2002)

**Description:** Issues with the Authorization header.

**Causes:**
- No Authorization header provided in request
- Authorization header format incorrect (should be `Bearer <token>`)

**Solution:**
```
Authorization: Bearer <your_access_token>
```

**Example Error Response:**
```json
{
    "result": {
        "status": 2002,
        "errorArr": ["Authorization header missing or malformed"],
        "data": null
    }
}
```

---

### DependentAPIServiceIssue (Code: 1000)

**Description:** Token validation failed.

**Causes:**
- Wrong/invalid token provided
- Token has expired

**Solution:**
- Obtain a new access token via `/oauth/token/`
- If using refresh token, request a new access token
- Implement token expiry tracking and auto-refresh

**Example Error Response:**
```json
{
    "result": {
        "status": 1000,
        "errorArr": ["Token validation failed"],
        "data": null
    }
}
```

---

## Authorization Errors

### NoAccess (Code: 3)

**Description:** User lacks SOCaaS portal permissions.

**Causes:**
- Incorrect IAM portal configuration
- User not granted SOCaaS access in FortiCloud

**Solution:**
- Verify IAM settings in FortiCloud portal
- Ensure user has SOCaaS service enabled
- Contact administrator to grant proper permissions

**Example Error Response:**
```json
{
    "result": {
        "status": 3,
        "errorArr": ["No access to SOCaaS portal"],
        "data": null
    }
}
```

---

### UnqualifiedUser (Code: 2001)

**Description:** User is not onboarded to SOCaaS.

**Causes:**
- User account exists but hasn't completed SOCaaS onboarding
- API user created but not associated with SOCaaS service

**Solution:**
- Complete SOCaaS onboarding process
- For MSSPs, ensure client onboarding is complete
- Contact Fortinet support if onboarding is stuck

**Example Error Response:**
```json
{
    "result": {
        "status": 2001,
        "errorArr": ["User not onboarded to SOCaaS"],
        "data": null
    }
}
```

---

### UnSatisfiedPermission (Code: 2004)

**Description:** Insufficient permissions for the requested action.

**Causes:**
- Read-only user attempting to create/update resources
- User role doesn't permit the operation

**Solution:**
- Use an API user with appropriate permissions
- Request elevated permissions from administrator
- Verify user role allows write operations

**Example Error Response:**
```json
{
    "result": {
        "status": 2004,
        "errorArr": ["Insufficient permissions for this operation"],
        "data": null
    }
}
```

---

## Resource Errors

### RecordNotFound (Code: 1005)

**Description:** The requested resource doesn't exist.

**Causes:**
- Invalid UUID provided
- Resource was deleted
- Resource belongs to different client/account

**Solution:**
- Verify the UUID is correct
- List resources first to get valid UUIDs
- Check you have access to the resource's client

**Example Error Response:**
```json
{
    "result": {
        "status": 1005,
        "errorArr": ["Record not found"],
        "data": null
    }
}
```

---

### InvalidRequest (Code: 14)

**Description:** Request contains invalid parameters or operations.

**Causes:**
- Invalid state transition (e.g., changing alert from 'Completed' to other status)
- Missing required fields
- Invalid field values

**Solution:**
- Review the API documentation for valid operations
- Check state transition rules for the resource
- Validate all required fields are provided

**Example Error Response:**
```json
{
    "result": {
        "status": 14,
        "errorArr": ["Invalid status transition"],
        "data": null
    }
}
```

---

## Rate Limit Errors

### Maximum API Query Limit Reached (Code: 500)

**Description:** Firewall rate limit exceeded.

**Causes:**
- Exceeded GET request limit (100/min or 1000/hour per IP)
- Exceeded POST request limit (5/min or 60/hour per IP)

**Response:** Returns HTTP 500 with HTML error page (not JSON).

**Rate Limits:**

| Method | Per Minute | Per Hour |
|--------|------------|----------|
| GET | 100 | 1,000 |
| POST | 5 | 60 |

**Solution:**
- Implement request throttling
- Add exponential backoff on 500 errors
- Cache responses where appropriate
- Batch operations when possible

**Example Handling (Python):**
```python
import time

def request_with_backoff(client, method, endpoint, max_retries=3):
    for attempt in range(max_retries):
        try:
            return client.request(method, endpoint)
        except Exception as e:
            if "500" in str(e) and attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 10  # 10s, 20s, 40s
                print(f"Rate limited. Waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise
```

---

## Error Code Quick Reference

| Code | Name | Category | Description |
|------|------|----------|-------------|
| 3 | NoAccess | Authorization | No SOCaaS portal permission |
| 14 | InvalidRequest | Request | Invalid parameters or operation |
| 500 | Rate Limit | Firewall | Maximum API query limit reached |
| 1000 | DependentAPIServiceIssue | Authentication | Wrong or expired token |
| 1005 | RecordNotFound | Resource | UUID not found |
| 2001 | UnqualifiedUser | Authorization | User not onboarded |
| 2002 | AuthorizationError | Authentication | Missing/malformed auth header |
| 2004 | UnSatisfiedPermission | Authorization | Read-only user attempting write |

---

## OAuth Token Errors

These errors occur during authentication at `/oauth/token/`:

| Error | Description |
|-------|-------------|
| `invalid_grant` | Invalid username or password |
| `invalid_client` | Invalid client_id |
| `invalid_request` | Missing required parameters |

**Example:**
```json
{
    "error": "invalid_grant",
    "error_description": "Invalid credentials given."
}
```

---

## Troubleshooting Checklist

### Authentication Failed (invalid_grant)
- [ ] Verify API User ID is correct (UUID format)
- [ ] Confirm password is correct
- [ ] Check account is active in FortiCloud
- [ ] Verify client_id is "socaas"

### No Access (Code: 3)
- [ ] Check IAM portal settings in FortiCloud
- [ ] Verify SOCaaS service is enabled for account
- [ ] Confirm API user has SOCaaS permissions

### User Not Onboarded (Code: 2001)
- [ ] Complete SOCaaS onboarding in portal
- [ ] For MSSP: verify client onboarding is complete
- [ ] Contact Fortinet support if needed

### Rate Limited (Code: 500)
- [ ] Implement request throttling
- [ ] Add delays between batch operations
- [ ] Cache frequently accessed data
