#!/usr/bin/env python3
"""
Example: List FortiZTP Devices

This example shows how to list devices and filter by various criteria.

Usage:
    python list_devices.py --creds credentials.yaml
    python list_devices.py  # Uses environment variables
"""

import os
import sys
import argparse
from collections import Counter

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fortiztp import FortiZTPClient


def main():
    parser = argparse.ArgumentParser(description="List FortiZTP devices")
    parser.add_argument("--creds", default="credentials.yaml",
                        help="Path to credentials file (default: credentials.yaml)")
    parser.add_argument("--device-type",
                        choices=["FortiGate", "FortiAP", "FortiSwitch", "FortiExtender"],
                        help="Filter by device type")
    parser.add_argument("--status",
                        choices=["provisioned", "unprovisioned", "hidden", "incomplete"],
                        help="Filter by provision status")
    args = parser.parse_args()

    # Create client - try credential file first, then environment variables
    if os.path.exists(args.creds):
        print(f"Using credentials from: {args.creds}")
        client = FortiZTPClient.from_credential_file(args.creds)
    else:
        print("Using environment variables (FORTIZTP_USERNAME, FORTIZTP_PASSWORD)")
        try:
            client = FortiZTPClient.from_env()
        except ValueError as e:
            print(f"\nError: {e}")
            print("\nTo use this script, either:")
            print("  1. Create a credentials.yaml file (see credentials.yaml.template)")
            print("  2. Set FORTIZTP_USERNAME and FORTIZTP_PASSWORD environment variables")
            sys.exit(1)

    print()
    print("=" * 60)
    print("FortiZTP Device Inventory")
    print("=" * 60)

    # Get devices with optional filters
    try:
        devices = client.list_devices(
            device_type=args.device_type,
            provision_status=args.status
        )
    except Exception as e:
        print(f"\nError fetching devices: {e}")
        sys.exit(1)

    print(f"\nTotal devices: {len(devices)}")

    if not devices:
        print("\nNo devices found.")
        return

    # Summary by status
    status_counts = Counter(d.get('provision_status', 'unknown') for d in devices)
    print("\nBy Provision Status:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")

    # Summary by device type
    type_counts = Counter(d.get('device_type', 'unknown') for d in devices)
    print("\nBy Device Type:")
    for dtype, count in sorted(type_counts.items()):
        print(f"  {dtype}: {count}")

    # List unprovisioned devices
    unprovisioned = [d for d in devices if d.get('provision_status') == 'unprovisioned']
    if unprovisioned:
        print(f"\n--- Unprovisioned Devices ({len(unprovisioned)}) ---")
        for d in unprovisioned:
            print(f"  {d['serial_number']} ({d.get('device_type', 'Unknown')})")

    # List provisioned devices
    provisioned = [d for d in devices if d.get('provision_status') == 'provisioned']
    if provisioned:
        print(f"\n--- Provisioned Devices ({len(provisioned)}) ---")
        for d in provisioned:
            target = d.get('provision_target', 'Unknown')
            fmg = d.get('fortimanager_oid', '')
            script = d.get('script_oid', '')
            print(f"  {d['serial_number']} -> {target} (FMG: {fmg}, Script: {script})")


if __name__ == "__main__":
    main()
