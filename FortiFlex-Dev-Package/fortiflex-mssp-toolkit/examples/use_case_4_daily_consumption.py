#!/usr/bin/env python3
"""
Use Case 4: Daily Consumption Data Pull (Billing)

Business Scenario:
    CRITICAL for MSSP - Pull yesterday's point consumption for billing.
    Portal only keeps 3 months of history - YOU MUST STORE THIS DATA!

Usage:
    python use_case_4_daily_consumption.py

This script demonstrates:
    1. Pulling yesterday's consumption (for daily billing job)
    2. Aggregating by customer account
    3. Storing data for long-term retention
    4. Monthly invoice generation pattern

Run this DAILY at 6:00 AM PST via cron/Task Scheduler!
"""

import sys
import os
import json
import argparse
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fortiflex_client import FortiFlexClient, get_oauth_token


def load_credentials():
    """Load API credentials."""
    config_file = os.path.join(
        os.path.dirname(__file__), '..', 'testing', 'config', 'credentials.json'
    )
    with open(config_file, 'r') as f:
        return json.load(f)


def get_yesterday_consumption(client: FortiFlexClient, account_id: int):
    """
    Pull yesterday's point consumption.
    
    Args:
        client: FortiFlexClient instance
        account_id: Account ID to query
        
    Returns:
        dict: Consumption data
    """
    # Calculate yesterday's date
    yesterday = (datetime.now() - timedelta(days=1)).date()
    yesterday_str = yesterday.strftime("%Y-%m-%d")
    today_str = datetime.now().date().strftime("%Y-%m-%d")
    
    print(f"\n{'='*80}")
    print(f"DAILY CONSUMPTION REPORT - {yesterday_str}")
    print(f"{'='*80}\n")
    
    print(f"Date: {yesterday_str}")
    print(f"Account ID: {account_id}")
    print()
    
    try:
        # Get consumption data
        result = client.get_entitlement_points(
            account_id=account_id,
            start_date=yesterday_str,
            end_date=today_str
        )
        
        entitlements = result.get('entitlements', [])
        
        if not entitlements:
            print("[INFO] No consumption data for yesterday")
            print("       Devices may not be active or haven't checked in yet")
            return None
        
        print(f"[SUCCESS] Retrieved consumption for {len(entitlements)} entitlement(s)\n")
        
        return result
        
    except Exception as e:
        print(f"[ERROR] Failed to retrieve consumption: {e}")
        return None


def display_consumption_summary(consumption_data: dict):
    """
    Display formatted consumption summary.
    
    Args:
        consumption_data: Consumption API response
    """
    entitlements = consumption_data.get('entitlements', [])
    
    if not entitlements:
        return
    
    print(f"{'='*80}")
    print("CONSUMPTION SUMMARY")
    print(f"{'='*80}\n")
    
    # Sort by points (highest first)
    sorted_ents = sorted(entitlements, key=lambda x: x.get('points', 0), reverse=True)
    
    # Display table
    print(f"{'Serial Number':<30} {'Points':>15}")
    print("-" * 50)
    
    total_points = 0
    for ent in sorted_ents:
        serial = ent.get('serialNumber', 'Unknown')
        points = ent.get('points', 0)
        total_points += points
        
        print(f"{serial:<30} {points:>15.2f}")
    
    print("-" * 50)
    print(f"{'TOTAL':<30} {total_points:>15.2f}")
    print()


def store_consumption_data(consumption_data: dict, date_str: str):
    """
    Store consumption data to file (simulate database storage).
    
    In production, this would write to PostgreSQL/MySQL database.
    
    Args:
        consumption_data: Consumption data
        date_str: Date string (YYYY-MM-DD)
    """
    entitlements = consumption_data.get('entitlements', [])
    
    if not entitlements:
        return
    
    # Create data directory if it doesn't exist
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'consumption')
    os.makedirs(data_dir, exist_ok=True)
    
    # Store as JSON file (one per day)
    filename = f"consumption_{date_str}.json"
    filepath = os.path.join(data_dir, filename)
    
    with open(filepath, 'w') as f:
        json.dump({
            'date': date_str,
            'timestamp': datetime.now().isoformat(),
            'entitlements': entitlements
        }, f, indent=2)
    
    print(f"[SUCCESS] Data stored to: {filepath}\n")


