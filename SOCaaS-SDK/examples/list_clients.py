#!/usr/bin/env python3
"""
Example: List MSSP Clients

Lists all clients managed by the MSSP account.

Usage:
    cd socaas-sdk
    python examples/list_clients.py
"""

import sys
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

    # List clients
    print("Listing MSSP clients...\n")
    clients = client.list_clients()

    if not clients:
        print("No clients found (this may not be an MSSP account)")
        return

    print(f"Found {len(clients)} clients:\n")
    for c in clients:
        print(f"  Name: {c.get('client_name')}")
        print(f"  UUID: {c.get('client_uuid')}")
        print(f"  Modified: {c.get('modify_date')}")
        print()

    # Get alerts for first client
    if clients:
        client_uuid = clients[0]['client_uuid']
        print(f"Getting alerts for '{clients[0]['client_name']}'...")
        alerts = client.get_alerts_by_client(client_uuid)
        print(f"  Found {len(alerts)} alerts for this client")


if __name__ == "__main__":
    main()
