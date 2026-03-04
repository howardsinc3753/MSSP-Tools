#!/usr/bin/env python3
from __future__ import annotations

"""
FortiFlex Token Create Tool

Create FortiFlex license tokens for VM provisioning.
Generates VM entitlements for FortiGate-VM, FortiManager-VM, FortiAnalyzer-VM.

IMPORTANT: Uses entitlements/vm/create endpoint for virtual appliances.
- Hardware products use entitlements/hardware/create (requires serial numbers)
- Cloud services (FortiEDR) use entitlements/cloud/create
- VMs (FortiGate-VM, FMG-VM, FAZ-VM) use entitlements/vm/create

API Reference: https://support.fortinet.com/ES/api/fortiflex/v2/
Client ID: flexvm

Author: Trust-Bot Tool Maker
Version: 1.0.3
Created: 2026-01-16
Updated: 2026-01-18 - Fixed endpoint from cloud/create to vm/create
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import yaml

logger = logging.getLogger(__name__)

# API Configuration
AUTH_URL = "https://customerapiauth.fortinet.com/api/v1/oauth/token/"
FORTIFLEX_API_BASE = "https://support.fortinet.com/ES/api/fortiflex/v2"
CLIENT_ID = "flexvm"

# Credential file paths
CREDENTIAL_PATHS = [
    Path("C:/ProgramData/Ulysses/config/forticloud_credentials.yaml"),
    Path("config/forticloud_credentials.yaml"),
    Path.home() / ".ulysses" / "forticloud_credentials.yaml",
]


def load_credentials(params: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """Load API credentials and program serial number."""
    creds = {
        "api_username": None,
        "api_password": None,
        "program_serial_number": None
    }

    # Check parameters first
    for key in creds.keys():
        if params.get(key):
            creds[key] = params[key]

    if creds["api_username"] and creds["api_password"]:
        return creds

    # Check environment variables
    if os.environ.get("FORTICLOUD_API_USERNAME"):
        creds["api_username"] = os.environ["FORTICLOUD_API_USERNAME"]
    if os.environ.get("FORTICLOUD_API_PASSWORD"):
        creds["api_password"] = os.environ["FORTICLOUD_API_PASSWORD"]
    if os.environ.get("FORTIFLEX_PROGRAM_SN"):
        creds["program_serial_number"] = os.environ["FORTIFLEX_PROGRAM_SN"]

    if creds["api_username"] and creds["api_password"]:
        return creds

    # Try credential files
    for cred_path in CREDENTIAL_PATHS:
        if cred_path.exists():
            try:
                with open(cred_path, "r") as f:
                    config = yaml.safe_load(f)
                if config:
                    if "api_username" in config:
                        creds["api_username"] = config["api_username"]
                    if "api_password" in config:
                        creds["api_password"] = config["api_password"]
                    if "program_serial_number" in config:
                        creds["program_serial_number"] = config["program_serial_number"]
                    if creds["api_username"] and creds["api_password"]:
                        logger.info(f"Loaded credentials from {cred_path}")
                        return creds
            except Exception as e:
                logger.warning(f"Failed to load from {cred_path}: {e}")

    return creds


def get_oauth_token(api_username: str, api_password: str) -> str:
    """Get OAuth access token from FortiCloud IAM."""
    payload = {
        "username": api_username,
        "password": api_password,
        "client_id": CLIENT_ID,
        "grant_type": "password"
    }

    logger.info(f"Requesting OAuth token for client_id: {CLIENT_ID}")
    response = requests.post(AUTH_URL, json=payload, timeout=30)
    response.raise_for_status()

    result = response.json()

    if result.get("status") != "success":
        raise Exception(f"Authentication failed: {result.get('message', 'Unknown error')}")

    logger.info(f"Token obtained, expires in {result.get('expires_in')}s")
    return result["access_token"]


def create_vm_entitlements(
    token: str,
    config_id: int,
    count: int = 1,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create VM entitlements (tokens) for FortiFlex.

    Uses the entitlements/vm/create endpoint for virtual appliances:
    - FortiGate-VM
    - FortiManager-VM
    - FortiAnalyzer-VM

    Args:
        token: OAuth access token
        config_id: FortiFlex configuration ID
        count: Number of tokens to create
        end_date: Optional end date (YYYY-MM-DD)

    Returns:
        API response with created tokens (includes token directly)
    """
    url = f"{FORTIFLEX_API_BASE}/entitlements/vm/create"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload: Dict[str, Any] = {
        "configId": config_id,
        "count": count
    }
    if end_date:
        payload["endDate"] = end_date

    logger.info(f"Creating {count} FortiFlex token(s) for config {config_id}")
    logger.info(f"Payload: {payload}")

    response = requests.post(url, headers=headers, json=payload, timeout=60)

    # Capture detailed error on failure
    if response.status_code != 200:
        try:
            error_data = response.json()
            error_msg = error_data.get("message") or error_data.get("error") or str(error_data)
            logger.error(f"API Error ({response.status_code}): {error_msg}")
            logger.error(f"Full response: {error_data}")
            raise Exception(f"API Error ({response.status_code}): {error_msg}")
        except ValueError:
            logger.error(f"HTTP {response.status_code}: {response.text}")
            raise Exception(f"HTTP {response.status_code}: {response.text}")

    response.raise_for_status()

    return response.json()


