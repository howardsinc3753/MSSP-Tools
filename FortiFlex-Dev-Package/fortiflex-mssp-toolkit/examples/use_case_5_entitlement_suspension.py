#!/usr/bin/env python3
"""
Use Case 5: Customer Suspension/Offboarding - MSSP Edition

Business Scenario:
    In real MSSP deployments, all entitlements live in ONE root account.
    Configurations represent customers or service packages.
    
    Suspend by:
    1. Configuration ID (all devices for a customer/service)
    2. Specific serial number (one device)
    3. List of serial numbers (selective suspension)

Usage:
    # Suspend entire configuration (all entitlements using it)
    python use_case_5_customer_suspension.py --config-id 47456 --action suspend
    
    # Suspend one specific device
    python use_case_5_customer_suspension.py --serial FGT60FTK20001234 --action suspend
    
    # List what would be affected
    python use_case_5_customer_suspension.py --config-id 47456 --action list
"""

import sys
import os
import json
import argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fortiflex_client import FortiFlexClient, get_oauth_token


def load_credentials():
    """Load API credentials."""
    config_file = os.path.join(
        os.path.dirname(__file__), '..', 'testing', 'config', 'credentials.json'
    )
    with open(config_file, 'r') as f:
        return json.load(f)


def get_config_details(client: FortiFlexClient, config_id: int):
    """
    Get configuration details.
    
    Args:
        client: FortiFlexClient instance
        config_id: Configuration ID
        
    Returns:
        dict: Configuration details
    """
    configs = client.list_configs()
    config = next((c for c in configs['configs'] if c['id'] == config_id), None)
    
    if not config:
        raise ValueError(f"Configuration {config_id} not found")
    
    return config


def list_entitlements_by_config(client: FortiFlexClient, config_id: int, account_id: int):
    """
    List all entitlements using a specific configuration.

    NOTE: FortiFlex API doesn't have a "list entitlements by config" endpoint.
    We use consumption data (last 90 days) to find which devices use this config.

    Args:
        client: FortiFlexClient instance
        config_id: Configuration ID
        account_id: Account ID (required for consumption API)

    Returns:
        list: Entitlements found in consumption data
    """
    print(f"\n{'='*80}")
    print(f"ENTITLEMENTS FOR CONFIG ID: {config_id}")
    print(f"{'='*80}\n")

    # Get config details first
    config = get_config_details(client, config_id)

    print("Configuration Details:")
    print(f"  Name: {config['name']}")
    print(f"  Status: {config['status']}")
    print(f"  Product: {config['productType']['name']}")
    print()

    print("[NOTE] Searching consumption data (last 90 days) to find active entitlements...")
    print("       Only devices that have consumed points will appear.\n")

    # Get consumption data for last 90 days
    from datetime import datetime, timedelta
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=90)

    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    try:
        result = client.get_entitlement_points(
            config_id=config_id,
            account_id=account_id,
            start_date=start_str,
            end_date=end_str
        )

        consumption_data = result.get('entitlements', [])

        if not consumption_data:
            print("[INFO] No consumption data found for this configuration.")
            print("       This means either:")
            print("       1. No entitlements exist for this config")
            print("       2. Entitlements exist but haven't consumed points in 90 days")
            print("       3. Entitlements are in PENDING status (not activated yet)")
            print()
            return []

        # Extract unique serial numbers from consumption data
        serials_found = {}
        for item in consumption_data:
            serial = item.get('serialNumber')
            if serial:
                if serial not in serials_found:
                    serials_found[serial] = {
                        'serialNumber': serial,
                        'accountId': item.get('accountId'),
                        'points': item.get('points', 0),
                        'status': 'ACTIVE'  # Consuming points = active
                    }
                else:
                    # Accumulate points
                    serials_found[serial]['points'] += item.get('points', 0)

        entitlements = list(serials_found.values())

        # Display table
        print(f"[SUCCESS] Found {len(entitlements)} active entitlement(s)\n")
        print(f"{'Serial Number':<30} {'Status':<15} {'Total Points (90d)':>20}")
        print("-" * 70)

        for ent in sorted(entitlements, key=lambda x: x['points'], reverse=True):
            serial = ent['serialNumber']
            status = ent['status']
            points = ent['points']

            print(f"{serial:<30} {status:<15} {points:>20.2f}")

        print()
        return entitlements

    except Exception as e:
        print(f"[ERROR] Failed to retrieve consumption data: {e}")
        print("       Cannot determine which entitlements use this config")
        return []


