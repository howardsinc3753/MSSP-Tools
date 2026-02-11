#!/usr/bin/env python3
"""
Example: Manage Comments on Alerts and Service Requests

Demonstrates how to:
  - List existing comments on an alert
  - Add investigation notes to an alert
  - Add comments to a service request

Usage:
    cd socaas-sdk
    python examples/manage_comments.py

Note:
    Service request comments may return HTTP 500 due to an API limitation.
"""

import sys
from pathlib import Path

# Robust path handling - works from any directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from socaas import SOCaaSClient


def main():
    # --- Authentication ---
    # Option 1: From credential file (recommended)
    # client = SOCaaSClient.from_credential_file("credentials.yaml")

    # Option 2: From environment variables
    # client = SOCaaSClient.from_env()

    # Option 3: Direct credentials
    client = SOCaaSClient(
        username="YOUR-API-USER-ID",
        password="YOUR-API-PASSWORD"
    )
    client.debug = True

    # --- Step 1: Find an alert to comment on ---
    print("=== Finding alerts ===")
    alerts = client.list_alerts()
    print(f"Found {len(alerts)} alerts\n")

    if not alerts:
        print("No alerts found. Cannot demo comments.")
        return

    # Pick the first alert
    alert = alerts[0]
    alert_uuid = alert["uuid"]
    alert_id = alert.get("id", "unknown")
    print(f"Using Alert-{alert_id}: {alert.get('name', 'Unknown')}")
    print(f"  UUID: {alert_uuid}")
    print(f"  Status: {alert.get('status')}")
    print()

    # --- Step 2: List existing comments ---
    print("=== Existing Comments ===")
    comments = client.list_alert_comments(alert_uuid)
    print(f"Found {len(comments)} comment(s)\n")

    for i, comment in enumerate(comments):
        author = comment.get("create_user", "Unknown")
        date = comment.get("created_date", "Unknown")
        content = comment.get("content", "")
        # Truncate HTML content for display
        if len(content) > 120:
            content = content[:120] + "..."
        print(f"  [{i+1}] {author} ({date})")
        print(f"      {content}")
        print()

    # --- Step 3: Add a comment ---
    # Note: The SOCaaS API only accepts tag="" (empty string).
    #       Non-empty tags will return InvalidRequest (code 14).
    print("=== Adding Investigation Note ===")
    try:
        result = client.create_alert_comment(
            alert_uuid=alert_uuid,
            content="SDK test: Investigated alert via SOCaaS Python SDK."
        )
        print(f"Comment added successfully!")
        if isinstance(result, dict):
            print(f"  Author: {result.get('create_user', 'N/A')}")
            print(f"  Date:   {result.get('created_date', 'N/A')}")
    except Exception as e:
        print(f"Failed to add comment: {e}")
    print()

    # --- Step 4: Verify the comment was added ---
    print("=== Verifying Comment ===")
    comments_after = client.list_alert_comments(alert_uuid)
    print(f"Comments now: {len(comments_after)} (was {len(comments)})")
    print()

    # --- Step 5 (Optional): Comment on a Service Request ---
    print("=== Service Request Comment (Optional) ===")
    from socaas.comments import CommentManager
    cm = CommentManager(client)

    srs = client.list_service_requests()
    if srs:
        sr = srs[0]
        sr_uuid = sr["uuid"]
        print(f"SR-{sr.get('id')}: {sr.get('type_display', sr.get('type', 'Unknown'))}")
        try:
            sr_result = cm.create_for_service_request(
                sr_uuid=sr_uuid,
                content="SDK test: Service request comment via SOCaaS Python SDK."
            )
            print(f"SR comment added successfully!")
        except Exception as e:
            print(f"SR comment failed (expected API limitation): {e}")
    else:
        print("No service requests found.")


if __name__ == "__main__":
    main()
