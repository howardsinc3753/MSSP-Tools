#!/usr/bin/env python3
"""
SOCaaS Alert Poller - Background Alert Monitoring with Webhook Notifications

This script monitors SOCaaS for new alerts and sends webhook notifications
to your destination (ServiceNow, Slack, Teams, PagerDuty, or custom REST API).

QUICK START:
    1. Copy credentials.yaml.template to credentials.yaml
    2. Set your webhook URL below
    3. Run: python alert_poller.py

USAGE:
    # Single check (cron-friendly)
    python alert_poller.py --webhook-url https://webhook.site/your-uuid

    # Continuous polling every 60 seconds
    python alert_poller.py --webhook-url https://webhook.site/your-uuid --interval 60

    # Poll 10 times then exit
    python alert_poller.py --webhook-url https://webhook.site/your-uuid --interval 60 --max-polls 10

DESTINATION EXAMPLES:
    See docs/webhook-integration.md for ServiceNow, Slack, Teams setup guides.
"""

import sys
import time
import json
import argparse
import requests
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory for imports when running from examples/
sys.path.insert(0, str(Path(__file__).parent.parent))

from socaas import SOCaaSClient


# =============================================================================
# CONFIGURATION - Modify these for your environment
# =============================================================================

# Default webhook URL (override with --webhook-url)
DEFAULT_WEBHOOK_URL = "https://webhook.site/YOUR-UUID-HERE"

# Default polling interval in seconds (0 = single check)
DEFAULT_POLL_INTERVAL = 0

# State file to persist alert count between runs
STATE_FILE = Path(__file__).parent / ".alert_poller_state.json"


# =============================================================================
# WEBHOOK PAYLOAD BUILDERS
# =============================================================================

def build_generic_payload(alert: dict, alert_details: dict, count_info: dict) -> dict:
    """
    Build generic webhook payload. Works with webhook.site and custom APIs.

    Modify this function to customize the payload for your destination.
    """
    payload = {
        "event_type": "new_socaas_alert",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "socaas-alert-poller",
        "alert_count": count_info,
        "alert": {
            "uuid": alert.get("uuid"),
            "id": alert.get("id"),
            "name": alert.get("name"),
            "status": alert.get("status"),
            "severity": alert.get("severity"),
            "category": alert.get("category"),
            "client_name": alert.get("client_name"),
            "created_datetime": alert.get("created_datetime"),
        }
    }

    # Add details if available
    if alert_details:
        payload["alert"]["description"] = alert_details.get("description")
        payload["alert"]["recommendations"] = alert_details.get("recommendations")

        # Add IOC summary
        indicators = alert_details.get("indicators", [])
        if indicators:
            payload["alert"]["ioc_count"] = len(indicators)
            payload["alert"]["sample_iocs"] = [
                {"type": i.get("type"), "value": i.get("value")}
                for i in indicators[:5]
            ]

        # Add endpoint summary
        endpoints = alert_details.get("endpoints", [])
        if endpoints:
            payload["alert"]["endpoint_count"] = len(endpoints)
            payload["alert"]["hostnames"] = [ep.get("hostname") for ep in endpoints[:5]]

    return payload


def build_servicenow_payload(alert: dict, alert_details: dict, count_info: dict) -> dict:
    """
    Build ServiceNow incident payload.

    NOTE: You may need to customize field names based on your ServiceNow instance.
    See docs/webhook-integration.md for details.
    """
    severity_map = {"Critical": 1, "High": 2, "Medium": 2, "Low": 3}

    return {
        "short_description": f"[SOCaaS] {alert.get('name', 'Security Alert')}",
        "description": alert_details.get("description", "") if alert_details else "",
        "impact": severity_map.get(alert.get("severity"), 3),
        "urgency": 2,
        "category": "Security",
        "subcategory": alert.get("category", "Unknown"),
        "caller_id": "socaas-integration",
        "assignment_group": "Security Operations",
        "u_socaas_alert_uuid": alert.get("uuid"),
        "u_client_name": alert.get("client_name"),
    }


