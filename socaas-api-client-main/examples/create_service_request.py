#!/usr/bin/env python3
"""
Example: Create SOCaaS Service Request

This script demonstrates how to create a new service request.

Usage:
    python create_service_request.py --title "Request Title" --type "Whitelist Request" --notes "Description"
    python create_service_request.py --title "Portal Access" --type "Portal Access" --notes "Need access" --email notify@example.com
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from SOCaaSClient import SOCaaSClient

load_dotenv()

# Valid service request types
VALID_TYPES = [
    "Portal Access",
    "Whitelist Request",
    "General Inquiry",
    "Device Onboarding"
]


def main():
    parser = argparse.ArgumentParser(description="Create a SOCaaS Service Request")
    parser.add_argument("--title", required=True, help="Service request title")
    parser.add_argument("--type", required=True, choices=VALID_TYPES, help="Request type")
    parser.add_argument("--notes", required=True, help="Request description/notes")
    parser.add_argument("--email", help="Notification email (optional)")
    parser.add_argument("--client", help="Client name (required for MSSPs with multiple clients)")
    args = parser.parse_args()

    # Load credentials
    username = os.getenv("USERNAME")
    password = os.getenv("PASSWORD")
    client_id = os.getenv("CLIENT_ID", "socaas")
    base_url = os.getenv("BASE_URL", "https://socaas.mss.fortinet.com")
    auth_url = os.getenv("AUTH_URL", "https://customerapiauth.fortinet.com/api/v1/oauth/token/")

    if not username or not password:
        print("Error: USERNAME and PASSWORD must be set in .env file")
        sys.exit(1)

    client = SOCaaSClient(
        username=username,
        password=password,
        client_id=client_id,
        authentication_url=auth_url,
        base_url=base_url
    )

    try:
        # Build request payload
        data = {
            "title": args.title,
            "type": args.type,
            "notes": args.notes,
        }

        if args.email:
            data["notification"] = args.email

        if args.client:
            data["client_name"] = args.client

        payload = {
            "param": {
                "data": data
            }
        }

        print(f"\nCreating service request...")
        print(f"  Title: {args.title}")
        print(f"  Type: {args.type}")
        print(f"  Notes: {args.notes[:50]}..." if len(args.notes) > 50 else f"  Notes: {args.notes}")

        # Create service request
        response = client.request("POST", "/socaasAPI/v1/service-request", json=payload)

        result = response.get("result", {})
        status = result.get("status", -1)
        errors = result.get("errorArr", [])
        sr = result.get("data", {})

        if status != 0:
            print(f"\nAPI Error: {errors}")
            sys.exit(1)

        print(f"\nService request created successfully!")
        print(f"{'='*50}")
        print(f"  UUID: {sr.get('portal_uuid')}")
        print(f"  Name: {sr.get('name')}")
        print(f"  Type: {sr.get('type')}")
        print(f"  Status: {sr.get('status')}")
        print(f"  Notification: {sr.get('notification', 'N/A')}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