def get_entitlement_token(token: str, serial_number: str) -> Optional[str]:
    """
    Get the actual license token for an entitlement.

    Args:
        token: OAuth access token
        serial_number: Entitlement serial number

    Returns:
        License token string or None
    """
    url = f"{FORTIFLEX_API_BASE}/entitlements/vm/token"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {"serialNumber": serial_number}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        return result.get("entitlements", [{}])[0].get("token")
    except Exception as e:
        logger.warning(f"Could not retrieve token for {serial_number}: {e}")
        return None


def execute(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the tool (synchronous - all requests are blocking)."""
    logger.info("Executing FortiFlex Token Create")

    try:
        # Validate required parameters
        config_id = params.get("config_id")
        if not config_id:
            return {"success": False, "error": "Missing required parameter: config_id"}

        count = params.get("count", 1)
        if count < 1 or count > 10:
            return {"success": False, "error": "count must be between 1 and 10"}

        end_date = params.get("end_date")

        # Load credentials
        creds = load_credentials(params)
        if not creds["api_username"] or not creds["api_password"]:
            return {
                "success": False,
                "error": "No credentials found. Provide api_username/api_password."
            }

        # Get OAuth token
        oauth_token = get_oauth_token(creds["api_username"], creds["api_password"])

        # Create VM entitlements (uses entitlements/vm/create endpoint)
        result = create_vm_entitlements(oauth_token, config_id, count, end_date)

        # Check response
        if result.get("status") != 0:
            return {
                "success": False,
                "error": result.get("message") or result.get("error") or "Unknown API error"
            }

        # Extract created entitlements
        entitlements = result.get("entitlements", [])

        # Format tokens - token is included directly in VM entitlement response
        tokens: List[Dict[str, Any]] = []
        for ent in entitlements:
            serial_number = ent.get("serialNumber")

            # Token is returned directly from vm/create endpoint
            license_token = ent.get("token")

            # If token not in response, try to fetch it separately
            if not license_token and serial_number:
                license_token = get_entitlement_token(oauth_token, serial_number)

            tokens.append({
                "serial_number": serial_number,
                "token": license_token,
                "config_id": ent.get("configId"),
                "status": ent.get("status"),
                "start_date": ent.get("startDate"),
                "end_date": ent.get("endDate"),
                "token_status": ent.get("tokenStatus"),
                "account_id": ent.get("accountId")
            })

        return {
            "success": True,
            "tokens_created": len(tokens),
            "tokens": tokens
        }

    except requests.exceptions.HTTPError as e:
        error_detail = str(e)
        try:
            error_body = e.response.json()
            error_detail = error_body.get("message") or error_body.get("error") or str(e)
        except Exception:
            pass
        logger.exception(f"HTTP error: {error_detail}")
        return {"success": False, "error": f"HTTP error: {error_detail}"}

    except Exception as e:
        logger.exception(f"Tool error: {e}")
        return {"success": False, "error": str(e)}


def main(context) -> Dict[str, Any]:
    """Entry point for MCP execution."""
    if hasattr(context, "parameters"):
        params = context.parameters
    elif isinstance(context, dict):
        params = context
    else:
        params = {}

    return execute(params)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python tool.py <config_id> [count]")
        sys.exit(1)

    test_params = {"config_id": int(sys.argv[1])}
    if len(sys.argv) > 2:
        test_params["count"] = int(sys.argv[2])

    result = main(test_params)
    print(json.dumps(result, indent=2))
