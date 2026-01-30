#!/usr/bin/env python3
"""
Example: Provision a Device

This example shows how to provision a device to FortiManager.
"""

import os
import sys
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fortiztp import FortiZTPClient
from fortiztp.devices import DeviceManager


def main():
    parser = argparse.ArgumentParser(description="Provision a FortiZTP device")
    parser.add_argument("serial_number", help="Device serial number")
    parser.add_argument("--device-type", default="FortiGate",
                        choices=["FortiGate", "FortiAP", "FortiSwitch", "FortiExtender"],
                        help="Device type (default: FortiGate)")
    parser.add_argument("--target", default="FortiManager",
                        choices=["FortiManager", "FortiGateCloud", "FortiEdgeCloud", "ExternalController"],
                        help="Provision target (default: FortiManager)")
    parser.add_argument("--fmg-oid", type=int, help="FortiManager OID")
    parser.add_argument("--fmg-ip", help="FortiManager IP address")
    parser.add_argument("--script-oid", type=int, help="Bootstrap script OID")
    parser.add_argument("--unprovision", action="store_true",
                        help="Unprovision the device instead of provisioning")
    parser.add_argument("--creds", default="credentials.yaml",
                        help="Path to credentials file")
    args = parser.parse_args()

    # Create client
    if os.path.exists(args.creds):
        client = FortiZTPClient.from_credential_file(args.creds)
    else:
        client = FortiZTPClient.from_env()

    devices = DeviceManager(client)

    # Build provision kwargs
    provision_kwargs = {
        "serial_number": args.serial_number,
        "device_type": args.device_type,
        "provision_status": "unprovisioned" if args.unprovision else "provisioned"
    }

    if not args.unprovision:
        provision_kwargs["provision_target"] = args.target

        if args.fmg_oid:
            provision_kwargs["fortimanager_oid"] = args.fmg_oid
        if args.fmg_ip:
            provision_kwargs["external_controller_ip"] = args.fmg_ip
        if args.script_oid:
            provision_kwargs["script_oid"] = args.script_oid

    # Execute provisioning
    action = "Unprovisioning" if args.unprovision else "Provisioning"
    print(f"{action} device {args.serial_number}...")

    try:
        result = devices.provision(**provision_kwargs)
        print(f"\nSuccess: {result['message']}")
        print(f"\nDevice details:")
        for key, value in result['device'].items():
            if value is not None:
                print(f"  {key}: {value}")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
