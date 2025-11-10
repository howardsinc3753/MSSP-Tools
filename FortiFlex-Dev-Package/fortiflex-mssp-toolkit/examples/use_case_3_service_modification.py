#!/usr/bin/env python3
"""
Use Case 3: Service Modification - Adding/Removing Addons

Business Scenario:
    Customer wants to add or remove service addons (FortiAnalyzer Cloud, SOCaaS, etc.)

Usage:
    python use_case_3_service_modification.py

This script demonstrates:
    1. Viewing current configuration parameters
    2. Calculating cost difference before/after changes
    3. Two approaches:
       - Update existing config (affects ALL devices)
       - Create new config (selective upgrade)
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


def show_config_details(client: FortiFlexClient, config_id: int):
    """
    Show detailed configuration including all parameters.
    
    Args:
        client: FortiFlexClient instance
        config_id: Configuration ID
        
    Returns:
        dict: Configuration details
    """
    configs = client.list_configs()
    config = next((c for c in configs['configs'] if c['id'] == config_id), None)
    
    if not config:
        raise ValueError(f"Config {config_id} not found")
    
    print(f"\n{'='*80}")
    print(f"CONFIGURATION DETAILS - ID: {config_id}")
    print(f"{'='*80}\n")
    
    print(f"Name: {config['name']}")
    print(f"Product: {config['productType']['name']}")
    print(f"Status: {config['status']}")
    print()
    
    print("Current Parameters:")
    for param in config.get('parameters', []):
        print(f"  {param['name']}: {param['value']}")
    print()
    
    return config


def calculate_cost_comparison(
    client: FortiFlexClient,
    product_type_id: int,
    old_params: list,
    new_params: list
):
    """
    Compare costs before and after parameter changes.
    
    Args:
        client: FortiFlexClient instance
        product_type_id: Product type ID
        old_params: Current parameters
        new_params: Proposed parameters
        
    Returns:
        dict: Cost comparison
    """
    print(f"\n{'='*80}")
    print("COST COMPARISON")
    print(f"{'='*80}\n")
    
    # Calculate old cost
    old_result = client.calculate_points(
        product_type_id=product_type_id,
        count=1,
        parameters=old_params
    )
    old_cost = old_result['points']['current']
    
    # Calculate new cost
    new_result = client.calculate_points(
        product_type_id=product_type_id,
        count=1,
        parameters=new_params
    )
    new_cost = new_result['points']['current']
    
    difference = new_cost - old_cost
    percent_change = (difference / old_cost * 100) if old_cost > 0 else 0
    
    print(f"Current Cost: {old_cost:.2f} points/day per device")
    print(f"New Cost: {new_cost:.2f} points/day per device")
    print(f"Difference: {difference:+.2f} points/day per device ({percent_change:+.1f}%)")
    print()
    
    return {
        'old_cost': old_cost,
        'new_cost': new_cost,
        'difference': difference,
        'percent_change': percent_change
    }


def update_configuration(
    client: FortiFlexClient,
    config_id: int,
    new_params: list
):
    """
    Update configuration with new parameters.
    
    WARNING: This affects ALL entitlements using this config!
    
    Args:
        client: FortiFlexClient instance
        config_id: Configuration ID
        new_params: New parameter list
    """
    print(f"\n{'='*80}")
    print("UPDATING CONFIGURATION")
    print(f"{'='*80}\n")
    
    print(f"[WARNING] This will affect ALL devices using config {config_id}")
    print()
    
    try:
        result = client.update_config(
            config_id=config_id,
            parameters=new_params
        )
        
        print("[SUCCESS] Configuration updated")
        print(f"  All devices will now use the new service bundle")
        print(f"  Cost changes apply to all devices")
        print()
        
        return result
        
    except Exception as e:
        print(f"[ERROR] Update failed: {e}")
        raise


def main():
    """Main execution."""
    
    parser = argparse.ArgumentParser(
        description='Modify service addons for customer'
    )
    
    parser.add_argument(
        '--config-id',
        type=int,
        required=True,
        help='Configuration ID to modify'
    )
    
    args = parser.parse_args()
    
    # Load credentials
    print(f"\n{'='*80}")
    print("FORTIFLEX SERVICE MODIFICATION")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    
    creds = load_credentials()
    API_USERNAME = creds['fortiflex']['api_username']
    API_PASSWORD = creds['fortiflex']['api_password']
    PROGRAM_SN = creds['fortiflex']['program_serial_number']
    
    try:
        # Authenticate
        print("Authenticating...")
        token = get_oauth_token(API_USERNAME, API_PASSWORD, client_id="flexvm")
        print("[SUCCESS]\n")
        
        # Initialize client
        client = FortiFlexClient(token, PROGRAM_SN)
        
        # Show current config
        config = show_config_details(client, args.config_id)
        
        # Convert parameters to list of dicts for API
        current_params = [
            {"id": p['id'], "value": p['value']} 
            for p in config['parameters']
        ]
        
        # Example: Add SOCaaS addon to FortiGate config
        # This is a demo - you'd customize based on actual needs
        print("Example Modification: Adding SOCaaS addon")
        print()

        product_type_id = config['productType']['id']
        product_type_name = config['productType']['name']

        # Support both FortiGate VM (1) and FortiGate Hardware (101)
        if product_type_id not in [1, 101]:
            print(f"[ERROR] This example only works for FortiGate products")
            print(f"        Your config is: {product_type_name} (ID {product_type_id})")
            print(f"        Supported: FortiGate-VM (1), FortiGate-Hardware (101)")
            return 1

        print(f"Product Type: {product_type_name} (ID {product_type_id})")
        print()

        # Build new parameters (current + SOCaaS)
        new_params = current_params.copy()

        # Determine which addon parameter to use
        if product_type_id == 1:
            # FortiGate VM uses parameter IDs: 43, 44, 45
            addon_param_id = 44  # Cloud services
            addon_value = "FGTSOCA"  # SOCaaS for VM
            print("Example: Adding/Removing SOCaaS (FortiGate VM)")
        elif product_type_id == 101:
            # FortiGate Hardware uses parameter ID: 29
            addon_param_id = 29
            addon_value = "FGHWSOCA"  # SOCaaS for Hardware
            print("Example: Adding/Removing SOCaaS (FortiGate Hardware)")

        print()

        # Check if addon already exists
        has_addon = any(
            p.get('id') == addon_param_id and p.get('value') == addon_value
            for p in new_params
        )

        if has_addon:
            print("[INFO] SOCaaS already configured - will remove it")
            new_params = [p for p in new_params
                          if not (p.get('id') == addon_param_id and p.get('value') == addon_value)]
            action = "Removing SOCaaS"
        else:
            print("[INFO] Adding SOCaaS addon")
            new_params.append({"id": addon_param_id, "value": addon_value})
            action = "Adding SOCaaS"
        
        print()
        print(f"Proposed Change: {action}")
        print()
        
        # Calculate cost difference
        cost_info = calculate_cost_comparison(
            client,
            config['productType']['id'],
            current_params,
            new_params
        )
        
        # Confirm
        print(f"This will affect ALL devices using config {args.config_id}")
        response = input(f"{action}? (yes/no): ")
        if response.lower() != 'yes':
            print("\nCancelled")
            return 0
        
        # Update configuration
        result = update_configuration(client, args.config_id, new_params)
        
        # Summary
        print(f"{'='*80}")
        print("MODIFICATION SUMMARY")
        print(f"{'='*80}")
        print(f"Configuration: {config['name']}")
        print(f"Action: {action}")
        print(f"Cost Impact: {cost_info['difference']:+.2f} points/day per device")
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
