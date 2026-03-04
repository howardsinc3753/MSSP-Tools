#!/usr/bin/env python3
"""
FortiFlex Entitlements List Tool

List all FortiFlex entitlements (VM licenses and hardware) under a program.
Returns serial numbers, config assignments, and status.

API Reference: https://support.fortinet.com/ES/api/fortiflex/v2/
Client ID: flexvm

Author: Trust-Bot Tool Maker
Version: 1.0.0
Created: 2026-01-18
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


def load_credentials(params: Dict[str, Any]) -> Dict[str, Any]:
    """Load API credentials, program serial number, and account ID."""
    creds: Dict[str, Any] = {
        "api_username": None,
        "api_password": None,
        "program_serial_number": None,
        "account_id": None
    }

    # Check parameters first
    for key in creds.keys():
        if params.get(key):
            creds[key] = params[key]

    # Check environment variables
    if not creds["api_username"] and os.environ.get("FORTICLOUD_API_USERNAME"):
        creds["api_username"] = os.environ["FORTICLOUD_API_USERNAME"]
    if not creds["api_password"] and os.environ.get("FORTICLOUD_API_PASSWORD"):
        creds["api_password"] = os.environ["FORTICLOUD_API_PASSWORD"]
    if not creds["program_serial_number"] and os.environ.get("FORTIFLEX_PROGRAM_SN"):
        creds["program_serial_number"] = os.environ["FORTIFLEX_PROGRAM_SN"]

    if creds["api_username"] and creds["api_password"]:
        # Also load program SN and account_id from file if not set
        for cred_path in CREDENTIAL_PATHS:
            if cred_path.exists():
                try:
                    with open(cred_path, "r") as f:
                        config = yaml.safe_load(f)
                    if config:
                        if not creds["program_serial_number"] and "program_serial_number" in config:
                            creds["program_serial_number"] = config["program_serial_number"]
                        if not creds["account_id"] and "account_id" in config:
                            creds["account_id"] = config["account_id"]
                        if creds["program_serial_number"]:
                            break
                except Exception:
                    pass
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
                    if "account_id" in config:
                        creds["account_id"] = config["account_id"]
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


def list_entitlements(
    token: str,
    program_serial_number: str,
    config_id: Optional[int] = None,
    serial_number: Optional[str] = None,
    account_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    List all FortiFlex entitlements under a program.

    Args:
        token: OAuth access token
        program_serial_number: Program serial number (ELAVMSXXXXXXXX)
        config_id: Optional filter by config ID
        serial_number: Optional filter by serial number
        account_id: Optional filter by account ID

    Returns:
        API response with entitlements list
    """
    url = f"{FORTIFLEX_API_BASE}/entitlements/list"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload: Dict[str, Any] = {"programSerialNumber": program_serial_number}

    if config_id:
        payload["configId"] = config_id
    if serial_number:
        payload["serialNumber"] = serial_number
    if account_id:
        payload["accountId"] = account_id

    logger.info(f"Listing entitlements for program {program_serial_number}")
    if config_id:
        logger.info(f"  Filtering by config_id: {config_id}")
    if serial_number:
        logger.info(f"  Filtering by serial: {serial_number}")
    if account_id:
        logger.info(f"  Filtering by account_id: {account_id}")

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()

    return response.json()


def execute(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the tool (synchronous)."""
    logger.info("Executing FortiFlex Entitlements List")

    try:
        # Load credentials
        creds = load_credentials(params)
        if not creds["api_username"] or not creds["api_password"]:
            return {
                "success": False,
                "error": "No credentials found. Provide api_username/api_password or configure credential file."
            }

        program_sn = creds["program_serial_number"]
        if not program_sn:
            return {
                "success": False,
                "error": "Missing program_serial_number. Use fortiflex-programs-list to find it."
            }

        # Get OAuth token
        oauth_token = get_oauth_token(creds["api_username"], creds["api_password"])

        # Get account_id from params or credentials (required for MSSP programs)
        account_id = params.get("account_id") or creds.get("account_id")
        if not account_id:
            return {
                "success": False,
                "error": "Missing account_id. Required for MSSP programs. Set in params or credential file."
            }

        # List entitlements
        result = list_entitlements(
            oauth_token,
            program_sn,
            config_id=params.get("config_id"),
            serial_number=params.get("serial_number"),
            account_id=account_id
        )

        # Check response
        if result.get("status") != 0:
            return {
                "success": False,
                "error": result.get("message") or result.get("error") or "Unknown API error"
            }

        # Extract entitlements
        entitlements = result.get("entitlements", [])

        # Format output
        formatted_entitlements: List[Dict[str, Any]] = []
        for ent in entitlements:
            formatted_entitlements.append({
                "serial_number": ent.get("serialNumber"),
                "config_id": ent.get("configId"),
                "config_name": ent.get("configName"),
                "product_type": ent.get("productType", {}).get("name") if isinstance(ent.get("productType"), dict) else ent.get("productType"),
                "status": ent.get("status"),
                "start_date": ent.get("startDate"),
                "end_date": ent.get("endDate"),
                "description": ent.get("description"),
                "token": ent.get("token")
            })

        return {
            "success": True,
            "program_serial_number": program_sn,
            "entitlement_count": len(formatted_entitlements),
            "entitlements": formatted_entitlements
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

    test_params = {}
    if len(sys.argv) > 1:
        test_params["config_id"] = int(sys.argv[1])

    result = main(test_params)
    print(json.dumps(result, indent=2))
