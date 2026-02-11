#!/usr/bin/env python3
"""
Example: Get Alert Details with IOCs

Gets full alert details including indicators of compromise.

Usage:
    cd socaas-sdk
    python examples/get_alert_details.py
"""

import sys
import json
from pathlib import Path

# Robust path handling - works from any directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from socaas import SOCaaSClient


def main():
    client = SOCaaSClient(
        username="YOUR-API-USER-ID",
        password="YOUR-API-PASSWORD"
    )
    client.debug = True

    # First, list alerts to get a UUID
    alerts = client.list_alerts()
    if not alerts:
        print("No alerts found")
        return

    alert_uuid = alerts[0]['uuid']
    print(f"Getting details for alert: {alert_uuid}\n")

    # Get full details
    details = client.get_alert(alert_uuid)

    print(f"Name: {details.get('name')}")
    print(f"Description: {details.get('description', 'N/A')}")
    print(f"Status: {details.get('status')}")
    print(f"Severity: {details.get('severity')}")
    print(f"Category: {details.get('category')}")
    print()

    # Show IOCs
    indicators = details.get('indicators', [])
    print(f"Indicators of Compromise ({len(indicators)}):")
    for ioc in indicators[:10]:
        print(f"  - [{ioc.get('type')}] {ioc.get('value')}")

    # Show endpoints
    endpoints = details.get('endpoints', [])
    print(f"\nAffected Endpoints ({len(endpoints)}):")
    for ep in endpoints[:5]:
        print(f"  - {ep.get('hostname')} ({ep.get('ip_address')})")

    # Show events
    events = details.get('events', [])
    print(f"\nEvents ({len(events)}):")
    for evt in events[:5]:
        print(f"  - [{evt.get('timestamp')}] {evt.get('event_type')}")


if __name__ == "__main__":
    main()
