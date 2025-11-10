#!/usr/bin/env python3
"""
FortiFlex MSSP API Client

A comprehensive Python client for managing FortiFlex MSSP operations including:
- Customer onboarding
- Configuration management
- Entitlement provisioning
- Consumption tracking
- Multi-tenant operations

Version: 1.0
Author: Fortinet MSSP SE Team
License: MIT
"""

import requests
import json
import time
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FortiFlexClient:
    """
    Main client for FortiFlex API operations.

    Handles authentication, rate limiting, and provides methods for all
    FortiFlex MSSP use cases.
    """

    def __init__(self, token: str, program_sn: str):
        """
        Initialize FortiFlex client.

        Args:
            token: OAuth access token
            program_sn: Program serial number (ELAVMSXXXXXXXX)
        """
        self.token = token
        self.program_sn = program_sn
        self.base_url = "https://support.fortinet.com/ES/api/fortiflex/v2"
        self.asset_base_url = "https://support.fortinet.com/ES/api/registration/v3"

    def _make_request(self, endpoint: str, payload: Dict) -> Dict:
        """
        Make authenticated request to FortiFlex API.

        Args:
            endpoint: API endpoint path
            payload: Request payload

        Returns:
            API response as dictionary

        Raises:
            requests.exceptions.HTTPError: On HTTP errors
        """
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        logger.debug(f"Request to {endpoint}: {json.dumps(payload, indent=2)}")

        response = requests.post(url, headers=headers, json=payload)

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            # Try to extract error message from response body
            try:
                error_data = response.json()
                error_msg = error_data.get('message', error_data.get('error', str(e)))
                logger.error(f"API Error ({response.status_code}): {error_msg}")
                logger.error(f"Full response: {json.dumps(error_data, indent=2)}")
                raise Exception(f"{response.status_code} {response.reason}: {error_msg}") from e
            except (ValueError, KeyError):
                logger.error(f"HTTP Error: {e}")
                raise

        result = response.json()
        logger.debug(f"Response from {endpoint}: {json.dumps(result, indent=2)}")

        return result

    # ========================================================================
    # Configuration Management
    # ========================================================================

    def create_config(self, name: str, product_type_id: int,
                     parameters: List[Dict], account_id: Optional[int] = None) -> Dict:
        """
        Create a new configuration.

        Args:
            name: Configuration name
            product_type_id: Product type ID (101=FortiGate HW, 102=FortiAP, etc.)
            parameters: List of parameter dicts with 'id' and 'value'
            account_id: Optional customer account ID for multi-tenant

        Returns:
            Created configuration details

        Example:
            config = client.create_config(
                name="Customer-A-FGT60F-UTP",
                product_type_id=101,
                account_id=12345,
                parameters=[
                    {"id": 27, "value": "FGT60F"},
                    {"id": 28, "value": "FGHWUTP"},
                    {"id": 29, "value": "FGHWFAZC"}
                ]
            )
        """
        payload = {
            "programSerialNumber": self.program_sn,
            "name": name,
            "productTypeId": product_type_id,
            "parameters": parameters
        }

        if account_id:
            payload["accountId"] = account_id

        logger.info(f"Creating config: {name} (product_type: {product_type_id})")
        return self._make_request("configs/create", payload)

    def update_config(self, config_id: int, name: Optional[str] = None,
                     parameters: Optional[List[Dict]] = None) -> Dict:
        """
        Update configuration name and/or parameters.

        WARNING: This affects ALL entitlements using this config!

        Args:
            config_id: Configuration ID to update
            name: New name (optional)
            parameters: New parameters (optional)

        Returns:
            Updated configuration details
        """
        payload = {"id": config_id}

        if name:
            payload["name"] = name
        if parameters:
            payload["parameters"] = parameters

        logger.info(f"Updating config ID {config_id}")
        return self._make_request("configs/update", payload)

    def list_configs(self, account_id: Optional[int] = None) -> Dict:
        """
        List configurations for account or all accounts.

        Args:
            account_id: Optional customer account ID. Omit to get all accounts.

        Returns:
            List of configurations
        """
        payload = {"programSerialNumber": self.program_sn}

        if account_id:
            payload["accountId"] = account_id

        logger.info(f"Listing configs for account: {account_id or 'ALL'}")
        return self._make_request("configs/list", payload)

    def disable_config(self, config_id: int) -> Dict:
        """
        Disable configuration (affects all entitlements).

        Args:
            config_id: Configuration ID

        Returns:
            Operation result
        """
        payload = {"id": config_id}
        logger.info(f"Disabling config ID {config_id}")
        return self._make_request("configs/disable", payload)

    def enable_config(self, config_id: int) -> Dict:
        """
        Enable configuration.

        Args:
            config_id: Configuration ID

        Returns:
            Operation result
        """
        payload = {"id": config_id}
        logger.info(f"Enabling config ID {config_id}")
        return self._make_request("configs/enable", payload)

    # ========================================================================
    # Entitlement Management
    # ========================================================================

    def create_hardware_entitlements(self, config_id: int,
                                    serial_numbers: List[str],
                                    end_date: Optional[str] = None) -> Dict:
        """
        Create hardware entitlements.

        Args:
            config_id: Configuration ID
            serial_numbers: List of device serial numbers
            end_date: Optional end date (YYYY-MM-DD). None = program end date

        Returns:
            Created entitlements details

        Example:
            result = client.create_hardware_entitlements(
                config_id=12345,
                serial_numbers=["FGT60FTK20001234", "FGT60FTK20001235"]
            )
        """
        payload = {
            "configId": config_id,
            "serialNumbers": serial_numbers,
            "endDate": end_date
        }

        logger.info(f"Creating {len(serial_numbers)} hardware entitlements for config {config_id}")
        return self._make_request("entitlements/hardware/create", payload)

    def create_cloud_entitlements(self, config_id: int,
                                 count: int = 1,
                                 end_date: Optional[str] = None) -> Dict:
        """
        Create cloud service entitlements.

        Args:
            config_id: Configuration ID
            count: Number of entitlements to create (default: 1)
            end_date: Optional end date (YYYY-MM-DD)

        Returns:
            Created cloud entitlement details (includes generated serial)
        """
        payload = {
            "configId": config_id,
            "count": count
        }

        # Only include endDate if specified (API may reject null values)
        if end_date:
            payload["endDate"] = end_date

        logger.info(f"Creating {count} cloud entitlement(s) for config {config_id}")
        logger.debug(f"Payload: {payload}")
        return self._make_request("entitlements/cloud/create", payload)

    def update_entitlement(self, serial_number: str, config_id: int,
                          description: Optional[str] = None,
                          end_date: Optional[str] = None) -> Dict:
        """
        Update entitlement to use different config.

        Args:
            serial_number: Device serial number
            config_id: New configuration ID
            description: Optional description
            end_date: Optional new end date

        Returns:
            Updated entitlement details
        """
        payload = {
            "serialNumber": serial_number,
            "configId": config_id
        }

        if description:
            payload["description"] = description
        if end_date:
            payload["endDate"] = end_date

        logger.info(f"Updating entitlement {serial_number} to config {config_id}")
        return self._make_request("entitlements/update", payload)

    def stop_entitlement(self, serial_number: str) -> Dict:
        """
        Stop an entitlement (billing stops next day).

        Args:
            serial_number: Device serial number

        Returns:
            Updated entitlement status
        """
        payload = {"serialNumber": serial_number}
        logger.info(f"Stopping entitlement {serial_number}")
        return self._make_request("entitlements/stop", payload)

    def reactivate_entitlement(self, serial_number: str) -> Dict:
        """
        Reactivate a stopped entitlement (billing resumes same day).

        Args:
            serial_number: Device serial number

        Returns:
            Updated entitlement status
        """
        payload = {"serialNumber": serial_number}
        logger.info(f"Reactivating entitlement {serial_number}")
        return self._make_request("entitlements/reactivate", payload)

    # ========================================================================
    # Point Consumption & Billing
    # ========================================================================

    def get_entitlement_points(self, config_id: Optional[int] = None,
                              serial_number: Optional[str] = None,
                              account_id: Optional[int] = None,
                              start_date: Optional[str] = None,
                              end_date: Optional[str] = None) -> Dict:
        """
        Get point consumption for entitlements.

        Args:
            config_id: Filter by configuration ID (optional)
            serial_number: Filter by serial number (optional)
            account_id: Account ID (required per API spec)
            start_date: Start date YYYY-MM-DD (optional)
            end_date: End date YYYY-MM-DD (optional)

        Returns:
            Consumption data by entitlement

        Example:
            # Get yesterday's consumption
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            consumption = client.get_entitlement_points(
                account_id=YOUR_ACCOUNT_ID,
                start_date=yesterday,
                end_date=datetime.now().strftime("%Y-%m-%d")
            )
        """
        # Build payload matching reference implementation order
        payload = {
            "programSerialNumber": self.program_sn,
            "accountId": account_id,
            "startDate": start_date,
            "endDate": end_date
        }

        # Add optional filters
        if config_id:
            payload["configId"] = config_id
        if serial_number:
            payload["serialNumber"] = serial_number

        logger.info(f"Getting point consumption from {start_date} to {end_date}")
        if serial_number:
            logger.info(f"Filtering by serial number: {serial_number}")
        if account_id:
            logger.info(f"Account ID: {account_id}")

        # DEBUG: Log exact payload
        import json as json_lib
        logger.info(f"API Request Payload: {json_lib.dumps(payload, indent=2)}")

        return self._make_request("entitlements/points", payload)

    def get_program_points(self) -> Dict:
        """
        Get program point balance (prepaid programs only).

        Returns:
            Program point balance and details
        """
        payload = {"programSerialNumber": self.program_sn}
        logger.info(f"Getting program points for {self.program_sn}")
        return self._make_request("programs/points", payload)

    def calculate_points(self, product_type_id: int, count: int,
                        parameters: List[Dict]) -> Dict:
        """
        Calculate expected point consumption.

        Args:
            product_type_id: Product type ID
            count: Number of devices/units
            parameters: Configuration parameters

        Returns:
            Point calculation (current, latest, effective date)

        Example:
            cost = client.calculate_points(
                product_type_id=101,
                count=3,
                parameters=[
                    {"id": 27, "value": "FGT60F"},
                    {"id": 28, "value": "FGHWUTP"}
                ]
            )
            # Returns: {"points": {"current": 12.5, "latest": 12.5}}
        """
        payload = {
            "programSerialNumber": self.program_sn,
            "productTypeId": product_type_id,
            "count": count,
            "parameters": parameters
        }

        logger.info(f"Calculating points for product {product_type_id} x {count}")
        return self._make_request("tools/calc", payload)

    # ========================================================================
    # Asset Management (FortiCloud Organization)
    # ========================================================================

    def move_to_folder(self, serial_numbers: List[str], folder_id: Optional[int],
                      asset_token: str) -> None:
        """
        Move products to specific folder in FortiCloud.

        Args:
            serial_numbers: List of serial numbers
            folder_id: Folder ID (None = My Assets root)
            asset_token: Asset Management API token (not FortiFlex token!)

        Note:
            Requires separate OAuth token with assetmanagement client_id
        """
        url = f"{self.asset_base_url}/products/folder"
        headers = {
            "Authorization": f"Bearer {asset_token}",
            "Content-Type": "application/json"
        }

        for serial in serial_numbers:
            payload = {
                "serialNumber": serial,
                "folderId": folder_id
            }

            logger.info(f"Moving {serial} to folder {folder_id}")
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()

    # ========================================================================
    # Multi-Tenant Operations
    # ========================================================================

    def get_multi_tenant_view(self) -> Dict[int, List[Dict]]:
        """
        Get configurations for all tenant accounts.

        Returns:
            Dictionary mapping account_id -> list of configs

        Example:
            customers = client.get_multi_tenant_view()
            for account_id, configs in customers.items():
                print(f"Account {account_id}: {len(configs)} configs")
        """
        # Omit accountId to get ALL tenants under program
        configs = self.list_configs()

        # Group by account
        by_account = {}
        for config in configs['configs']:
            account_id = config['accountId']
            if account_id not in by_account:
                by_account[account_id] = []
            by_account[account_id].append(config)

        logger.info(f"Retrieved multi-tenant view: {len(by_account)} accounts")
        return by_account


