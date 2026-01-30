#!/usr/bin/env python3
"""
Example: Bulk Device Provisioning

This example shows how to provision multiple devices from a CSV file.
"""

import os
import sys
import csv
import argparse
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fortiztp import FortiZTPClient
from fortiztp.devices import DeviceManager


def load_devices_from_csv(filepath):
    """
    Load device list from CSV file.

    Expected CSV format:
        serial_number,device_type,script_oid
        FGT60F0000000001,FortiGate,456
        FGT60F0000000002,FortiGate,456
        FAP221E0000000001,FortiAP,
    """
    devices = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            devices.append({
                "serial_number": row.get("serial_number", "").strip(),
                "device_type": row.get("device_type", "FortiGate").strip(),
                "script_oid": row.get("script_oid", "").strip() or None
            })
    return devices


def main():
    parser = argparse.ArgumentParser(description="Bulk provision FortiZTP devices")
    parser.add_argument("--csv", help="CSV file with device list")
    parser.add_argument("--target", default="FortiManager",
                        choices=["FortiManager", "FortiGateCloud", "FortiEdgeCloud", "ExternalController"],
                        help="Provision target (default: FortiManager)")
    parser.add_argument("--fmg-oid", type=int, help="FortiManager OID (required for FortiManager target)")
    parser.add_argument("--fmg-ip", help="FortiManager/Controller IP address (required for FortiManager/ExternalController)")
    parser.add_argument("--region", help="FortiCloud region (required for cloud targets)")
    parser.add_argument("--script-oid", type=int, help="Default bootstrap script OID")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument("--creds", default="credentials.yaml",
                        help="Path to credentials file")
    args = parser.parse_args()

    # Validate target-specific requirements
    if args.target == "FortiManager":
        if not args.fmg_oid:
            parser.error("--fmg-oid is required for FortiManager target")
        if not args.fmg_ip:
            parser.error("--fmg-ip is required for FortiManager target")
    elif args.target == "ExternalController":
        if not args.fmg_ip:
            parser.error("--fmg-ip is required for ExternalController target")
    elif args.target in ["FortiGateCloud", "FortiEdgeCloud"]:
        if not args.region:
            parser.error(f"--region is required for {args.target} target")

    # Create client
    if os.path.exists(args.creds):
        client = FortiZTPClient.from_credential_file(args.creds)
    else:
        client = FortiZTPClient.from_env()

    device_manager = DeviceManager(client)

    # Load devices from CSV or get unprovisioned devices
    if args.csv:
        devices_to_provision = load_devices_from_csv(args.csv)
        print(f"Loaded {len(devices_to_provision)} devices from {args.csv}")
    else:
        # Get all unprovisioned devices
        all_devices = device_manager.list(provision_status="unprovisioned")
        devices_to_provision = [
            {
                "serial_number": d["serial_number"],
                "device_type": d["device_type"],
                "script_oid": None
            }
            for d in all_devices
        ]
        print(f"Found {len(devices_to_provision)} unprovisioned devices")

    if not devices_to_provision:
        print("No devices to provision")
        return

    # Show plan
    print("\n" + "=" * 70)
    print(f"Bulk Provisioning Plan - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print(f"Target: {args.target}")
    if args.fmg_oid:
        print(f"FortiManager OID: {args.fmg_oid}")
    if args.fmg_ip:
        print(f"Controller IP: {args.fmg_ip}")
    if args.region:
        print(f"Region: {args.region}")
    print(f"Default Script OID: {args.script_oid or 'None'}")
    print(f"Devices: {len(devices_to_provision)}")
    print("-" * 70)

    for d in devices_to_provision:
        script = d.get("script_oid") or args.script_oid or "None"
        print(f"  {d['serial_number']:20} ({d['device_type']:12}) -> Script: {script}")

    if args.dry_run:
        print("\n[DRY RUN] No changes made")
        return

    # Confirm
    print("\n" + "-" * 70)
    confirm = input("Proceed with provisioning? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Aborted")
        return

    # Execute provisioning
    print("\nProvisioning devices...\n")

    results = {"success": [], "failed": []}

    for device in devices_to_provision:
        sn = device["serial_number"]
        dtype = device["device_type"]
        script = device.get("script_oid") or args.script_oid

        try:
            # Build provision kwargs based on target
            provision_kwargs = {
                "serial_number": sn,
                "device_type": dtype,
                "provision_target": args.target,
            }
            if args.fmg_oid:
                provision_kwargs["fortimanager_oid"] = args.fmg_oid
            if args.fmg_ip:
                provision_kwargs["external_controller_ip"] = args.fmg_ip
            if args.region:
                provision_kwargs["region"] = args.region
            if script:
                provision_kwargs["script_oid"] = int(script)

            result = device_manager.provision(**provision_kwargs)
            print(f"[OK]    {sn}")
            results["success"].append(sn)
        except Exception as e:
            print(f"[ERROR] {sn}: {e}")
            results["failed"].append({"sn": sn, "error": str(e)})

    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Success: {len(results['success'])}")
    print(f"Failed:  {len(results['failed'])}")

    if results['failed']:
        print("\nFailed devices:")
        for f in results['failed']:
            print(f"  {f['sn']}: {f['error']}")


if __name__ == "__main__":
    main()
