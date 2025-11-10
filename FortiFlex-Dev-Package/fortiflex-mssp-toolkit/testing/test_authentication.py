#!/usr/bin/env python3
"""
Test Authentication and Basic API Access

This script tests:
1. OAuth token generation
2. API connectivity
3. Basic configuration listing

Run this FIRST before testing other scripts.
"""

import sys
import os
import json

# Add src directory to path (go up one level from testing/ to root, then into src/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fortiflex_client import FortiFlexClient, get_oauth_token


def load_credentials():
    """Load credentials from config file."""
    config_file = os.path.join(os.path.dirname(__file__), 'config', 'credentials.json')

    if not os.path.exists(config_file):
        print("[ERROR] credentials.json not found!")
        print(f"   Expected location: {config_file}")
        print("\n   Please create config/credentials.json with your API credentials")
        sys.exit(1)

    with open(config_file, 'r') as f:
        return json.load(f)


def test_authentication():
    """Test 1: OAuth Authentication"""
    print("\n" + "="*70)
    print("TEST 1: OAuth Authentication")
    print("="*70)

    creds = load_credentials()

    try:
        print(f"\nAttempting authentication...")
        print(f"Username: {creds['fortiflex']['api_username']}")
        print(f"Client ID: {creds['fortiflex']['client_id']}")

        token = get_oauth_token(
            api_username=creds['fortiflex']['api_username'],
            api_password=creds['fortiflex']['api_password'],
            client_id=creds['fortiflex']['client_id']
        )

        print(f"\n[SUCCESS] Authentication successful!")
        print(f"Token (first 20 chars): {token[:20]}...")
        print(f"Token length: {len(token)} characters")

        return token

    except Exception as e:
        print(f"\n[FAILED] Authentication failed")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_program_info(client, program_sn):
    """Test 2: Get Program Information"""
    print("\n" + "="*70)
    print("TEST 2: Program Information")
    print("="*70)

    try:
        print(f"\nProgram Serial Number: {program_sn}")
        print(f"Attempting to list configurations...")

        result = client.list_configs()

        configs = result.get('configs', [])

        print(f"\n[SUCCESS] Retrieved program information")
        print(f"Total Configurations: {len(configs)}")

        if configs:
            print(f"\nSample Configuration:")
            config = configs[0]
            print(f"  ID: {config.get('id')}")
            print(f"  Name: {config.get('name')}")
            print(f"  Product Type: {config.get('productType', {}).get('name')}")
            print(f"  Status: {config.get('status')}")

        return True

    except Exception as e:
        print(f"\n[FAILED] Could not retrieve program info")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_multi_tenant_view(client):
    """Test 3: Multi-Tenant View"""
    print("\n" + "="*70)
    print("TEST 3: Multi-Tenant View")
    print("="*70)

    try:
        print(f"\nRetrieving multi-tenant view...")

        customers = client.get_multi_tenant_view()

        print(f"\n[SUCCESS] Retrieved multi-tenant data")
        print(f"Total Accounts: {len(customers)}")

        for account_id, configs in customers.items():
            print(f"\n  Account {account_id}:")
            print(f"    Configurations: {len(configs)}")

            # Count by product type
            product_types = {}
            for config in configs:
                prod_name = config['productType']['name']
                product_types[prod_name] = product_types.get(prod_name, 0) + 1

            for prod_type, count in product_types.items():
                print(f"      - {prod_type}: {count}")

        return True

    except Exception as e:
        print(f"\n[FAILED] Could not retrieve multi-tenant view")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all authentication tests."""

    print("\n" + "="*70)
    print("FORTIFLEX MSSP TOOLKIT - AUTHENTICATION TEST")
    print("="*70)

    # Load credentials
    try:
        creds = load_credentials()
        program_sn = creds['fortiflex']['program_serial_number']

        if program_sn == "ELAVMSXXXXXXXX":
            print("\n[WARNING] You're using the example program serial number!")
            print("   Please update config/credentials.json with your actual program SN")
            print("\n   Continue anyway? (y/n): ", end="")
            if input().strip().lower() != 'y':
                return 1
    except Exception as e:
        print(f"[ERROR] Error loading credentials: {e}")
        return 1

    # Test 1: Authentication
    token = test_authentication()
    if not token:
        print("\n[WARNING] Authentication failed - cannot proceed with other tests")
        return 1

    # Initialize client
    client = FortiFlexClient(token, program_sn)

    # Test 2: Program Info
    success = test_program_info(client, program_sn)
    if not success:
        print("\n[WARNING] Program info test failed - check your program serial number")
        return 1

    # Test 3: Multi-Tenant View
    test_multi_tenant_view(client)

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print("\n[PASS] Authentication: PASSED")
    print("[PASS] API Connectivity: PASSED")
    print("[PASS] Program Access: PASSED")
    print("\nYou can now proceed to test the use case examples!")
    print("="*70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
