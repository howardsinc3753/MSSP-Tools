#!/usr/bin/env python3
"""
Use Case 7: Program Balance Monitoring

Business Scenario:
    - For PREPAID: Monitor point balance and alert when low
    - For MSSP POSTPAID: Track consumption vs. 50,000 points/year minimum

Usage:
    python use_case_7_program_balance_monitoring.py

This script demonstrates:
    1. Checking program type (prepaid vs postpaid)
    2. For prepaid: Point balance and days remaining
    3. For MSSP: Year-to-date consumption vs. minimum commitment
    4. Consumption trends and projections
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


def check_program_info(client: FortiFlexClient, program_sn: str):
    """
    Get program information - simplified version without list_programs().

    Args:
        client: FortiFlexClient instance
        program_sn: Program serial number

    Returns:
        dict: Program information
    """
    print(f"\n{'='*80}")
    print("PROGRAM INFORMATION")
    print(f"{'='*80}\n")

    print(f"Serial Number: {program_sn}")

    # Determine program type from serial number pattern
    # MSSP programs start with "ELAVMS"
    program_type = "MSSP (Postpaid)" if program_sn.startswith("ELAVMS") else "Prepaid"
    print(f"Program Type: {program_type}")

    return {
        'serial_number': program_sn,
        'type': program_type
    }


def check_prepaid_balance(client: FortiFlexClient, program_sn: str):
    """
    Check point balance for prepaid program.
    
    Args:
        client: FortiFlexClient instance
        program_sn: Program serial number
    """
    print(f"\n{'='*80}")
    print("PREPAID PROGRAM BALANCE")
    print(f"{'='*80}\n")
    
    try:
        # Get point balance
        result = client.get_program_points(program_sn)
        
        programs = result.get('programs', [])
        if not programs:
            print("[INFO] No point balance data available")
            return
        
        program = programs[0]
        balance = program.get('pointBalance', 0)
        
        print(f"Current Balance: {balance:,.2f} points")
        
        # Estimate days remaining based on recent consumption
        # This would require daily consumption data
        # For now, show balance only
        
        # Alert thresholds
        if balance < 1000:
            status = "CRITICAL"
            print(f"\n[{status}] Balance is LOW! Please add points soon.")
        elif balance < 5000:
            status = "WARNING"
            print(f"\n[{status}] Balance is getting low.")
        else:
            status = "OK"
            print(f"\n[{status}] Balance is adequate.")
        
        print()
        
    except Exception as e:
        error_msg = str(e)
        if "Point balance is only valid for prepaid programs" in error_msg:
            print("[INFO] This is a postpaid program - no point balance to check")
        else:
            print(f"[ERROR] Failed to check balance: {e}")


def check_mssp_commitment(client: FortiFlexClient, account_id: int, year: int = None):
    """
    Check MSSP annual commitment (50,000 points/year minimum).

    Args:
        client: FortiFlexClient instance
        account_id: FortiFlex account ID (required for API)
        year: Year to check (default: current year)
    """
    if year is None:
        year = datetime.now().year
    
    print(f"\n{'='*80}")
    print(f"MSSP ANNUAL COMMITMENT STATUS - {year}")
    print(f"{'='*80}\n")
    
    print("[INFO] MSSP programs require minimum 50,000 points/year")
    print()
    
    # Calculate year-to-date date range
    year_start = datetime(year, 1, 1).date()
    today = datetime.now().date()
    
    # If checking past year, use full year
    if year < datetime.now().year:
        year_end = datetime(year, 12, 31).date()
    else:
        year_end = today
    
    start_str = year_start.strftime("%Y-%m-%d")
    end_str = year_end.strftime("%Y-%m-%d")
    
    print(f"Date Range: {start_str} to {end_str}")
    
    try:
        # Get year-to-date consumption
        result = client.get_entitlement_points(
            account_id=account_id,
            start_date=start_str,
            end_date=end_str
        )
        
        entitlements = result.get('entitlements', [])
        
        if not entitlements:
            print("\n[INFO] No consumption data available for this period")
            return
        
        # Calculate total consumption
        ytd_consumption = sum(e.get('points', 0) for e in entitlements)
        
        # Calculate days elapsed
        days_elapsed = (year_end - year_start).days + 1
        days_in_year = 365
        
        # Project annual consumption
        if days_elapsed > 0:
            daily_avg = ytd_consumption / days_elapsed
            projected_annual = daily_avg * days_in_year
        else:
            projected_annual = 0
        
        # Compare to minimum
        minimum_annual = 50000
        on_track = projected_annual >= minimum_annual
        shortfall = minimum_annual - projected_annual if not on_track else 0
        
        # Display results
        print()
        print(f"{'Metric':<30} {'Value':>20}")
        print("-" * 55)
        print(f"{'YTD Consumption':<30} {ytd_consumption:>20,.2f} points")
        print(f"{'Days Elapsed':<30} {days_elapsed:>20} days")
        print(f"{'Daily Average':<30} {daily_avg:>20,.2f} points")
        print(f"{'Projected Annual':<30} {projected_annual:>20,.2f} points")
        print(f"{'Minimum Commitment':<30} {minimum_annual:>20,.2f} points")
        print()
        
        # Status
        if on_track:
            print("[OK] ON TRACK to meet annual commitment")
            surplus = projected_annual - minimum_annual
            print(f"    Projected surplus: {surplus:,.2f} points")
        else:
            print("[WARNING] BELOW TARGET for annual commitment")
            print(f"          Projected shortfall: {shortfall:,.2f} points")
            print(f"          Need to increase consumption or true-up at year-end")
        
        print()
        
    except Exception as e:
        print(f"\n[ERROR] Failed to retrieve consumption: {e}")


def check_recent_trends(client: FortiFlexClient, account_id: int, days: int = 30):
    """
    Analyze recent consumption trends.

    Args:
        client: FortiFlexClient instance
        account_id: FortiFlex account ID (required for API)
        days: Number of days to analyze
    """
    print(f"\n{'='*80}")
    print(f"CONSUMPTION TRENDS - LAST {days} DAYS")
    print(f"{'='*80}\n")
    
    # Calculate date range
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    try:
        result = client.get_entitlement_points(
            account_id=account_id,
            start_date=start_str,
            end_date=end_str
        )
        
        entitlements = result.get('entitlements', [])
        
        if not entitlements:
            print("[INFO] No consumption data available")
            return
        
        # Calculate totals
        total_points = sum(e.get('points', 0) for e in entitlements)
        device_count = len(set(e.get('serialNumber') for e in entitlements))
        
        daily_avg = total_points / days if days > 0 else 0
        monthly_projected = daily_avg * 30
        annual_projected = daily_avg * 365
        
        print(f"Period: {days} days ({start_str} to {end_str})")
        print()
        print(f"Total Consumption: {total_points:,.2f} points")
        print(f"Active Devices: {device_count}")
        print(f"Daily Average: {daily_avg:,.2f} points/day")
        print(f"Projected Monthly: {monthly_projected:,.2f} points")
        print(f"Projected Annual: {annual_projected:,.2f} points")
        print()
        
    except Exception as e:
        print(f"[ERROR] Failed to analyze trends: {e}")


def main():
    """Main execution."""
    
    parser = argparse.ArgumentParser(
        description='Monitor FortiFlex program balance and consumption'
    )
    
    parser.add_argument(
        '--year',
        type=int,
        default=datetime.now().year,
        help='Year for MSSP commitment check'
    )
    
    parser.add_argument(
        '--trends-days',
        type=int,
        default=30,
        help='Days for trend analysis (default: 30)'
    )
    
    args = parser.parse_args()
    
    # Load credentials
    print(f"\n{'='*80}")
    print("FORTIFLEX PROGRAM BALANCE MONITORING")
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
        
        # Get program info
        program_info = check_program_info(client, PROGRAM_SN)
        
        if not program_info:
            return 1
        
        # Check balance based on program type
        if "Prepaid" in program_info['type']:
            check_prepaid_balance(client, PROGRAM_SN)
        else:
            check_mssp_commitment(client, ACCOUNT_ID, args.year)

        # Show consumption trends
        check_recent_trends(client, ACCOUNT_ID, args.trends_days)
        
        # Summary
        print(f"{'='*80}")
        print("MONITORING SUMMARY")
        print(f"{'='*80}")
        print(f"Program: {PROGRAM_SN}")
        print(f"Type: {program_info['type']}")
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
