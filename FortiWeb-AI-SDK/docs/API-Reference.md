# FortiWeb 8.0 REST API Reference

## Access

- **Protocol:** HTTPS only (HTTP 1.0/1.1, no HTTP/2)
- **No keepalive or pipeline** — one API call per HTTP request
- **Base URL:** `https://<host>/api/v2.0/`

## Authentication

Base64-encode a JSON credential object, pass in `Authorization` header on **every request** (stateless):

```
Authorization: <base64({"username":"admin","password":"pass","vdom":"root"})>
```

Generate token:
```bash
echo '{"username":"admin","password":"pass","vdom":"root"}' | base64
```

## Required Headers

| Header | Value |
|--------|-------|
| `Accept` | `application/json` (or `application/raw` for file downloads) |
| `Content-Type` | `application/json` |
| `Authorization` | Base64-encoded credential JSON |

## URL Format

```
/api/v2.0/<path>/<table>/<subtable>?<args>
```

### Paths

| Path | Purpose |
|------|---------|
| `cmdb` | General CLI config operations |
| `cmdb_extra` | File upload/download |
| `ftp` | FTP policy operations |
| `log` | Log filtering and searching |
| `machine_learning` | ML operations |
| `monitor` | Monitoring operations |
| `policy` | Policy operations |
| `server` | Server object operations |
| `system` | System operations |
| `user` | User management operations |
| `wad` | WAD function operations |
| `waf` | WAF function operations |
| `wvs` | WVS function operations |

### Query Parameters

| Parameter | Purpose |
|-----------|---------|
| `mkey` | Primary key of main table (required for PUT/DELETE) |
| `sub_mkey` | Primary key of sub table |
| `move_mkey` | Target primary key for move operation |
| `move_flag` | Move before or after target |
| `insert_mkey` | Insert before this entry |
| `clone_mkey` | Clone source primary key |

## HTTP Methods

| Method | Purpose |
|--------|---------|
| `GET` | Read/list config or download files |
| `POST` | Create new config or upload files |
| `PUT` | Update existing config (requires `?mkey=`) |
| `DELETE` | Delete config (requires `?mkey=`) |

## Response Format

### Success (200 OK / 220 Readonly)

```json
{
    "results": {
        "field1": "value1",
        "field2": "value2"
    }
}
```

File downloads return `Content-Type: application/raw` with `Content-Disposition: attachment; filename=<name>`.

### Error

```json
{
    "results": {
        "errcode": -5
    }
}
```

## Response Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 220 | Read-only access (ADOM user viewing global/ADOM config) |
| 401 | Unauthorized / auth failed |
| 404 | Invalid CLI path or table name |
| 421 | No access permission |
| 423 | VM requires valid license |
| 500 | Internal server error (check response body) |

## Common Error Codes (in response body)

| Code | Message |
|------|---------|
| -1 | Invalid length of value |
| -2 | Value out of range |
| -3 | Entry not found |
| -4 | Max entries reached |
| -5 | Duplicate entry exists |
| -6 | Memory allocation failed |
| -7 | Conflicts with system settings |
| -8 | Invalid IP address |
| -20 | Blank entry |
| -23 | Entry is in use |
| -30 | Invalid username or password |
| -37 | Permission denied |
| -50 | Invalid input format |
| -56 | Empty value not allowed |
| -100 | Duplicate username exists |
| -204 | Invalid username or password |
| -515 | Name is reserved keyword |

## Example: Create Static Route (POST)

```bash
curl -k -X POST \
  -H "Authorization:eyJ1c2Vy..." \
  https://10.0.2.90/api/v2.0/cmdb/router/static \
  -d '{"data":{"q_type":0,"id":"0","dst":"10.0.0.0/16","gateway":"10.0.0.1","device":"mgmt1","device_val":"0"}}'
```

## Example: Update Static Route (PUT)

```bash
curl -k -X PUT \
  -H "Authorization:eyJ1c2Vy..." \
  https://10.0.2.90/api/v2.0/cmdb/router/static?mkey=3 \
  -d '{"data":{"dst":"10.1.0.0/16","gateway":"10.0.0.1","device":"mgmt1","device_val":"1058"}}'
```

## Example: Delete Static Route (DELETE)

```bash
curl -k -X DELETE \
  -H "Authorization:eyJ1c2Vy..." \
  https://10.0.2.90/api/v2.0/cmdb/router/static?mkey=3
```

## Request Body Format

POST and PUT bodies wrap data in a `"data"` key:

```json
{
    "data": {
        "field1": "value1",
        "field2": "value2"
    }
}
```

DELETE has no body.
