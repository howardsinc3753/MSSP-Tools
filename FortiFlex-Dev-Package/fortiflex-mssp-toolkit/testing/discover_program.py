#!/usr/bin/env python3
"""
Discover FortiFlex Program Serial Number

This script helps you find your program serial number(s) using the API.
You only need your API username and password - no program SN required!
"""

import sys
import os
import json

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fortiflex_client import get_oauth_token
import requests


def discover_programs(api_username, api_password):
    """
    Discover all FortiFlex programs associated with your account.

    Args:
        api_username: Your FortiCloud IAM API username
        api_password: Your FortiCloud IAM API password

    Returns:
        List of programs with their serial numbers
    """
    print("\n" + "="*70)
    print("FORTIFLEX PROGRAM DISCOVERY")
    print("="*70)

    # Step 1: Get OAuth token
    print("\n[1/2] Authenticating...")
    try:
        token = get_oauth_token(api_username, api_password, client_id="flexvm")
        print("[SUCCESS] Authentication successful!")
    except Exception as e:
        print(f"[FAILED] Authentication failed: {e}")
        return None

    # Step 2: Get programs list
    print("\n[2/2] Retrieving your programs...")
    try:
        url = "https://support.fortinet.com/ES/api/fortiflex/v2/programs/list"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, headers=headers, json={})
        response.raise_for_status()

        result = response.json()
        programs = result.get('programs', [])

        if not programs:
            print("\n[WARNING] No FortiFlex programs found for this account")
            print("   - Verify you have FortiFlex programs in your account")
            print("   - Check your IAM user has FortiFlex permissions")
            return None

        print(f"\n[SUCCESS] Found {len(programs)} program(s)!")
        print("\n" + "="*70)
        print("YOUR FORTIFLEX PROGRAMS")
        print("="*70)

        for i, program in enumerate(programs, 1):
            print(f"\nProgram {i}:")
            print(f"  Serial Number: {program.get('serialNumber')}")
            print(f"  Start Date: {program.get('startDate')}")
            print(f"  End Date: {program.get('endDate')}")

            # Determine program type
            has_balance = 'pointBalance' in program
            program_type_str = program.get('programType')

            if has_balance:
                # Has point balance = Prepaid
                print(f"  Point Balance: {program.get('pointBalance'):,.2f}")
                print(f"  Billing Type: PREPAID (pay upfront, points deducted daily)")
            else:
                # No point balance = MSSP Postpaid
                print(f"  Billing Type: MSSP POSTPAID (monthly billing, 50K points/year minimum)")

            if program_type_str and program_type_str != "None":
                print(f"  Program Type: {program_type_str}")

        print("\n" + "="*70)

        return programs

    except requests.exceptions.HTTPError as e:
        print(f"\n[FAILED] API request failed: {e}")
        if e.response.status_code == 401:
            print("   Hint: Your API user may not have FortiFlex permissions")
        return None
    except Exception as e:
        print(f"\n[FAILED] Error retrieving programs: {e}")
        import traceback
        traceback.print_exc()
        return None


def save_to_config(programs, config_file):
    """Save the first program SN to credentials.json"""
    if not programs:
        return False

    primary_program = programs[0]
    program_sn = primary_program.get('serialNumber')

    # Determine billing type
    has_balance = 'pointBalance' in primary_program
    if has_balance:
        billing_type = "PREPAID"
    else:
        billing_type = "MSSP POSTPAID"

    print("\n" + "="*70)
    print("UPDATE CREDENTIALS FILE")
    print("="*70)
    print(f"\nWould you like to update your credentials.json with:")
    print(f"  Program SN: {program_sn}")
    print(f"  Billing Type: {billing_type}")
    print(f"\nUpdate credentials.json? (y/n): ", end="")

    choice = input().strip().lower()

    if choice == 'y':
        try:
            # Read existing credentials
            with open(config_file, 'r') as f:
                creds = json.load(f)

            # Update program serial number
            creds['fortiflex']['program_serial_number'] = program_sn

            # Write back
            with open(config_file, 'w') as f:
                json.dump(creds, f, indent=2)

            print(f"\n[SUCCESS] Updated {config_file}")
            print(f"  Program SN: {program_sn}")
            print("\nYou can now run: python testing\\test_authentication.py")
            return True

        except Exception as e:
            print(f"\n[FAILED] Could not update file: {e}")
            print(f"\nPlease manually update:")
            print(f"  File: {config_file}")
            print(f"  Set: program_serial_number = {program_sn}")
            return False
    else:
        print(f"\nNo changes made. Please manually update your credentials.json:")
        print(f"  \"program_serial_number\": \"{program_sn}\"")
        return False


def main():
    """Main execution."""

    # Load credentials
    config_file = os.path.join(os.path.dirname(__file__), 'config', 'credentials.json')

    if not os.path.exists(config_file):
        print(f"[ERROR] Config file not found: {config_file}")
        print("\nPlease create config/credentials.json first")
        return 1

    try:
        with open(config_file, 'r') as f:
            creds = json.load(f)

        api_username = creds['fortiflex']['api_username']
        api_password = creds['fortiflex']['api_password']

    except Exception as e:
        print(f"[ERROR] Could not load credentials: {e}")
        return 1

    # Discover programs
    programs = discover_programs(api_username, api_password)

    if programs:
        # Offer to save
        save_to_config(programs, config_file)

        print("\n" + "="*70)
        print("NEXT STEPS")
        print("="*70)
        print("\n1. Verify credentials.json has correct program_serial_number")
        print("2. Run: python testing\\test_authentication.py")
        print("3. Start testing use cases!")
        print("\n" + "="*70)

        return 0
    else:
        print("\n[ERROR] Could not discover programs")
        print("\nPlease check:")
        print("  1. API credentials are correct")
        print("  2. API user has FortiFlex permissions")
        print("  3. You have at least one FortiFlex program")
        return 1


if __name__ == "__main__":
    sys.exit(main())
