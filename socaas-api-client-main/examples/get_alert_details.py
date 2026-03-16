#!/usr/bin/env python3
"""
Example: Get SOCaaS Alert Details

This script retrieves detailed information for a specific alert by UUID.

Usage:
    python get_alert_details.py <alert_uuid>
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from SOCaaSClient import SOCaaSClient

load_dotenv()


def main():
    if len(sys.argv) < 2:
        print("Usage: python get_alert_details.py <alert_uuid>")
        print("Example: python get_alert_details.py 3a90b295-c110-4333-a361-469789cb5b16")
        sys.exit(1)

    alert_uuid = sys.argv[1]

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
        # Get alert details
        response = client.request("GET", f"/socaasAPI/v1/alert/{alert_uuid}")

        result = response.get("result", {})
        status = result.get("status", -1)
        errors = result.get("errorArr", [])
        alert = result.get("data", {})

        if status != 0:
            print(f"API Error: {errors}")
            sys.exit(1)

        # Display alert details
        print(f"\n{'='*60}")
        print(f"Alert Details: {alert.get('name')}")
        print(f"{'='*60}\n")

        print(f"UUID: {alert.get('uuid')}")
        print(f"ID: {alert.get('id')}")
        print(f"Status: {alert.get('status')}")
        print(f"Severity: {alert.get('severity', 'N/A')}")
        print(f"Client: {alert.get('client_name')}")
        print(f"\nDescription:")
        print(f"  {alert.get('description', 'N/A')}")
        print(f"\nClosure Notes:")
        print(f"  {alert.get('closure_notes') or 'None'}")
        print(f"\nAnalysis & Recommendation:")
        print(f"  {alert.get('analysis_recommendation') or 'None'}")

        # Show attachments
        attachments = alert.get("attachments", [])
        if attachments:
            print(f"\nAttachments ({len(attachments)}):")
            for att in attachments:
                file_info = att.get("file", {})
                print(f"  - {file_info.get('filename')} ({file_info.get('content_type')}, {file_info.get('size')} bytes)")
                print(f"    UUID: {file_info.get('portal_uuid')}")

        print()

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