def build_slack_payload(alert: dict, alert_details: dict, count_info: dict) -> dict:
    """
    Build Slack incoming webhook payload.

    NOTE: Uses simple text format. For rich formatting, use Slack Blocks.
    """
    severity_emoji = {
        "Critical": ":red_circle:",
        "High": ":orange_circle:",
        "Medium": ":yellow_circle:",
        "Low": ":white_circle:"
    }
    emoji = severity_emoji.get(alert.get("severity"), ":grey_question:")

    text = (
        f"{emoji} *New SOCaaS Alert*\n"
        f"*{alert.get('name', 'Unknown')}*\n"
        f"Severity: {alert.get('severity')} | Status: {alert.get('status')}\n"
        f"Client: {alert.get('client_name')}\n"
        f"UUID: `{alert.get('uuid')}`"
    )

    return {"text": text}


def build_teams_payload(alert: dict, alert_details: dict, count_info: dict) -> dict:
    """
    Build Microsoft Teams incoming webhook payload (MessageCard format).

    NOTE: For Adaptive Cards, use Power Automate to transform the payload.
    """
    severity_color = {
        "Critical": "FF0000",
        "High": "FFA500",
        "Medium": "FFFF00",
        "Low": "00FF00"
    }

    return {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": severity_color.get(alert.get("severity"), "808080"),
        "summary": f"SOCaaS Alert: {alert.get('name')}",
        "sections": [{
            "activityTitle": f"New SOCaaS Alert: {alert.get('name')}",
            "facts": [
                {"name": "Severity", "value": alert.get("severity", "Unknown")},
                {"name": "Status", "value": alert.get("status", "Unknown")},
                {"name": "Client", "value": alert.get("client_name", "Unknown")},
                {"name": "Category", "value": alert.get("category", "Unknown")},
            ],
            "markdown": True
        }]
    }


def build_pagerduty_payload(alert: dict, alert_details: dict, count_info: dict, routing_key: str) -> dict:
    """
    Build PagerDuty Events API v2 payload.

    Args:
        routing_key: Your PagerDuty integration key
    """
    severity_map = {"Critical": "critical", "High": "error", "Medium": "warning", "Low": "info"}

    return {
        "routing_key": routing_key,
        "event_action": "trigger",
        "dedup_key": f"socaas-{alert.get('uuid')}",
        "payload": {
            "summary": f"[SOCaaS] {alert.get('name', 'Security Alert')}",
            "severity": severity_map.get(alert.get("severity"), "warning"),
            "source": "SOCaaS",
            "component": alert.get("client_name"),
            "group": alert.get("category"),
            "custom_details": {
                "alert_uuid": alert.get("uuid"),
                "description": alert_details.get("description") if alert_details else None,
            }
        }
    }


# =============================================================================
# CORE POLLER LOGIC
# =============================================================================

