#!/usr/bin/env python3
"""
Use Case 2: Service Expansion - Adding New Devices

Business Scenario:
    Existing customer needs to add more devices to their deployment.
    Use existing configuration, create new entitlements only.

Usage:
    python use_case_2_service_expansion.py

This script demonstrates:
    1. Finding existing customer configurations
    2. Adding new hardware entitlements to existing configs
    3. Billing starts immediately (same day)
"""

import sys
import os
import json
import argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fortiflex_client import FortiFlexClient, get_oauth_token


def load_credentials():
    """Load API credentials from central config file."""
    config_file = os.path.join(
        os.path.dirname(__file__), '..', 'testing', 'config', 'credentials.json'
    )

    if not os.path.exists(config_file):
        print("[ERROR] credentials.json not found!")
        sys.exit(1)

    with open(config_file, 'r') as f:
        return json.load(f)


def list_customer_configs(client: FortiFlexClient, account_id: int):
    """
    List all configurations for a specific customer account.
    
    Args:
        client: FortiFlexClient instance
        account_id: Customer account ID
        
    Returns:
        list: Customer configurations
    """
    print(f"\n{'='*80}")
    print(f"CUSTOMER CONFIGURATIONS - Account ID: {account_id}")
    print(f"{'='*80}\n")
    
    # Get all configs filtered by account
    configs = client.list_configs(account_id=account_id)
    
    if not configs or 'configs' not in configs:
        print("No configurations found for this customer.")
        return []
    
    config_list = configs['configs']
    
    # Display table
    print(f"{'ID':<8} {'Name':<35} {'Product Type':<25} {'Status':<10}")
    print("-" * 80)
    
    for cfg in config_list:
        cfg_id = cfg.get('id', 'N/A')
        name = cfg.get('name', 'Unknown')
        product = cfg.get('productType', {}).get('name', 'Unknown')
        status = cfg.get('status', 'Unknown')
        
        print(f"{cfg_id:<8} {name:<35} {product:<25} {status:<10}")
    
    print()
    return config_list


def add_devices(
    client: FortiFlexClient,
    config_id: int,
    serial_numbers: list
):
    """
    Add new hardware devices to existing configuration.
    
    Args:
        client: FortiFlexClient instance
        config_id: Configuration ID to add devices to
        serial_numbers: List of device serial numbers
        
    Returns:
        list: Created entitlements
    """
    print(f"\n{'='*80}")
    print(f"ADDING {len(serial_numbers)} DEVICES TO CONFIG {config_id}")
    print(f"{'='*80}\n")
    
    print("Serial numbers to add:")
    for serial in serial_numbers:
        print(f"  - {serial}")
    print()
    
    try:
        # Create hardware entitlements
        result = client.create_hardware_entitlements(
            config_id=config_id,
            serial_numbers=serial_numbers
        )
        
        entitlements = result['entitlements']
        
        print(f"[SUCCESS] Created {len(entitlements)} new entitlements\n")
        
        print("Details:")
        for ent in entitlements:
            print(f"  Serial: {ent['serialNumber']}")
            print(f"  Start Date: {ent['startDate']}")
            print(f"  Status: {ent.get('status', 'ACTIVE')}")
            print()
        
        return entitlements
        
    except Exception as e:
        print(f"[ERROR] Failed to add devices: {e}")
        raise


def main():
    """Main execution."""
    
    parser = argparse.ArgumentParser(
        description='Add devices to existing customer deployment'
    )
    
    parser.add_argument(
        '--config-id',
        type=int,
        help='Configuration ID to add devices to (or list configs to choose)'
    )
    
    parser.add_argument(
        '--serials',
        type=str,
        nargs='+',
        help='Serial numbers of new devices (space-separated)'
    )
    
    args = parser.parse_args()
    
    # Load credentials
    print(f"\n{'='*80}")
    print("FORTIFLEX SERVICE EXPANSION")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    
    creds = load_credentials()
    API_USERNAME = creds['fortiflex']['api_username']
    API_PASSWORD = creds['fortiflex']['api_password']
    PROGRAM_SN = creds['fortiflex']['program_serial_number']
    ACCOUNT_ID = creds['fortiflex'].get('account_id', 12345)
    
    try:
        # Authenticate
        print("Authenticating...")
        token = get_oauth_token(API_USERNAME, API_PASSWORD, client_id="flexvm")
        print("[SUCCESS]\n")
        
        # Initialize client
        client = FortiFlexClient(token, PROGRAM_SN)
        
        # List customer configs
        configs = list_customer_configs(client, ACCOUNT_ID)
        
        if not configs:
            print("No configurations found. Run onboarding first.")
            return 1
        
        # Get config ID
        if args.config_id:
            config_id = args.config_id
        else:
            # Prompt user to choose
            config_id = int(input("\nEnter Config ID to add devices to: "))
        
        # Verify config exists
        selected_config = next((c for c in configs if c['id'] == config_id), None)
        if not selected_config:
            print(f"[ERROR] Config ID {config_id} not found")
            return 1
        
        print(f"\nSelected Configuration:")
        print(f"  ID: {selected_config['id']}")
        print(f"  Name: {selected_config['name']}")
        print(f"  Product: {selected_config['productType']['name']}")
        
        # Get serial numbers
        if args.serials:
            serial_numbers = args.serials
        else:
            # Prompt for serial numbers
            print("\nEnter serial numbers (one per line, empty line to finish):")
            serial_numbers = []
            while True:
                serial = input("  Serial: ").strip()
                if not serial:
                    break
                serial_numbers.append(serial)
        
        if not serial_numbers:
            print("[ERROR] No serial numbers provided")
            return 1
        
        # Confirm
        print(f"\nAbout to add {len(serial_numbers)} device(s) to config {config_id}")
        response = input("Proceed? (yes/no): ")
        if response.lower() != 'yes':
            print("\nCancelled")
            return 0
        
        # Add devices
        entitlements = add_devices(client, config_id, serial_numbers)
        
        # Summary
        print(f"{'='*80}")
        print("EXPANSION SUMMARY")
        print(f"{'='*80}")
        print(f"Configuration: {selected_config['name']}")
        print(f"Devices Added: {len(entitlements)}")
        print(f"Billing: Starts today")
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