def generate_monthly_summary(data_dir: str, year: int, month: int):
    """
    Generate monthly summary from daily consumption files.
    
    Args:
        data_dir: Directory containing daily consumption files
        year: Year (e.g., 2025)
        month: Month (1-12)
        
    Returns:
        dict: Monthly summary
    """
    print(f"\n{'='*80}")
    print(f"MONTHLY SUMMARY - {year}-{month:02d}")
    print(f"{'='*80}\n")
    
    # Collect all daily files for the month
    monthly_data = {}
    
    for day in range(1, 32):
        try:
            date_str = f"{year}-{month:02d}-{day:02d}"
            filename = f"consumption_{date_str}.json"
            filepath = os.path.join(data_dir, filename)
            
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    
                for ent in data['entitlements']:
                    serial = ent['serialNumber']
                    points = ent['points']
                    
                    if serial not in monthly_data:
                        monthly_data[serial] = 0
                    monthly_data[serial] += points
        
        except ValueError:
            # Invalid day for month (e.g., Feb 30)
            break
    
    if not monthly_data:
        print("[INFO] No consumption data found for this month")
        return None
    
    # Display summary
    print(f"{'Serial Number':<30} {'Total Points':>15}")
    print("-" * 50)
    
    total_monthly = 0
    for serial in sorted(monthly_data.keys(), key=lambda k: monthly_data[k], reverse=True):
        points = monthly_data[serial]
        total_monthly += points
        print(f"{serial:<30} {points:>15.2f}")
    
    print("-" * 50)
    print(f"{'MONTHLY TOTAL':<30} {total_monthly:>15.2f}")
    print()
    
    return {
        'year': year,
        'month': month,
        'total_points': total_monthly,
        'by_device': monthly_data
    }


def main():
    """Main execution."""
    
    parser = argparse.ArgumentParser(
        description='Pull daily consumption data for billing'
    )
    
    parser.add_argument(
        '--monthly-summary',
        action='store_true',
        help='Generate monthly summary instead of daily pull'
    )
    
    parser.add_argument(
        '--year',
        type=int,
        default=datetime.now().year,
        help='Year for monthly summary'
    )
    
    parser.add_argument(
        '--month',
        type=int,
        default=datetime.now().month,
        help='Month for monthly summary'
    )
    
    args = parser.parse_args()
    
    # Load credentials
    print(f"\n{'='*80}")
    print("FORTIFLEX DAILY CONSUMPTION DATA PULL")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    
    creds = load_credentials()
    API_USERNAME = creds['fortiflex']['api_username']
    API_PASSWORD = creds['fortiflex']['api_password']
    PROGRAM_SN = creds['fortiflex']['program_serial_number']
    ACCOUNT_ID = creds['fortiflex'].get('account_id')
    
    if not ACCOUNT_ID:
        print("[ERROR] account_id not found in credentials.json")
        print("       Run: python testing/discover_program.py")
        return 1
    
    try:
        if args.monthly_summary:
            # Generate monthly summary from stored data
            data_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'consumption')
            
            if not os.path.exists(data_dir):
                print("[ERROR] No consumption data directory found")
                print("       Run daily pulls first to collect data")
                return 1
            
            summary = generate_monthly_summary(data_dir, args.year, args.month)
            
            if summary:
                # Save monthly summary
                output_file = f"monthly_summary_{args.year}_{args.month:02d}.json"
                with open(output_file, 'w') as f:
                    json.dump(summary, f, indent=2)
                
                print(f"Monthly summary saved to: {output_file}\n")
            
            return 0
        
        # Daily consumption pull
        print("Authenticating...")
        token = get_oauth_token(API_USERNAME, API_PASSWORD, client_id="flexvm")
        print("[SUCCESS]\n")
        
        # Initialize client
        client = FortiFlexClient(token, PROGRAM_SN)
        
        # Get yesterday's consumption
        yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        consumption = get_yesterday_consumption(client, ACCOUNT_ID)
        
        if not consumption:
            return 1
        
        # Display summary
        display_consumption_summary(consumption)
        
        # Store data (simulate database)
        store_consumption_data(consumption, yesterday_str)
        
        # Summary
        entitlements = consumption.get('entitlements', [])
        total_points = sum(e.get('points', 0) for e in entitlements)
        
        print(f"{'='*80}")
        print("DAILY JOB SUMMARY")
        print(f"{'='*80}")
        print(f"Date: {yesterday_str}")
        print(f"Devices: {len(entitlements)}")
        print(f"Total Points: {total_points:.2f}")
        print(f"Status: [COMPLETE]")
        print(f"{'='*80}\n")
        
        print("[REMINDER] Run this daily at 6:00 AM PST!")
        print("           Portal only keeps 3 months of history!\n")
        
        return 0
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
