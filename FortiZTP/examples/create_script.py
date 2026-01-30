#!/usr/bin/env python3
"""
Example: Create Bootstrap Script

This example shows how to create pre-run CLI scripts for ZTP.
"""

import os
import sys
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fortiztp import FortiZTPClient
from fortiztp.scripts import ScriptManager


# Sample bootstrap scripts for different use cases
SAMPLE_SCRIPTS = {
    "basic": """
# Basic FortiGate Bootstrap
config system global
    set hostname "Branch-FGT"
    set timezone America/New_York
end

config system interface
    edit "wan1"
        set mode dhcp
        set allowaccess ping https ssh snmp fgfm
    next
end

config system dns
    set primary 8.8.8.8
    set secondary 8.8.4.4
end
""",

    "fmg-registration": """
# FortiManager Registration Script
config system global
    set hostname "Managed-FGT"
end

config system interface
    edit "wan1"
        set mode dhcp
        set allowaccess ping https ssh fgfm
    next
end

config system central-management
    set type fortimanager
    set fmg "192.168.1.100"
end
""",

    "ipsec-vpn": """
# IPsec VPN Bootstrap Script
config system interface
    edit "wan1"
        set mode dhcp
        set allowaccess ping https ssh fgfm
    next
end

config vpn ipsec phase1-interface
    edit "HQ-VPN"
        set interface "wan1"
        set ike-version 2
        set peertype any
        set proposal aes256-sha256
        set remote-gw 203.0.113.1
        set psksecret "change-this-psk"
    next
end

config vpn ipsec phase2-interface
    edit "HQ-VPN"
        set phase1name "HQ-VPN"
        set proposal aes256-sha256
        set auto-negotiate enable
    next
end

config router static
    edit 0
        set dst 10.0.0.0/8
        set device "HQ-VPN"
    next
end
""",

    "sdwan": """
# SD-WAN Bootstrap Script
config system interface
    edit "wan1"
        set mode dhcp
        set allowaccess ping https ssh fgfm
    next
    edit "wan2"
        set mode dhcp
        set allowaccess ping
    next
end

config system sdwan
    set status enable
    config zone
        edit "virtual-wan-link"
        next
    end
    config members
        edit 1
            set interface "wan1"
            set gateway 0.0.0.0
        next
        edit 2
            set interface "wan2"
            set gateway 0.0.0.0
        next
    end
end
"""
}


def main():
    parser = argparse.ArgumentParser(description="Create FortiZTP bootstrap script")
    parser.add_argument("--name", help="Script name (required for create)")
    parser.add_argument("--template", choices=list(SAMPLE_SCRIPTS.keys()),
                        help="Use a sample template")
    parser.add_argument("--file", help="Read script content from file")
    parser.add_argument("--content", help="Script content (inline)")
    parser.add_argument("--list", action="store_true", help="List existing scripts")
    parser.add_argument("--creds", default="credentials.yaml",
                        help="Path to credentials file")
    args = parser.parse_args()

    # Create client
    if os.path.exists(args.creds):
        client = FortiZTPClient.from_credential_file(args.creds)
    else:
        client = FortiZTPClient.from_env()

    scripts = ScriptManager(client)

    # List scripts if requested (no name required)
    if args.list:
        existing = scripts.list()
        print(f"\nExisting Scripts ({len(existing)}):")
        print("-" * 50)
        for s in existing:
            print(f"  OID: {s['oid']:5}  Name: {s['name']}")
        return

    # Name is required for creating scripts
    if not args.name:
        print("Error: --name is required when creating a script")
        print("Use --list to see existing scripts")
        sys.exit(1)

    # Determine script content
    content = None
    if args.template:
        content = SAMPLE_SCRIPTS[args.template]
        print(f"Using '{args.template}' template")
    elif args.file:
        with open(args.file, 'r') as f:
            content = f.read()
        print(f"Loaded content from {args.file}")
    elif args.content:
        content = args.content
    else:
        print("Error: Provide --template, --file, or --content")
        print("\nAvailable templates:")
        for name, desc in [
            ("basic", "Basic hostname, WAN, DNS configuration"),
            ("fmg-registration", "FortiManager registration"),
            ("ipsec-vpn", "Site-to-site IPsec VPN setup"),
            ("sdwan", "SD-WAN dual-WAN configuration")
        ]:
            print(f"  {name:20} - {desc}")
        sys.exit(1)

    # Create script
    print(f"\nCreating script '{args.name}'...")
    try:
        result = scripts.create(name=args.name, content=content)
        print(f"\nSuccess: {result['message']}")
        print(f"\nScript Details:")
        print(f"  OID: {result['script']['oid']}")
        print(f"  Name: {result['script']['name']}")
        print(f"  Content Length: {result['script']['content_length']} chars")

        if result.get('content_upload_failed'):
            print(f"\n  WARNING: Content upload failed.")
            print(f"  Add content via portal: {result.get('portal_url')}")

        print(f"\n  Use script_oid={result['script']['oid']} when provisioning devices")

    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
