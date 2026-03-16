#!/usr/bin/env python3
"""
Example: Add Comment to Alert or Service Request

This script demonstrates how to add comments to alerts or service requests.

Usage:
    python add_comment.py alerts <alert_uuid> "Your comment here"
    python add_comment.py service_request <sr_uuid> "Your comment here"
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from SOCaaSClient import SOCaaSClient

load_dotenv()


def main():
    if len(sys.argv) < 4:
        print("Usage: python add_comment.py <module> <uuid> <comment>")
        print()
        print("Modules:")
        print("  alerts          - Add comment to an alert")
        print("  service_request - Add comment to a service request")
        print()
        print("Examples:")
        print('  python add_comment.py alerts 3a90b295-c110-4333-a361-469789cb5b16 "Investigating this alert"')
        print('  python add_comment.py service_request 04ad3519-e1a2-438f-b2b5-1299ea32893c "Request update"')
        sys.exit(1)

    module = sys.argv[1]
    uuid = sys.argv[2]
    comment_text = sys.argv[3]

    if module not in ["alerts", "service_request"]:
        print(f"Error: Invalid module '{module}'. Use 'alerts' or 'service_request'")
        sys.exit(1)

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
        # Create comment payload
        payload = {
            "param": {
                "data": {
                    "content": comment_text,
                    "related": module,
                    "related_uuid": uuid,
                    "tag": ""
                }
            }
        }

        # Post comment
        response = client.request("POST", "/socaasAPI/v1/comment", json=payload)

        result = response.get("result", {})
        status = result.get("status", -1)
        errors = result.get("errorArr", [])
        data = result.get("data", {})

        if status != 0:
            print(f"API Error: {errors}")
            sys.exit(1)

        print(f"\nComment added successfully!")
        print(f"  Content: {data.get('content')}")
        print(f"  Created by: {data.get('create_user')}")
        print(f"  Created at: {data.get('created_date')}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
