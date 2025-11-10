#!/usr/bin/env python3
"""
Use Case 1: Customer Onboarding

Business Scenario:
    New customer signs MSSP contract. Provision initial infrastructure with:
    - FortiGate hardware
    - FortiSwitch
    - FortiAP
    - FortiEDR endpoint protection

Usage:
    python use_case_1_customer_onboarding.py

This script demonstrates:
    1. Cost estimation before provisioning
    2. Creating configurations for each product type
    3. Creating hardware entitlements (with serial numbers)
    4. Creating cloud service entitlements (without serial numbers)
    5. Summary report of what was created
"""

import sys
import os
import json
import argparse
from datetime import datetime

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fortiflex_client import FortiFlexClient, get_oauth_token


def load_credentials():
    """
    Load API credentials from central config file.
    
    Returns:
        dict: Credentials dictionary
    """
    config_file = os.path.join(
        os.path.dirname(__file__), '..', 'testing', 'config', 'credentials.json'
    )

    if not os.path.exists(config_file):
        print("[ERROR] credentials.json not found!")
        print(f"   Expected location: {config_file}")
        print("\n   Please run: python testing/discover_program.py")
        sys.exit(1)

    with open(config_file, 'r') as f:
        return json.load(f)


def calculate_costs(client: FortiFlexClient, customer_profile: dict):
    """
    Calculate estimated costs for all products before creating resources.
    
    Args:
        client: FortiFlexClient instance
        customer_profile: Customer configuration dict
        
    Returns:
        dict: Cost breakdown by product
    """
    print(f"\n{'='*80}")
    print("STEP 1: COST ESTIMATION")
    print(f"{'='*80}\n")
    
    costs = {}
    total_monthly = 0
    
    for product in customer_profile['products']:
        try:
            # Call calculator API
            result = client.calculate_points(
                product_type_id=product['product_type_id'],
                count=product.get('quantity', 1),
                parameters=product['parameters']
            )

            # Extract daily cost - handle both response formats
            daily_cost = result.get('points', 0)
            if isinstance(daily_cost, dict):
                # Format: {"points": {"current": 12.5}}
                daily_cost = daily_cost.get('current', 0)
            # else: Format: {"points": 12.5}

            quantity = product.get('quantity', 1)
            monthly_cost = daily_cost * quantity * 30

            costs[product['name']] = {
                'daily_per_device': daily_cost,
                'quantity': quantity,
                'monthly_total': monthly_cost
            }

            total_monthly += monthly_cost

            # Display
            print(f"{product['name']}:")
            print(f"  Quantity: {quantity}")
            print(f"  Cost per device: {daily_cost:.2f} points/day")
            print(f"  Monthly total: {monthly_cost:.2f} points")
            print()

        except Exception as e:
            print(f"[ERROR] Failed to calculate cost for {product['name']}: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    print(f"{'='*80}")
    print(f"ESTIMATED MONTHLY TOTAL: {total_monthly:.2f} points")
    print(f"{'='*80}\n")
    
    return {
        'by_product': costs,
        'total_monthly': total_monthly
    }


def create_configurations(
    client: FortiFlexClient,
    customer_profile: dict
):
    """
    Create FortiFlex configurations for each product type.
    
    Args:
        client: FortiFlexClient instance
        customer_profile: Customer configuration dict
        
    Returns:
        list: Created configuration details
    """
    print(f"\n{'='*80}")
    print("STEP 2: CREATE CONFIGURATIONS")
    print(f"{'='*80}\n")
    
    created_configs = []
    
    for product in customer_profile['products']:
        config_name = f"{customer_profile['name']}-{product['name']}"
        
        print(f"Creating configuration: {config_name}")
        print(f"  Product Type ID: {product['product_type_id']}")
        print(f"  Account ID: {customer_profile['account_id']}")
        
        try:
            # Create config via API
            result = client.create_config(
                name=config_name,
                product_type_id=product['product_type_id'],
                account_id=customer_profile['account_id'],
                parameters=product['parameters']
            )
            
            config_id = result['configs']['id']
            
            created_configs.append({
                'name': product['name'],
                'config_id': config_id,
                'config_name': config_name,
                'product': product
            })
            
            print(f"  [SUCCESS] Config ID: {config_id}\n")
            
        except Exception as e:
            print(f"  [ERROR] Failed: {e}\n")
            # Rollback: disable previously created configs
            print("Rolling back created configurations...")
            for cfg in created_configs:
                try:
                    client.disable_config(cfg['config_id'])
                    print(f"  Disabled config: {cfg['config_id']}")
                except:
                    pass
            raise
    
    return created_configs


def create_entitlements(
    client: FortiFlexClient,
    configurations: list
):
    """
    Create entitlements (licenses) for hardware and cloud services.
    
    Args:
        client: FortiFlexClient instance
        configurations: List of created configs
        
    Returns:
        list: All created entitlements
    """
    print(f"\n{'='*80}")
    print("STEP 3: CREATE ENTITLEMENTS")
    print(f"{'='*80}\n")
    
    all_entitlements = []
    
    for config in configurations:
        product = config['product']
        print(f"{config['name']}:")
        
        try:
            # Check if hardware (has serial numbers) or cloud (no serials)
            if product.get('serial_numbers'):
                # Hardware entitlements
                print(f"  Creating {len(product['serial_numbers'])} hardware entitlements...")
                
                result = client.create_hardware_entitlements(
                    config_id=config['config_id'],
                    serial_numbers=product['serial_numbers']
                )
                
                entitlements = result['entitlements']
                all_entitlements.extend(entitlements)
                
                print(f"  [SUCCESS] Created {len(entitlements)} hardware licenses")
                
                # Show first 3 as examples
                for i, ent in enumerate(entitlements[:3]):
                    print(f"    - {ent['serialNumber']} (starts: {ent['startDate']})")
                
                if len(entitlements) > 3:
                    print(f"    ... and {len(entitlements) - 3} more")
                
            else:
                # Cloud service entitlements
                print(f"  Creating cloud service entitlement...")
                
                result = client.create_cloud_entitlements(
                    config_id=config['config_id']
                )
                
                entitlements = result['entitlements']
                all_entitlements.extend(entitlements)
                
                print(f"  [SUCCESS] Created cloud license")
                print(f"    - Serial: {entitlements[0]['serialNumber']}")
                if 'token' in entitlements[0]:
                    print(f"    - Token: {entitlements[0]['token'][:30]}...")
            
            print()
            
        except Exception as e:
            print(f"  [ERROR] Failed: {e}\n")
            # Rollback: stop created entitlements
            print("Rolling back created entitlements...")
            for ent in all_entitlements:
                try:
                    client.stop_entitlement(ent['serialNumber'])
                    print(f"  Stopped: {ent['serialNumber']}")
                except:
                    pass
            raise
    
    return all_entitlements


def print_summary(
    customer_profile: dict,
    costs: dict,
    configurations: list,
    entitlements: list
):
    """
    Print onboarding summary report.
    
    Args:
        customer_profile: Customer data
        costs: Cost breakdown
        configurations: Created configs
        entitlements: Created entitlements
    """
    print(f"\n{'='*80}")
    print("ONBOARDING SUMMARY")
    print(f"{'='*80}\n")
    
    print(f"Customer Name: {customer_profile['name']}")
    print(f"Account ID: {customer_profile['account_id']}")
    print()
    
    print("Resources Created:")
    print(f"  Configurations: {len(configurations)}")
    print(f"  Total Entitlements: {len(entitlements)}")
    print()
    
    print("Entitlements by Type:")
    for config in configurations:
        product = config['product']
        if product.get('serial_numbers'):
            count = len(product['serial_numbers'])
            print(f"  {config['name']}: {count} hardware devices")
        else:
            print(f"  {config['name']}: 1 cloud service")
    print()
    
    print("Cost Breakdown:")
    for product_name, cost_info in costs['by_product'].items():
        print(f"  {product_name}:")
        print(f"    {cost_info['quantity']} devices × "
              f"{cost_info['daily_per_device']:.2f} points/day = "
              f"{cost_info['monthly_total']:.2f} points/month")
    print()
    
    print(f"Estimated Monthly Cost: {costs['total_monthly']:.2f} points")
    print()
    
    print("Status: [COMPLETE]")
    print(f"{'='*80}\n")


def main():
    """Main execution."""
    
    # Parse arguments
    parser = argparse.ArgumentParser(
        description='FortiFlex Customer Onboarding',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Calculate costs only, do not create resources'
    )
    
    args = parser.parse_args()
    
    # Load credentials
    print(f"\n{'='*80}")
    print("FORTIFLEX CUSTOMER ONBOARDING")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    
    creds = load_credentials()
    API_USERNAME = creds['fortiflex']['api_username']
    API_PASSWORD = creds['fortiflex']['api_password']
    PROGRAM_SN = creds['fortiflex']['program_serial_number']
    
    # Example customer profile
    # TODO: Replace with actual customer data
    customer_profile = {
        'name': 'Acme-Corp',
        'account_id': creds['fortiflex'].get('account_id', 12345),
        'products': [
            {
                'name': 'FGT-60F-UTP-FAZ',
                'product_type_id': 101,  # FortiGate Hardware
                'quantity': 3,
                'parameters': [
                    {"id": 27, "value": "FGT60F"},
                    {"id": 28, "value": "FGHWUTP"},
                    {"id": 29, "value": "FGHWFAZC"}
                ],
                'serial_numbers': [
                    # TODO: Replace with ACTUAL device serial numbers
                    "FGT60FTK20001234",
                    "FGT60FTK20001235",
                    "FGT60FTK20001236"
                ]
            },
            {
                'name': 'FSW-124F',
                'product_type_id': 103,  # FortiSwitch Hardware
                'quantity': 12,
                'parameters': [
                    {"id": 53, "value": "S124FP"},
                    {"id": 54, "value": "FSWHWFC247"}
                ],
                'serial_numbers': [
                    # TODO: Replace with ACTUAL device serial numbers
                    f"S124FPTK2000{i:04d}" for i in range(1001, 1013)
                ]
            },
            {
                'name': 'FAP-231F',
                'product_type_id': 102,  # FortiAP Hardware
                'quantity': 8,
                'parameters': [
                    {"id": 55, "value": "FP231F"},
                    {"id": 56, "value": "FAPHWFC247"},
                    {"id": 57, "value": "NONE"}
                ],
                'serial_numbers': [
                    # TODO: Replace with ACTUAL device serial numbers
                    f"FP231FTK2000{i:04d}" for i in range(2001, 2009)
                ]
            },
            {
                'name': 'EDR-250-Users',
                'product_type_id': 206,  # FortiEDR MSSP
                'quantity': 1,
                'parameters': [
                    {"id": 46, "value": "FEDRPDR"},
                    {"id": 47, "value": "250"},
                    {"id": 52, "value": "NONE"},
                    {"id": 76, "value": "1024"}
                ]
                # No serial_numbers = cloud service
            }
        ]
    }
    
    try:
        # Authenticate
        print("Authenticating with FortiFlex API...")
        token = get_oauth_token(API_USERNAME, API_PASSWORD, client_id="flexvm")
        print("[SUCCESS] Authenticated\n")
        
        # Initialize client
        client = FortiFlexClient(token, PROGRAM_SN)
        print(f"Program: {PROGRAM_SN}")
        print(f"Customer: {customer_profile['name']}\n")
        
        # Step 1: Calculate costs
        costs = calculate_costs(client, customer_profile)
        
        if args.dry_run:
            print("[DRY RUN] Stopping here - no resources created")
            return 0
        
        # Ask for confirmation
        response = input("Proceed with onboarding? (yes/no): ")
        if response.lower() != 'yes':
            print("\nOnboarding cancelled")
            return 0
        
        # Step 2: Create configurations
        configurations = create_configurations(client, customer_profile)
        
        # Step 3: Create entitlements
        entitlements = create_entitlements(client, configurations)
        
        # Print summary
        print_summary(customer_profile, costs, configurations, entitlements)
        
        # Save results
        output_file = f"onboarding_{customer_profile['name']}_{int(datetime.now().timestamp())}.json"
        with open(output_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'customer': customer_profile['name'],
                'account_id': customer_profile['account_id'],
                'costs': costs,
                'configurations': [{'id': c['config_id'], 'name': c['config_name']} 
                                   for c in configurations],
                'entitlements': [{'serial': e['serialNumber'], 'start': e.get('startDate')} 
                                 for e in entitlements]
            }, f, indent=2)
        
        print(f"Results saved to: {output_file}\n")
        
        return 0
        
    except Exception as e:
        print(f"\n[ERROR] Onboarding failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