def list_entitlement_by_serial(client: FortiFlexClient, serial_number: str, account_id: int):
    """
    Get details for a specific entitlement by serial number.

    NOTE: Uses consumption data to find the device. If device hasn't consumed
    points in last 90 days, it won't be found.

    Args:
        client: FortiFlexClient instance
        serial_number: Serial number to look up
        account_id: Account ID (required for consumption API)

    Returns:
        dict: Entitlement details (or basic serial info if not in consumption data)
    """
    print(f"\n{'='*80}")
    print(f"ENTITLEMENT DETAILS: {serial_number}")
    print(f"{'='*80}\n")

    print("[NOTE] Searching consumption data (last 90 days)...\n")

    # Get consumption data for last 90 days
    from datetime import datetime, timedelta
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=90)

    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    try:
        result = client.get_entitlement_points(
            account_id=account_id,
            serial_number=serial_number,
            start_date=start_str,
            end_date=end_str
        )

        consumption_data = result.get('entitlements', [])

        if not consumption_data:
            print(f"[INFO] No consumption data found for {serial_number}")
            print("       The device either:")
            print("       1. Doesn't exist")
            print("       2. Exists but hasn't consumed points in 90 days")
            print("       3. Is in PENDING status (not activated)")
            print()
            print("[INFO] Will attempt to suspend anyway...")
            print("       (API will return error if serial doesn't exist)\n")

            # Return minimal info so suspension can be attempted
            return {
                'serialNumber': serial_number,
                'status': 'UNKNOWN'
            }

        # Aggregate consumption data
        total_points = sum(item.get('points', 0) for item in consumption_data)
        account_id_found = consumption_data[0].get('accountId')

        # Display details
        print(f"Serial Number: {serial_number}")
        print(f"Status: ACTIVE (consuming points)")
        print(f"Account ID: {account_id_found}")
        print(f"Total Points (90 days): {total_points:.2f}")
        print()

        return {
            'serialNumber': serial_number,
            'status': 'ACTIVE',
            'accountId': account_id_found,
            'points': total_points
        }

    except Exception as e:
        print(f"[WARNING] Could not retrieve consumption data: {e}")
        print(f"          Will attempt to suspend anyway...\n")

        # Return minimal info
        return {
            'serialNumber': serial_number,
            'status': 'UNKNOWN'
        }


def suspend_entitlements(client: FortiFlexClient, entitlements: list):
    """
    Suspend (stop) entitlements.
    
    Args:
        client: FortiFlexClient instance
        entitlements: List of entitlements to suspend
        
    Returns:
        dict: Results
    """
    print(f"\n{'='*80}")
    print(f"SUSPENDING {len(entitlements)} ENTITLEMENT(S)")
    print(f"{'='*80}\n")
    
    print("[WARNING] Billing will stop TOMORROW for suspended devices")
    print("          Devices will lose FortiGuard services")
    print()
    
    results = {
        'suspended': [],
        'already_stopped': [],
        'errors': []
    }
    
    for ent in entitlements:
        serial = ent['serialNumber']
        status = ent.get('status', 'Unknown')
        
        # Skip if already stopped
        if status == 'STOPPED':
            print(f"  [SKIP] {serial} (already stopped)")
            results['already_stopped'].append(serial)
            continue
        
        try:
            # Stop entitlement
            client.stop_entitlement(serial)
            print(f"  [OK] {serial} (suspended)")
            results['suspended'].append(serial)
            
        except Exception as e:
            print(f"  [ERROR] {serial}: {e}")
            results['errors'].append({'serial': serial, 'error': str(e)})
    
    print()
    return results


def reactivate_entitlements(client: FortiFlexClient, entitlements: list):
    """
    Reactivate stopped entitlements.
    
    Args:
        client: FortiFlexClient instance
        entitlements: List of entitlements to reactivate
        
    Returns:
        dict: Results
    """
    print(f"\n{'='*80}")
    print(f"REACTIVATING ENTITLEMENT(S)")
    print(f"{'='*80}\n")
    
    print("[INFO] Billing will resume TODAY for reactivated devices")
    print()
    
    results = {
        'reactivated': [],
        'already_active': [],
        'errors': []
    }
    
    for ent in entitlements:
        serial = ent['serialNumber']
        status = ent.get('status', 'Unknown')
        
        # Skip if already active
        if status == 'ACTIVE':
            print(f"  [SKIP] {serial} (already active)")
            results['already_active'].append(serial)
            continue
        
        # Only reactivate if stopped
        if status != 'STOPPED':
            print(f"  [SKIP] {serial} (status: {status})")
            continue
        
        try:
            # Reactivate entitlement
            client.reactivate_entitlement(serial)
            print(f"  [OK] {serial} (reactivated)")
            results['reactivated'].append(serial)
            
        except Exception as e:
            print(f"  [ERROR] {serial}: {e}")
            results['errors'].append({'serial': serial, 'error': str(e)})
    
    print()
    return results


def disable_configuration(client: FortiFlexClient, config_id: int):
    """
    Disable a configuration (prevents new entitlements, doesn't affect existing).
    
    Args:
        client: FortiFlexClient instance
        config_id: Configuration ID to disable
    """
    print(f"\n{'='*80}")
    print(f"DISABLING CONFIGURATION {config_id}")
    print(f"{'='*80}\n")
    
    print("[INFO] Disabling configuration prevents NEW entitlements")
    print("       Existing entitlements must be stopped separately")
    print()
    
    try:
        client.disable_config(config_id)
        print(f"[SUCCESS] Configuration {config_id} disabled")
        print()
    except Exception as e:
        print(f"[ERROR] Failed to disable configuration: {e}")
        raise


