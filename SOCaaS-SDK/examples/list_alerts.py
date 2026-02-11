#!/usr/bin/env python3
"""
Example: List SOCaaS Alerts

Lists all alerts from SOCaaS with optional date filtering.

Usage:
    cd socaas-sdk
    python examples/list_alerts.py
"""

import sys
from pathlib import Path

# Robust path handling - works from any directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from socaas import SOCaaSClient


def main():
    # Create client from credential file
    # client = SOCaaSClient.from_credential_file("../credentials.yaml")

    # Or create directly
    client = SOCaaSClient(
        username="YOUR-API-USER-ID",
        password="YOUR-API-PASSWORD"
    )
    client.debug = True

    # List all alerts
    print("Listing alerts...")
    alerts = client.list_alerts()
    print(f"Found {len(alerts)} alerts\n")

    # Print summary
    for i, alert in enumerate(alerts[:5]):
        print(f"[{i+1}] {alert.get('name', 'Unknown')}")
        print(f"    UUID: {alert.get('uuid')}")
        print(f"    Status: {alert.get('status')}")
        print(f"    Severity: {alert.get('severity')}")
        print(f"    Client: {alert.get('client_name')}")
        print()

    if len(alerts) > 5:
        print(f"... and {len(alerts) - 5} more alerts")


if __name__ == "__main__":
    main()
