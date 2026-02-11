#!/usr/bin/env python3
"""
Example: Create Service Request

Creates a new service request (support ticket) in SOCaaS.

Usage:
    cd socaas-sdk
    python examples/create_service_request.py
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

    # Create a whitelist request
    print("Creating service request...\n")

    # NOTE: Uncomment to actually create a service request
    # new_sr = client.create_service_request(
    #     title="Whitelist Request - Test IP",
    #     request_type="whitelistrequest",
    #     notes="Please whitelist the following IP address: 192.168.1.100\n\nReason: Internal server for monitoring."
    # )
    # print(f"Created SR: {new_sr}")

    # Instead, just list existing service requests
    print("Listing existing service requests...\n")
    srs = client.list_service_requests()
    print(f"Found {len(srs)} service requests\n")

    for sr in srs[:5]:
        print(f"  [{sr.get('id')}] {sr.get('title')}")
        print(f"      Type: {sr.get('type')}")
        print(f"      Status: {sr.get('status')}")
        print()

    # Valid request types
    print("\nValid request types:")
    types = [
        "devicedecommissioning",
        "escalationmatrixupdate",
        "newmonitoringrequest",
        "newreportrequest",
        "portalaccess",
        "servicedecommissioning",
        "serviceenquiry",
        "technicalassitance",
        "whitelistrequest",
        "others"
    ]
    for t in types:
        print(f"  - {t}")


if __name__ == "__main__":
    main()
