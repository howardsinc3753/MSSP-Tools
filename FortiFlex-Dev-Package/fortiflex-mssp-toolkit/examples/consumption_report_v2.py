#!/usr/bin/env python3
"""
Enhanced Consumption Report

Pull point consumption data with filtering options.
Supports both single entitlement and all-entitlement reports.

Usage:
    # All entitlements, last 30 days
    python consumption_report_v2.py

    # All entitlements, last 1 day (daily report)
    python consumption_report_v2.py --days 1

    # Specific entitlement, last 30 days
    python consumption_report_v2.py --serial FMVMMLTMXXXXXXXX

    # Specific entitlement, last 7 days
    python consumption_report_v2.py --serial FMVMMLTMXXXXXXXX --days 7
"""

import sys
import os
import json
import argparse
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fortiflex_client import FortiFlexClient, get_oauth_token


def load_credentials():
    """Load credentials from config file."""
    config_file = os.path.join(os.path.dirname(__file__), '..', 'testing', 'config', 'credentials.json')

    if not os.path.exists(config_file):
        print("[ERROR] credentials.json not found!")
        print(f"   Expected location: {config_file}")
        print("\n   Please run: python testing/discover_program.py")
        sys.exit(1)

    with open(config_file, 'r') as f:
        creds = json.load(f)

    # Validate required fields
    required_fields = ['api_username', 'api_password', 'program_serial_number', 'account_id']
    for field in required_fields:
        if field not in creds.get('fortiflex', {}):
            print(f"[ERROR] Missing required field '{field}' in credentials.json")
            print(f"\n   Your credentials.json must include:")
            print(f"   {{\n     \"fortiflex\": {{")
            print(f"       \"api_username\": \"YOUR_USERNAME\",")
            print(f"       \"api_password\": \"YOUR_PASSWORD\",")
            print(f"       \"program_serial_number\": \"ELAVMSXXXXXXXX\",")
            print(f"       \"account_id\": YOUR_ACCOUNT_ID")
            print(f"     }}\n   }}")
            sys.exit(1)

    return creds


def list_all_configurations(client: FortiFlexClient):
    """
    List all configurations to show what entitlements exist.

    Args:
        client: FortiFlexClient instance

    Returns:
        List of configurations
    """
    print(f"\n{'='*80}")
    print("AVAILABLE CONFIGURATIONS (Templates)")
    print(f"{'='*80}\n")

    configs = client.list_configs()

    if not configs or 'configs' not in configs:
        print("No configurations found.")
        return []

    config_list = configs['configs']

    print(f"{'ID':<8} {'Name':<30} {'Product Type':<25} {'Status':<10}")
    print("-" * 80)

    for cfg in config_list:
        cfg_id = cfg.get('id', 'N/A')
        name = cfg.get('name', 'Unknown')
        product = cfg.get('productType', {}).get('name', 'Unknown')
        status = cfg.get('status', 'Unknown')

        print(f"{cfg_id:<8} {name:<30} {product:<25} {status:<10}")

    print(f"\n{'='*80}\n")
    print(f"[NOTE] These are configuration templates, not actual entitlements.")
    print(f"       To see actual deployed entitlements, you need to query the portal")
    print(f"       or use the consumption API (which only shows devices consuming points).\n")

    return config_list


