#!/usr/bin/env python3
"""
List All Configuration IDs

Simple helper script to see all your FortiFlex configurations and their IDs.

Usage:
    python list_configs.py
    
    # With filtering
    python list_configs.py --filter "FGT"
    python list_configs.py --status ACTIVE
"""

import sys
import os
import json
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fortiflex_client import FortiFlexClient, get_oauth_token


def load_credentials():
    """Load API credentials."""
    config_file = os.path.join(
        os.path.dirname(__file__), '..', 'testing', 'config', 'credentials.json'
    )
    with open(config_file, 'r') as f:
        return json.load(f)


def list_all_configs(client: FortiFlexClient, name_filter: str = None, status_filter: str = None):
    """
    List all configurations with IDs.
    
    Args:
        client: FortiFlexClient instance
        name_filter: Optional filter by name (case-insensitive substring)
        status_filter: Optional filter by status (ACTIVE, DISABLED)
    """
    print(f"\n{'='*100}")
    print("ALL FORTIFLEX CONFIGURATIONS")
    print(f"{'='*100}\n")
    
    # Get all configs
    result = client.list_configs()
    configs = result.get('configs', [])
    
    if not configs:
        print("No configurations found.")
        return
    
    # Apply filters
    if name_filter:
        configs = [c for c in configs if name_filter.lower() in c.get('name', '').lower()]
    
    if status_filter:
        configs = [c for c in configs if c.get('status', '').upper() == status_filter.upper()]
    
    if not configs:
        print(f"No configurations found matching filters")
        if name_filter:
            print(f"  Name contains: {name_filter}")
        if status_filter:
            print(f"  Status: {status_filter}")
        return
    
    # Sort by name
    configs.sort(key=lambda x: x.get('name', ''))
    
    # Display table
    print(f"{'ID':<8} {'Name':<40} {'Product Type':<30} {'Status':<10}")
    print("-" * 100)
    
    for cfg in configs:
        cfg_id = cfg.get('id', 'N/A')
        name = cfg.get('name', 'Unknown')[:39]  # Truncate long names
        product = cfg.get('productType', {}).get('name', 'Unknown')[:29]
        status = cfg.get('status', 'Unknown')
        
        print(f"{cfg_id:<8} {name:<40} {product:<30} {status:<10}")
    
    print()
    print(f"Total: {len(configs)} configuration(s)")
    
    if name_filter or status_filter:
        print(f"Filters applied:")
        if name_filter:
            print(f"  Name contains: '{name_filter}'")
        if status_filter:
            print(f"  Status: {status_filter}")
    
    print()


def main():
    """Main execution."""
    
    parser = argparse.ArgumentParser(
        description='List all FortiFlex configuration IDs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all configs
  python list_configs.py
  
  # Find FortiGate configs
  python list_configs.py --filter "FGT"
  
  # Find FortiManager configs
  python list_configs.py --filter "FMG"
  
  # Show only active configs
  python list_configs.py --status ACTIVE
  
  # Find customer by name
  python list_configs.py --filter "Customer-A"
        """
    )
    
    parser.add_argument(
        '--filter',
        type=str,
        help='Filter by name (case-insensitive substring match)'
    )
    
    parser.add_argument(
        '--status',
        type=str,
        choices=['ACTIVE', 'DISABLED'],
        help='Filter by status'
    )
    
    args = parser.parse_args()
    
    # Load credentials
    creds = load_credentials()
    API_USERNAME = creds['fortiflex']['api_username']
    API_PASSWORD = creds['fortiflex']['api_password']
    PROGRAM_SN = creds['fortiflex']['program_serial_number']
    
    try:
        # Authenticate
        print("\nAuthenticating...")
        token = get_oauth_token(API_USERNAME, API_PASSWORD, client_id="flexvm")
        print("[SUCCESS]\n")
        
        # Initialize client
        client = FortiFlexClient(token, PROGRAM_SN)
        
        # List configs
        list_all_configs(client, args.filter, args.status)
        
        return 0
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