def load_state() -> dict:
    """Load persisted state from file."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_known_count": None, "seen_uuids": []}


def save_state(state: dict):
    """Persist state to file."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def send_webhook(url: str, payload: dict, headers: dict = None) -> dict:
    """Send webhook notification."""
    default_headers = {"Content-Type": "application/json"}
    if headers:
        default_headers.update(headers)

    try:
        response = requests.post(url, json=payload, headers=default_headers, timeout=30)
        return {
            "success": response.status_code in [200, 201, 202, 204],
            "status_code": response.status_code,
            "response": response.text[:200] if response.text else None
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def poll_alerts(
    client: SOCaaSClient,
    webhook_url: str,
    webhook_headers: dict = None,
    payload_format: str = "generic",
    last_known_count: int = None,
    seen_uuids: list = None,
    include_details: bool = True,
    pagerduty_routing_key: str = None
) -> dict:
    """
    Check for new alerts and send webhook if detected.

    Uses hybrid detection: both count changes AND UUID tracking to catch
    new alerts even when count stays flat (e.g., alert deleted + new alert).

    Args:
        client: SOCaaSClient instance
        webhook_url: Destination webhook URL
        webhook_headers: Optional custom headers
        payload_format: One of: generic, servicenow, slack, teams, pagerduty
        last_known_count: Previous alert count (None = establish baseline)
        seen_uuids: List of previously seen alert UUIDs
        include_details: Fetch full alert details for webhook
        pagerduty_routing_key: Required if payload_format is pagerduty

    Returns:
        Dict with current_count, new_alerts_detected, webhook_sent, seen_uuids, etc.
    """
    # Get current alerts
    alerts = client.list_alerts()
    current_count = len(alerts)
    current_uuids = [a.get("uuid") for a in alerts if a.get("uuid")]

    # Initialize seen_uuids if not provided
    if seen_uuids is None:
        seen_uuids = []
    seen_uuids_set = set(seen_uuids)

    result = {
        "current_count": current_count,
        "previous_count": last_known_count,
        "new_alerts_detected": 0,
        "webhook_sent": False,
        "webhook_result": None,
        "seen_uuids": current_uuids[:100]  # Keep last 100 UUIDs to limit state size
    }

    # First run - establish baseline
    if last_known_count is None:
        print(f"[Baseline] Current alert count: {current_count}, tracking {len(current_uuids)} UUIDs")
        return result

    # Find new alerts by UUID (more reliable than count-only)
    new_alerts = [a for a in alerts if a.get("uuid") not in seen_uuids_set]

    # Also check count increase as backup detection
    count_increased = current_count > last_known_count

    if new_alerts or count_increased:
        new_count = len(new_alerts) if new_alerts else (current_count - last_known_count)
        result["new_alerts_detected"] = max(new_count, 1)

        if new_alerts:
            print(f"[New Alert] {len(new_alerts)} new alert(s) detected by UUID tracking!")
        elif count_increased:
            print(f"[New Alert] Count increased ({last_known_count} -> {current_count})")

        # Get the newest alert (prefer UUID-detected, fallback to first in list)
        latest_alert = new_alerts[0] if new_alerts else alerts[0]

        # Fetch details if requested
        alert_details = None
        if include_details:
            try:
                alert_details = client.get_alert(latest_alert["uuid"])
            except Exception as e:
                print(f"[Warning] Could not fetch alert details: {e}")

        # Build payload based on format
        count_info = {
            "current": current_count,
            "previous": last_known_count,
            "new_alerts": result["new_alerts_detected"]
        }

        if payload_format == "servicenow":
            payload = build_servicenow_payload(latest_alert, alert_details, count_info)
        elif payload_format == "slack":
            payload = build_slack_payload(latest_alert, alert_details, count_info)
        elif payload_format == "teams":
            payload = build_teams_payload(latest_alert, alert_details, count_info)
        elif payload_format == "pagerduty":
            if not pagerduty_routing_key:
                raise ValueError("pagerduty_routing_key required for PagerDuty format")
            payload = build_pagerduty_payload(latest_alert, alert_details, count_info, pagerduty_routing_key)
        else:
            payload = build_generic_payload(latest_alert, alert_details, count_info)

        # Send webhook
        webhook_result = send_webhook(webhook_url, payload, webhook_headers)
        result["webhook_sent"] = webhook_result.get("success", False)
        result["webhook_result"] = webhook_result

        if webhook_result.get("success"):
            print(f"[Webhook] Sent successfully to {webhook_url}")
        else:
            print(f"[Webhook] Failed: {webhook_result}")
    else:
        print(f"[No Change] Alert count: {current_count}, no new UUIDs detected")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="SOCaaS Alert Poller - Monitor for new alerts and send webhooks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
    # Test with webhook.site
    python alert_poller.py --webhook-url https://webhook.site/your-uuid

    # ServiceNow integration
    python alert_poller.py --webhook-url https://instance.service-now.com/api/now/table/incident \\
        --format servicenow --header "Authorization: Basic YOUR-CREDS"

    # Slack integration
    python alert_poller.py --webhook-url https://hooks.slack.com/services/T00/B00/XXX --format slack

    # Continuous polling every 5 minutes
    python alert_poller.py --webhook-url https://webhook.site/your-uuid --interval 300
        """
    )

    parser.add_argument("--webhook-url", default=DEFAULT_WEBHOOK_URL,
                        help="Webhook destination URL")
    parser.add_argument("--interval", type=int, default=DEFAULT_POLL_INTERVAL,
                        help="Polling interval in seconds (0 = single check)")
    parser.add_argument("--max-polls", type=int, default=0,
                        help="Maximum poll cycles (0 = unlimited)")
    parser.add_argument("--format", choices=["generic", "servicenow", "slack", "teams", "pagerduty"],
                        default="generic", help="Webhook payload format")
    parser.add_argument("--header", action="append", dest="headers",
                        help="Custom header (e.g., 'Authorization: Bearer token')")
    parser.add_argument("--pagerduty-key", help="PagerDuty routing key (required for pagerduty format)")
    parser.add_argument("--no-details", action="store_true",
                        help="Skip fetching alert details (faster, less data)")
    parser.add_argument("--reset-state", action="store_true",
                        help="Reset stored state (re-establish baseline)")
    parser.add_argument("--credentials", default="../credentials.yaml",
                        help="Path to credentials.yaml file")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")

    args = parser.parse_args()

    # Validate
    if args.format == "pagerduty" and not args.pagerduty_key:
        parser.error("--pagerduty-key required when using pagerduty format")

    # Parse custom headers
    webhook_headers = {}
    if args.headers:
        for h in args.headers:
            if ":" in h:
                key, value = h.split(":", 1)
                webhook_headers[key.strip()] = value.strip()

    # Load state
    if args.reset_state and STATE_FILE.exists():
        STATE_FILE.unlink()
        print("[State] Reset - will establish new baseline")

    state = load_state()
    last_known_count = state.get("last_known_count")
    seen_uuids = state.get("seen_uuids", [])

    # Create client
    creds_path = Path(__file__).parent / args.credentials
    if creds_path.exists():
        client = SOCaaSClient.from_credential_file(str(creds_path))
    else:
        # Try environment variables
        client = SOCaaSClient.from_env()

    if args.debug:
        client.debug = True

    print(f"[Start] Polling SOCaaS alerts -> {args.webhook_url}")
    print(f"[Config] Format: {args.format}, Interval: {args.interval}s, Max polls: {args.max_polls or 'unlimited'}")

    # Polling loop
    poll_count = 0
    try:
        while True:
            poll_count += 1
            print(f"\n[Poll {poll_count}] Checking for new alerts...")

            result = poll_alerts(
                client=client,
                webhook_url=args.webhook_url,
                webhook_headers=webhook_headers if webhook_headers else None,
                payload_format=args.format,
                last_known_count=last_known_count,
                seen_uuids=seen_uuids,
                include_details=not args.no_details,
                pagerduty_routing_key=args.pagerduty_key
            )

            # Update state
            last_known_count = result["current_count"]
            seen_uuids = result.get("seen_uuids", seen_uuids)
            save_state({"last_known_count": last_known_count, "seen_uuids": seen_uuids})

            # Check exit conditions
            if args.interval <= 0:
                break  # Single check mode

            if args.max_polls > 0 and poll_count >= args.max_polls:
                print(f"\n[Done] Reached max polls ({args.max_polls})")
                break

            print(f"[Wait] Sleeping {args.interval}s until next poll...")
            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n[Stopped] Interrupted by user")

    print(f"\n[Summary] Completed {poll_count} poll(s), final count: {last_known_count}")


if __name__ == "__main__":
    main()
