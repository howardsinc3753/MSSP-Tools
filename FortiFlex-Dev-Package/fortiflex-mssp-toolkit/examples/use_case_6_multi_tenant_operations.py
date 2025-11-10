#!/usr/bin/env python3
"""
Use Case 6: Multi-Tenant Operations View

Business Scenario:
    MSSP operations team needs visibility across all customers.

Usage:
    python use_case_6_multi_tenant_operations.py

This script demonstrates:
    1. Viewing all customer accounts in program
    2. Configurations by customer
    3. Device counts by product type
    4. Cross-customer consumption analysis
"""

import sys
import os
import json
import argparse
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fortiflex_client import FortiFlexClient, get_oauth_token


def load_credentials():
    """Load API credentials."""
    config_file = os.path.join(
        os.path.dirname(__file__), '..', 'testing', 'config', 'credentials.json'
    )
    with open(config_file, 'r') as f:
        return json.load(f)


def get_multi_tenant_view(client: FortiFlexClient):
    """
    Get configurations grouped by customer account.
    
    Args:
        client: FortiFlexClient instance
        
    Returns:
        dict: Configurations by account ID
    """
    print(f"\n{'='*80}")
    print("MULTI-TENANT OPERATIONS VIEW")
    print(f"{'='*80}\n")
    
    # Get ALL configurations (no account filter)
    configs_result = client.list_configs()
    all_configs = configs_result.get('configs', [])
    
    if not all_configs:
        print("No configurations found.")
        return {}
    
    # Group by account ID
    by_account = defaultdict(list)
    for config in all_configs:
        account_id = config.get('accountId')
        if account_id:
            by_account[account_id].append(config)
    
    print(f"[SUCCESS] Found {len(all_configs)} configurations across {len(by_account)} customer account(s)\n")
    
    return dict(by_account)


def display_customer_summary(by_account: dict):
    """
    Display summary of all customer accounts.
    
    Args:
        by_account: Configurations grouped by account ID
    """
    print(f"{'='*80}")
    print("CUSTOMER SUMMARY")
    print(f"{'='*80}\n")
    
    print(f"{'Account ID':<15} {'Configs':<10} {'Product Types':<50}")
    print("-" * 80)
    
    for account_id in sorted(by_account.keys()):
        configs = by_account[account_id]
        
        # Count by product type
        product_counts = defaultdict(int)
        for config in configs:
            product_name = config.get('productType', {}).get('name', 'Unknown')
            product_counts[product_name] += 1
        
        # Format product summary
        product_summary = ', '.join([f"{name}({count})" for name, count in product_counts.items()])
        
        print(f"{account_id:<15} {len(configs):<10} {product_summary:<50}")
    
    print()


def display_customer_details(by_account: dict, account_id: int = None):
    """
    Display detailed view of customer configurations.
    
    Args:
        by_account: Configurations grouped by account ID
        account_id: Optional account ID to filter
    """
    if account_id:
        accounts_to_show = {account_id: by_account.get(account_id, [])}
    else:
        accounts_to_show = by_account
    
    for acc_id, configs in accounts_to_show.items():
        print(f"\n{'='*80}")
        print(f"ACCOUNT ID: {acc_id}")
        print(f"{'='*80}\n")
        
        if not configs:
            print("  No configurations found\n")
            continue
        
        print(f"{'Config ID':<10} {'Name':<35} {'Product':<25} {'Status':<10}")
        print("-" * 85)
        
        for config in configs:
            cfg_id = config.get('id', 'N/A')
            name = config.get('name', 'Unknown')
            product = config.get('productType', {}).get('name', 'Unknown')
            status = config.get('status', 'Unknown')
            
            print(f"{cfg_id:<10} {name:<35} {product:<25} {status:<10}")
        
        print()


def get_cross_customer_consumption(client: FortiFlexClient, days_back: int = 7):
    """
    Get consumption across all customers for analysis.
    
    Args:
        client: FortiFlexClient instance
        days_back: Number of days to analyze
        
    Returns:
        dict: Consumption by account
    """
    print(f"\n{'='*80}")
    print(f"CROSS-CUSTOMER CONSUMPTION - LAST {days_back} DAYS")
    print(f"{'='*80}\n")
    
    # Calculate date range
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days_back)
    
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    print(f"Date Range: {start_str} to {end_str}\n")
    
    try:
        # Get consumption for all accounts (no account filter)
        result = client.get_entitlement_points(
            start_date=start_str,
            end_date=end_str
        )
        
        entitlements = result.get('entitlements', [])
        
        if not entitlements:
            print("[INFO] No consumption data available")
            return {}
        
        # Group by account
        by_account = defaultdict(lambda: {'points': 0, 'devices': set()})
        
        for ent in entitlements:
            account_id = ent.get('accountId')
            points = ent.get('points', 0)
            serial = ent.get('serialNumber')
            
            if account_id:
                by_account[account_id]['points'] += points
                by_account[account_id]['devices'].add(serial)
        
        # Display
        print(f"{'Account ID':<15} {'Devices':<10} {'Total Points':>15} {'Avg/Day':>12}")
        print("-" * 60)
        
        # Sort by points (highest first)
        sorted_accounts = sorted(by_account.items(), key=lambda x: x[1]['points'], reverse=True)
        
        grand_total = 0
        for account_id, data in sorted_accounts:
            points = data['points']
            device_count = len(data['devices'])
            avg_per_day = points / days_back if days_back > 0 else 0
            
            grand_total += points
            
            print(f"{account_id:<15} {device_count:<10} {points:>15.2f} {avg_per_day:>12.2f}")
        
        print("-" * 60)
        print(f"{'TOTAL':<15} {'':<10} {grand_total:>15.2f}")
        print()
        
        return dict(by_account)
        
    except Exception as e:
        print(f"[ERROR] Failed to retrieve consumption: {e}\n")
        return {}


def main():
    """Main execution."""
    
    parser = argparse.ArgumentParser(
        description='Multi-tenant operations view'
    )
    
    parser.add_argument(
        '--account-id',
        type=int,
        help='Show details for specific account ID only'
    )
    
    parser.add_argument(
        '--consumption',
        action='store_true',
        help='Include consumption analysis'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Days for consumption analysis (default: 7)'
    )
    
    args = parser.parse_args()
    
    # Load credentials
    print(f"\n{'='*80}")
    print("FORTIFLEX MULTI-TENANT OPERATIONS")
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
        
        # Get multi-tenant view
        by_account = get_multi_tenant_view(client)
        
        if not by_account:
            print("No customer accounts found")
            return 0
        
        # Display summary
        if not args.account_id:
            display_customer_summary(by_account)
        
        # Display details
        display_customer_details(by_account, args.account_id)
        
        # Optional: Consumption analysis
        if args.consumption:
            consumption_by_account = get_cross_customer_consumption(client, args.days)
        
        # Overall summary
        total_configs = sum(len(configs) for configs in by_account.values())
        
        print(f"{'='*80}")
        print("OPERATIONS SUMMARY")
        print(f"{'='*80}")
        print(f"Total Customers: {len(by_account)}")
        print(f"Total Configurations: {total_configs}")
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