def get_consumption_report(client: FortiFlexClient, account_id: int, days_back: int = 30, serial_filter: str = None):
    """
    Get consumption report for specified number of days.

    Args:
        client: FortiFlexClient instance
        account_id: FortiFlex account ID (required per API spec)
        days_back: Number of days to look back (default: 30)
        serial_filter: Optional serial number to filter by

    Returns:
        Consumption data dict
    """
    print(f"\n{'='*80}")
    if serial_filter:
        print(f"CONSUMPTION REPORT - {serial_filter} - LAST {days_back} DAYS")
    else:
        print(f"CONSUMPTION REPORT - ALL ENTITLEMENTS - LAST {days_back} DAYS")
    print(f"{'='*80}\n")

    # Calculate date range - use local date (not datetime) to match GUI
    today = datetime.now().date()
    end_date = today  # inclusive end as YYYY-MM-DD
    start_date = today - timedelta(days=days_back)

    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    print(f"Date Range: {start_str} to {end_str}")
    print(f"Account ID: {account_id}")
    if serial_filter:
        print(f"Serial Number Filter: {serial_filter}")
    print(f"\nRetrieving consumption data...\n")

    # Get consumption data with required identifiers
    try:
        consumption = client.get_entitlement_points(
            account_id=account_id,  # REQUIRED per API spec
            serial_number=serial_filter,  # Optional filter
            start_date=start_str,
            end_date=end_str
        )
    except Exception as e:
        msg = str(e)
        if "400" in msg:
            print(f"\n[INFO] No consumption data found for the date range.")
            print(f"       (HTTP 400) Server message:")
            print(f"       {msg[:500]}")
            print("\n       Possible reasons:")
            print("       1. Entitlements exist but haven't consumed points yet")
            print("       2. Entitlements are in PENDING status (not activated)")
            print("       3. Devices haven't checked in with FortiCloud")
            print("       4. No entitlements exist for this date range")
            print("\n[NOTE] The '/entitlements/points' API only returns consumption data.")
            print("       It does NOT return a list of entitlements.")
            print("\n       Once ACTIVE devices check in with FortiCloud and start")
            print("       consuming points, they will appear in this report.\n")
            return None
        else:
            raise

    # Check if we got data
    points_data = consumption.get('entitlements', [])

    if not points_data:
        print(f"[INFO] API 200 OK but no consumption for {start_str} to {end_str}.")
        print("       This means entitlements exist but have not consumed any points yet.")
        print("\n       Your entitlements are configured, but they need to:")
        print("       1. Be activated (if PENDING)")
        print("       2. Check in with FortiCloud")
        print("       3. Start consuming services\n")
        return consumption

    # Optional defensive client-side filter (server already filtered if serialNumber was sent)
    if serial_filter:
        points_data = [p for p in points_data if p.get('serialNumber') == serial_filter]

        if not points_data:
            print(f"[INFO] No consumption data found for serial number: {serial_filter}")
            print(f"       Either this device hasn't consumed points, or the serial number is incorrect.\n")
            return None

    # Process the data
    print(f"[SUCCESS] Retrieved consumption data for {len(points_data)} entitlement(s)\n")

    # Display summary
    print(f"{'='*80}")
    print("CONSUMPTION SUMMARY")
    print(f"{'='*80}\n")

    # Sort by total points (highest first)
    sorted_points = sorted(points_data, key=lambda x: x.get('points', 0), reverse=True)

    # Display header
    print(f"{'Serial Number':<30} {'Account ID':<15} {'Total Points':>15}")
    print("-" * 65)

    # Display each entitlement
    grand_total = 0
    for item in sorted_points:
        serial = item.get('serialNumber', 'Unknown')
        account_id = item.get('accountId', 'N/A')
        points = item.get('points', 0)
        grand_total += points

        print(f"{serial:<30} {str(account_id):<15} {points:>15.2f}")

    # Display totals
    print("-" * 65)
    print(f"{'GRAND TOTAL':<30} {'':<15} {grand_total:>15.2f}")
    print(f"\n{'='*80}\n")

    # Daily breakdown - be tolerant to shape differences
    if sorted_points and isinstance(sorted_points[0].get('daily'), list):
        for idx, item in enumerate(sorted_points, 1):
            serial = item.get('serialNumber', 'Unknown')
            daily_data = item.get('daily', [])

            if not daily_data:
                continue

            print(f"{'='*80}")
            print(f"DAILY BREAKDOWN #{idx} - {serial}")
            print(f"{'='*80}\n")

            print(f"{'Date':<15} {'Points':>15}")
            print("-" * 35)

            for day in daily_data:
                date_str = day.get('date', 'Unknown')
                points = day.get('points', 0)
                print(f"{date_str:<15} {points:>15.2f}")

            print(f"\n{'='*80}\n")

    return consumption


def main():
    """Main execution."""

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='FortiFlex Consumption Report',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # All entitlements, last 30 days (default)
  python consumption_report_v2.py

  # Daily report (last 1 day)
  python consumption_report_v2.py --days 1

  # Specific entitlement, last 30 days
  python consumption_report_v2.py --serial FMVMMLTMXXXXXXXX

  # Specific entitlement, last 7 days
  python consumption_report_v2.py --serial FMVMMLTMXXXXXXXX --days 7

  # Show configurations first
  python consumption_report_v2.py --list-configs
        """
    )

    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days to look back (default: 30)'
    )

    parser.add_argument(
        '--serial',
        type=str,
        help='Filter by specific serial number (e.g., FMVMMLTMXXXXXXXX)'
    )

    parser.add_argument(
        '--list-configs',
        action='store_true',
        help='List all configurations before running report'
    )

    args = parser.parse_args()

    # Load credentials
    creds = load_credentials()
    API_USERNAME = creds['fortiflex']['api_username']
    API_PASSWORD = creds['fortiflex']['api_password']
    PROGRAM_SN = creds['fortiflex']['program_serial_number']
    ACCOUNT_ID = creds['fortiflex']['account_id']  # REQUIRED per API spec

    try:
        print(f"\n{'='*80}")
        print("FORTIFLEX CONSUMPTION REPORT")
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

        # List configurations if requested
        if args.list_configs:
            list_all_configurations(client)

        # Get consumption report
        consumption = get_consumption_report(
            client,
            account_id=ACCOUNT_ID,
            days_back=args.days,
            serial_filter=args.serial
        )

        if consumption is None:
            print("No data to report.")
            return 1

        # Optional: Save to JSON file with safer filenames
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_serial = (args.serial or "all").replace(":", "_").replace("/", "_")
        output_file = f"consumption_{safe_serial}_{args.days}days_{timestamp}.json"

        with open(output_file, 'w') as f:
            json.dump({
                'generated_at': datetime.now().isoformat(),
                'days_back': args.days,
                'serial_filter': args.serial,
                'program_serial': PROGRAM_SN,
                'consumption': consumption
            }, f, indent=2)

        print(f"[SUCCESS] Report saved to: {output_file}\n")

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
