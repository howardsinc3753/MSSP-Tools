#!/usr/bin/env python3
"""
Example: List SOCaaS Alerts

This script demonstrates how to authenticate and retrieve alerts from the SOCaaS API.
"""

import os
import sys

# Add parent directory to path for SOCaaSClient import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from SOCaaSClient import SOCaaSClient

load_dotenv()


def main():
    # Load credentials from environment
    username = os.getenv("USERNAME")
    password = os.getenv("PASSWORD")
    client_id = os.getenv("CLIENT_ID", "socaas")
    base_url = os.getenv("BASE_URL", "https://socaas.mss.fortinet.com")
    auth_url = os.getenv("AUTH_URL", "https://customerapiauth.fortinet.com/api/v1/oauth/token/")

    if not username or not password:
        print("Error: USERNAME and PASSWORD must be set in .env file")
        print("Copy .env.example to .env and fill in your credentials")
        sys.exit(1)

    # Initialize client
    client = SOCaaSClient(
        username=username,
        password=password,
        client_id=client_id,
        authentication_url=auth_url,
        base_url=base_url
    )

    try:
        # Get alerts
        response = client.request("GET", "/socaasAPI/v1/alert")

        # Parse response
        result = response.get("result", {})
        status = result.get("status", -1)
        errors = result.get("errorArr", [])
        alerts = result.get("data", [])

        if status != 0:
            print(f"API Error: {errors}")
            sys.exit(1)

        # Display alerts
        print(f"\n{'='*60}")
        print(f"Found {len(alerts)} alert(s)")
        print(f"{'='*60}\n")

        for alert in alerts:
            print(f"ID: {alert.get('id')}")
            print(f"UUID: {alert.get('uuid')}")
            print(f"Name: {alert.get('name')}")
            print(f"Severity: {alert.get('severity')}")
            print(f"Status: {alert.get('status')}")
            print(f"SLA: {alert.get('sla')}")
            print(f"Client: {alert.get('client_name')}")
            print(f"Created: {alert.get('created_date')}")
            print(f"Modified: {alert.get('modified_date')}")
            print("-" * 60)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
