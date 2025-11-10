#!/usr/bin/env python3
"""
Use Case 1: Customer Onboarding - SIMPLE TEST VERSION

This is a simplified test version that creates just ONE configuration
to verify the API works correctly before running the full onboarding.

What this script does:
1. Authenticates with FortiFlex API
2. Creates ONE configuration (FortiGate VM 04 with UTP bundle)
3. Creates ONE VM entitlement (no hardware serial number needed)
4. Shows the results

This is SAFE to test because:
- It only creates 1 VM entitlement (not hardware)
- You can easily delete it from the FortiFlex portal if needed
- It helps verify the API workflow works
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fortiflex_client import FortiFlexClient, get_oauth_token


def load_credentials():
    """Load credentials from config file."""
    config_file = os.path.join(os.path.dirname(__file__), '..', 'testing', 'config', 'credentials.json')

    if not os.path.exists(config_file):
        print("[ERROR] credentials.json not found!")
        print(f"   Expected location: {config_file}")
        print("\n   Please run: python testing\\discover_program.py")
        sys.exit(1)

    with open(config_file, 'r') as f:
        return json.load(f)


def test_simple_onboarding(client: FortiFlexClient, account_id: int):
    """
    Test simple onboarding with ONE VM configuration.

    Args:
        client: FortiFlexClient instance
        account_id: Your FortiFlex account ID

    Returns:
        Created resources
    """
    print(f"\n{'='*80}")
    print("SIMPLE ONBOARDING TEST - Creating 1 FortiGate VM Config")
    print(f"{'='*80}\n")

    # Configuration details
    test_config = {
        'name': f'TEST-FGT-VM-{datetime.now().strftime("%Y%m%d-%H%M%S")}',
        'product_type_id': 1,  # FortiGate-VM
        'parameters': [
            {"id": 1, "value": "4"},       # CPU: 4 cores
            {"id": 2, "value": "UTP"},     # Bundle: UTP
            {"id": 10, "value": "0"},      # VDOM: 0 (unlimited)
            {"id": 43, "value": "NONE"},   # Additional services: None
            {"id": 44, "value": "NONE"},   # Cloud services: None
            {"id": 45, "value": "NONE"}    # Support: None
        ]
    }

    print("Configuration Details:")
    print(f"  Name: {test_config['name']}")
    print(f"  Product: FortiGate-VM")
    print(f"  CPU Cores: 4")
    print(f"  Bundle: UTP (Unified Threat Protection)")
    print(f"  Account ID: {account_id}\n")

    # Step 1: Calculate cost estimate
    print(f"{'='*80}")
    print("Step 1: Calculating point cost...")
    print("-" * 80)

    try:
        cost_result = client.calculate_points(
            product_type_id=test_config['product_type_id'],
            count=1,
            parameters=test_config['parameters']
        )

        daily_cost = cost_result['points']['current']
        monthly_cost = daily_cost * 30
        annual_cost = daily_cost * 365

        print(f"\nPoint Cost Estimate:")
        print(f"  Daily:   {daily_cost:>10.2f} points/day")
        print(f"  Monthly: {monthly_cost:>10.2f} points/month")
        print(f"  Annual:  {annual_cost:>10.2f} points/year")
        print()

    except Exception as e:
        print(f"[WARNING] Could not calculate costs: {e}")
        print("Continuing with configuration creation...\n")

    # Step 2: Create configuration
    print(f"{'='*80}")
    print("Step 2: Creating configuration...")
    print("-" * 80)

    try:
        config_result = client.create_config(
            name=test_config['name'],
            product_type_id=test_config['product_type_id'],
            account_id=account_id,
            parameters=test_config['parameters']
        )

        config_id = config_result['configs']['id']
        print(f"\n[SUCCESS] Configuration created successfully!")
        print(f"   Config ID: {config_id}")
        print(f"   Name: {test_config['name']}")
        print()

    except Exception as e:
        print(f"\n[ERROR] Failed to create configuration: {e}")
        raise

    # Step 3: Create VM entitlement
    print(f"{'='*80}")
    print("Step 3: Creating VM entitlement...")
    print("-" * 80)

    # Small delay to ensure configuration is fully propagated
    import time
    print("Waiting 2 seconds for configuration to propagate...")
    time.sleep(2)

    try:
        entitlement_result = client.create_cloud_entitlements(
            config_id=config_id,
            count=1
        )

        # API returns single entitlement, wrap in list for consistent handling
        entitlements = entitlement_result.get('entitlements', [])

        # If API returned single object instead of array, wrap it
        if not entitlements and entitlement_result:
            # Check if response has entitlement fields directly
            if 'serialNumber' in entitlement_result:
                entitlements = [entitlement_result]

        if not entitlements:
            print("[WARNING] No entitlements returned in response")
            print(f"Response: {json.dumps(entitlement_result, indent=2)}")
            return None

        ent = entitlements[0]

        print(f"\n[SUCCESS] VM entitlement created successfully!")
        print(f"   Serial Number: {ent.get('serialNumber', 'N/A')}")
        print(f"   Token: {ent.get('token', 'N/A')[:40]}..." if ent.get('token') else "   Token: N/A")
        print(f"   Start Date: {ent.get('startDate', 'N/A')}")
        print(f"   End Date: {ent.get('endDate', 'N/A')}")
        print(f"   Status: {ent.get('status', 'N/A')}")
        print()

    except Exception as e:
        print(f"\n[ERROR] Failed to create entitlement: {e}")
        raise

    # Summary
    print(f"{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")
    print(f"[SUCCESS] Configuration created: {test_config['name']} (ID: {config_id})")
    print(f"[SUCCESS] Entitlement created: {ent.get('serialNumber', 'N/A')}")
    print(f"[SUCCESS] Status: {ent.get('status', 'UNKNOWN')}")
    print()
    print("[NOTE] This is a test entitlement. You can:")
    print("       - View it in the FortiFlex portal")
    print("       - Use the serial number to deploy a VM")
    print("       - Delete it from the portal if you don't need it")
    print(f"{'='*80}\n")

    return {
        'config_id': config_id,
        'config_name': test_config['name'],
        'entitlement': ent
    }


def main():
    """Main execution."""

    # Load credentials
    creds = load_credentials()
    API_USERNAME = creds['fortiflex']['api_username']
    API_PASSWORD = creds['fortiflex']['api_password']
    PROGRAM_SN = creds['fortiflex']['program_serial_number']

    # Your actual account ID from testing
    ACCOUNT_ID = YOUR_ACCOUNT_ID  # Account YOUR_ACCOUNT_ID/MSSP Arcane LLC

    try:
        print(f"\n{'='*80}")
        print("USE CASE 1 - CUSTOMER ONBOARDING - SIMPLE TEST")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")

        # Authenticate
        print("Authenticating with FortiFlex API...")
        token = get_oauth_token(API_USERNAME, API_PASSWORD, client_id="flexvm")
        print("[SUCCESS] Authentication successful\n")

        # Initialize client
        client = FortiFlexClient(token, PROGRAM_SN)
        print(f"Program Serial Number: {PROGRAM_SN}")
        print(f"Account ID: {ACCOUNT_ID}\n")

        # Confirm with user
        print("[WARNING] This will CREATE a new configuration and VM entitlement.")
        print("   This is a real operation that will:")
        print("   - Create 1 FortiGate VM configuration")
        print("   - Generate 1 VM license/entitlement")
        print("   - Start consuming points when the VM is deployed")
        print()

        response = input("Continue? (yes/no): ")

        if response.lower() not in ['yes', 'y']:
            print("\n[INFO] Operation cancelled by user.")
            return 0

        print()

        # Run test onboarding
        result = test_simple_onboarding(client, ACCOUNT_ID)

        if result:
            # Save results to file
            output_file = f"test_onboarding_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'program_serial': PROGRAM_SN,
                    'account_id': ACCOUNT_ID,
                    'result': result
                }, f, indent=2)

            print(f"[SUCCESS] Results saved to: {output_file}\n")

        print(f"{'='*80}")
        print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")

        return 0

    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