class RateLimiter:
    """
    Thread-safe rate limiter for FortiFlex API.

    Limits:
    - 100 requests per minute
    - 1000 requests per hour
    """

    def __init__(self, max_per_minute: int = 90, max_per_hour: int = 900):
        """
        Initialize rate limiter.

        Args:
            max_per_minute: Max requests per minute (default: 90, below 100 limit)
            max_per_hour: Max requests per hour (default: 900, below 1000 limit)
        """
        self.max_per_minute = max_per_minute
        self.max_per_hour = max_per_hour
        self.minute_calls = []
        self.hour_calls = []

    def wait_if_needed(self) -> None:
        """Block if rate limits would be exceeded."""
        now = time.time()

        # Remove old entries
        minute_ago = now - 60
        self.minute_calls = [t for t in self.minute_calls if t > minute_ago]

        hour_ago = now - 3600
        self.hour_calls = [t for t in self.hour_calls if t > hour_ago]

        # Check limits
        if len(self.minute_calls) >= self.max_per_minute:
            sleep_time = 60 - (now - self.minute_calls[0])
            if sleep_time > 0:
                logger.warning(f"Rate limit: sleeping {sleep_time:.1f}s")
                time.sleep(sleep_time)

        if len(self.hour_calls) >= self.max_per_hour:
            sleep_time = 3600 - (now - self.hour_calls[0])
            if sleep_time > 0:
                logger.warning(f"Rate limit: sleeping {sleep_time:.1f}s")
                time.sleep(sleep_time)

        # Record this call
        self.minute_calls.append(now)
        self.hour_calls.append(now)


