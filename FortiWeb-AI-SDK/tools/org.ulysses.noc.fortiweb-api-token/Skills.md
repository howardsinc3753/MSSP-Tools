# FortiWeb API Token Manager Skills

## Purpose

Provision and manage REST API admin accounts on FortiWeb 8.0+ devices. This is the **first step** for enabling programmatic access to FortiWeb configuration and monitoring. Without an API token, no other FortiWeb SDK tools can operate.

FortiWeb uses dedicated "REST API" admin accounts (separate from GUI/CLI admins). Each API admin gets a unique token that authenticates all subsequent API calls.

## When to Use This Tool

**Use this tool when the user asks:**
- "Set up API access on FortiWeb"
- "Create an API token for FortiWeb"
- "Provision a new API admin"
- "List API admin accounts"
- "Revoke/delete an API token"
- "I need to connect to FortiWeb programmatically"
- "Enable REST API access on the WAF"

**Do NOT use this tool for:**
- Querying FortiWeb configuration (use fortiweb-config tools)
- Checking WAF status or health (use fortiweb-health-check)
- Managing GUI/CLI admin accounts (different admin type)
- FortiGate operations (use fortigate-* tools)

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `target_ip` | string | Yes | - | FortiWeb management IP address |
| `action` | string | Yes | - | `create`, `list`, or `delete` |
| `admin_name` | string | create/delete | - | Name for the API admin account |
| `vdom` | string | No | root | VDOM scope for the API admin |
| `accprofile` | string | No | prof_admin | Access profile (prof_admin = full access) |
| `timeout` | integer | No | 30 | Request timeout in seconds |
| `verify_ssl` | boolean | No | false | Verify SSL certificate |

## Provisioning Workflow

### Step 1: List Existing API Admins
Check what API admins already exist:
```json
{
    "target_ip": "192.168.209.31",
    "action": "list"
}
```

### Step 2: Create a New API Admin
```json
{
    "target_ip": "192.168.209.31",
    "action": "create",
    "admin_name": "sdk-admin",
    "accprofile": "prof_admin"
}
```

**IMPORTANT:** The API key is returned ONLY at creation time. Store it immediately in the credential file at `~/.config/mcp/fortiweb_credentials.yaml`.

### Step 3: Save Credentials
After creating the API admin, save the token to the credential file:
```yaml
devices:
  fortiweb-lab:
    host: "192.168.209.31"
    api_token: "<token-from-create-response>"
    verify_ssl: false
default_lookup:
  "192.168.209.31": fortiweb-lab
```

### Step 4: Verify API Access
Use any FortiWeb SDK tool (e.g., fortiweb-health-check) to confirm the token works.

## GUI Alternative

If you need to create the API admin manually via the FortiWeb GUI:

1. Navigate to **System > Admin > Administrators**
2. Click **Create New**
3. Set **Type** to **REST API**
4. Enter a name and select an access profile
5. Click **OK** — the API key is displayed once
6. Copy and store the key securely

CLI alternative:
```
config system admin
    edit "sdk-admin"
        set type api
        set accprofile prof_admin
    next
end
```

## Credential File Format

Location: `~/.config/mcp/fortiweb_credentials.yaml`

```yaml
# FortiWeb device credentials for SDK tools
# Used by all org.ulysses.noc.fortiweb-* tools

devices:
  fortiweb-prod:
    host: "10.0.1.100"
    username: "admin"
    password: "secure-password"
    api_token: "generated-api-token"
    verify_ssl: true

  fortiweb-lab:
    host: "<fortiweb-ip>"
    username: "admin"
    password: "<admin-password>"
    api_token: null  # will be set after create action
    verify_ssl: false

default_lookup:
  "10.0.1.100": fortiweb-prod
  "<fortiweb-ip>": fortiweb-lab
```

## Sample Responses

### List Action
```json
{
    "success": true,
    "target_ip": "192.168.209.31",
    "action": "list",
    "admins": [
        {
            "name": "sdk-admin",
            "vdom": "root",
            "accprofile": "prof_admin"
        }
    ]
}
```

### Create Action
```json
{
    "success": true,
    "target_ip": "192.168.209.31",
    "action": "create",
    "admin_name": "sdk-admin",
    "api_key": "abc123def456...",
    "vdom": "root",
    "accprofile": "prof_admin",
    "message": "API admin 'sdk-admin' created. Store the api_key securely — it cannot be retrieved again."
}
```

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `target_ip is required` | Missing parameter | Provide FortiWeb IP |
| `No admin credentials found` | Missing config | Add device to credential file |
| `Authentication failed` | Wrong username/password | Verify admin credentials |
| `HTTP 403 Forbidden` | Insufficient permissions | Use admin with full access |
| `HTTP 409 Conflict` | Admin name already exists | Choose a different name or delete first |
| `Connection failed` | Network issue | Check network path to FortiWeb |

## Related Tools

- `org.ulysses.noc.fortiweb-health-check` - Check FortiWeb device health
- `org.ulysses.noc.fortiweb-server-policy` - View/manage server policies
- `org.ulysses.noc.fortiweb-protection-profile` - View/manage protection profiles
- `org.ulysses.noc.fortiweb-attack-log` - Query attack logs