def main():
    """Main execution."""
    
    parser = argparse.ArgumentParser(
        description='Suspend/reactivate services in MSSP environment',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all entitlements for a configuration
  python use_case_5_customer_suspension.py --config-id 47456 --action list

  # Suspend all devices in a configuration (e.g., customer non-payment)
  python use_case_5_customer_suspension.py --config-id 47456 --action suspend

  # Suspend one specific device
  python use_case_5_customer_suspension.py --serial FGT60FTK20001234 --action suspend

  # Reactivate a configuration after payment
  python use_case_5_customer_suspension.py --config-id 47456 --action reactivate

  # Disable configuration (prevent new entitlements)
  python use_case_5_customer_suspension.py --config-id 47456 --action disable-config
        """
    )
    
    parser.add_argument(
        '--config-id',
        type=int,
        help='Configuration ID (represents customer/service package)'
    )
    
    parser.add_argument(
        '--serial',
        type=str,
        help='Specific serial number to suspend/reactivate'
    )
    
    parser.add_argument(
        '--action',
        choices=['list', 'suspend', 'reactivate', 'disable-config'],
        required=True,
        help='Action to perform'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.config_id and not args.serial:
        print("[ERROR] Must specify either --config-id or --serial")
        return 1
    
    if args.config_id and args.serial:
        print("[ERROR] Cannot specify both --config-id and --serial")
        print("       Use --config-id for entire configuration")
        print("       Use --serial for one specific device")
        return 1
    
    # Load credentials
    print(f"\n{'='*80}")
    print("FORTIFLEX CUSTOMER SUSPENSION/OFFBOARDING")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    
    creds = load_credentials()
    API_USERNAME = creds['fortiflex']['api_username']
    API_PASSWORD = creds['fortiflex']['api_password']
    PROGRAM_SN = creds['fortiflex']['program_serial_number']
    ACCOUNT_ID = creds['fortiflex'].get('account_id')  # Required for consumption API

    try:
        # Authenticate
        print("Authenticating...")
        token = get_oauth_token(API_USERNAME, API_PASSWORD, client_id="flexvm")
        print("[SUCCESS]\n")

        # Initialize client
        client = FortiFlexClient(token, PROGRAM_SN)

        # Get entitlements based on input
        if args.config_id:
            # Get all entitlements for configuration
            entitlements = list_entitlements_by_config(client, args.config_id, ACCOUNT_ID)
            scope = f"Configuration {args.config_id}"
        else:
            # Get single entitlement by serial
            ent = list_entitlement_by_serial(client, args.serial, ACCOUNT_ID)
            if not ent:
                return 1
            entitlements = [ent]
            scope = f"Serial {args.serial}"
        
        if not entitlements and args.action != 'disable-config':
            print("[INFO] No entitlements found")
            return 0
        
        # Perform action
        if args.action == 'list':
            # Just list - already displayed above
            pass
            
        elif args.action == 'disable-config':
            if not args.config_id:
                print("[ERROR] --disable-config requires --config-id")
                return 1
            
            # Confirm
            response = input(f"Disable configuration {args.config_id}? (yes/no): ")
            if response.lower() != 'yes':
                print("\nCancelled")
                return 0
            
            disable_configuration(client, args.config_id)
            
        elif args.action == 'suspend':
            # Confirm suspension
            print(f"About to suspend {len(entitlements)} entitlement(s)")
            print(f"Scope: {scope}")
            response = input("Proceed with suspension? (yes/no): ")
            if response.lower() != 'yes':
                print("\nCancelled")
                return 0
            
            results = suspend_entitlements(client, entitlements)
            
            # Summary
            print(f"{'='*80}")
            print("SUSPENSION SUMMARY")
            print(f"{'='*80}")
            print(f"Scope: {scope}")
            print(f"Suspended: {len(results['suspended'])}")
            print(f"Already Stopped: {len(results['already_stopped'])}")
            print(f"Errors: {len(results['errors'])}")
            print(f"Status: [COMPLETE]")
            print(f"{'='*80}\n")
            
        elif args.action == 'reactivate':
            # Confirm reactivation
            print(f"About to reactivate stopped entitlements")
            print(f"Scope: {scope}")
            response = input("Proceed with reactivation? (yes/no): ")
            if response.lower() != 'yes':
                print("\nCancelled")
                return 0
            
            results = reactivate_entitlements(client, entitlements)
            
            # Summary
            print(f"{'='*80}")
            print("REACTIVATION SUMMARY")
            print(f"{'='*80}")
            print(f"Scope: {scope}")
            print(f"Reactivated: {len(results['reactivated'])}")
            print(f"Already Active: {len(results['already_active'])}")
            print(f"Errors: {len(results['errors'])}")
            print(f"Status: [COMPLETE]")
            print(f"{'='*80}\n")
        
        return 0
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
