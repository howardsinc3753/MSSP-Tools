#!/usr/bin/env python3
"""
Example: List SOCaaS Service Requests

This script retrieves and displays all service requests.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from SOCaaSClient import SOCaaSClient

load_dotenv()


def main():
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
        # Get service requests
        response = client.request("GET", "/socaasAPI/v1/service-request")

        result = response.get("result", {})
        status = result.get("status", -1)
        errors = result.get("errorArr", [])
        requests = result.get("data", [])

        if status != 0:
            print(f"API Error: {errors}")
            sys.exit(1)

        print(f"\n{'='*70}")
        print(f"Found {len(requests)} service request(s)")
        print(f"{'='*70}\n")

        for sr in requests:
            print(f"ID: {sr.get('id')}")
            print(f"UUID: {sr.get('uuid')}")
            print(f"Name: {sr.get('name')}")
            print(f"Type: {sr.get('type')}")
            print(f"Status: {sr.get('status')}")
            print(f"Notification: {sr.get('notification')}")
            print(f"Client: {sr.get('client_name')}")
            print(f"Created: {sr.get('created_date')}")
            print(f"Description: {sr.get('description', '')[:100]}...")
            print("-" * 70)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