def get_oauth_token(api_username: str, api_password: str,
                   client_id: str = "flexvm") -> str:
    """
    Get OAuth access token for FortiFlex API.

    Args:
        api_username: FortiCloud IAM API username
        api_password: FortiCloud IAM API password
        client_id: Client ID (flexvm for FortiFlex, assetmanagement for Asset Mgmt)

    Returns:
        Access token (valid for 1 hour)

    Raises:
        requests.exceptions.HTTPError: On authentication failure

    Example:
        token = get_oauth_token(
            api_username="217CD4CB-742D-439A-B907-460AF16D894C",
            api_password="261284a4dbfad754c7cc052eaa9f8cbf!1Aa",
            client_id="flexvm"
        )
    """
    url = "https://customerapiauth.fortinet.com/api/v1/oauth/token/"
    payload = {
        "username": api_username,
        "password": api_password,
        "client_id": client_id,
        "grant_type": "password"
    }

    logger.info(f"Getting OAuth token for client_id: {client_id}")
    response = requests.post(url, json=payload)
    response.raise_for_status()

    result = response.json()

    if result.get("status") != "success":
        raise Exception(f"Authentication failed: {result.get('message')}")

    logger.info(f"Token obtained, expires in {result.get('expires_in')}s")
    return result["access_token"]


def retry_with_backoff(func, max_retries: int = 3, base_delay: int = 1,
                       max_delay: int = 60):
    """
    Retry function with exponential backoff.

    Args:
        func: Function to retry
        max_retries: Maximum retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds

    Returns:
        Function result

    Raises:
        Exception: After all retries exhausted
    """
    for attempt in range(max_retries):
        try:
            return func()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code in [429, 503]:
                # Rate limit or service unavailable - retry
                delay = min(base_delay * (2 ** attempt), max_delay)
                logger.warning(f"Retry {attempt + 1}/{max_retries} in {delay}s...")
                time.sleep(delay)
                continue
            else:
                # Other HTTP error - don't retry
                raise

        except requests.exceptions.RequestException as e:
            # Network error - retry
            delay = min(base_delay * (2 ** attempt), max_delay)
            logger.warning(f"Network error, retry {attempt + 1}/{max_retries} in {delay}s...")
            time.sleep(delay)
            continue

    # All retries exhausted
    raise Exception(f"Failed after {max_retries} retries")
