"""
FortiFlex MSSP API Client
Enhanced Python library for FortiFlex v2 API with MSSP-specific features

Based on: github.com/movinalot/fortinet-flexvm
Enhanced for: MSSP postpaid billing, rate limiting, multi-tenant operations

Requirements:
    pip install requests python-dotenv

Usage:
    from fortiflex_mssp import FortiFlexMSSP
    
    client = FortiFlexMSSP(
        username="YOUR_API_USER",
        password="YOUR_API_PASS",
        program_sn="ELAVMSXXXXXXXX"
    )
    
    # Create configuration
    config = client.create_config(
        name="Customer-FGT-60F",
        product_type_id=101,
        account_id=12345,
        parameters=[
            {"id": 27, "value": "FGT60F"},
            {"id": 28, "value": "FGHWUTP"}
        ]
    )
"""

import os
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from collections import deque
from threading import Lock
from functools import wraps

import requests
from dotenv import load_dotenv


# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('fortiflex_mssp')


class RateLimiter:
    """Thread-safe rate limiter for FortiFlex API"""
    
    def __init__(self, max_per_minute=90, max_per_hour=900):
        self.max_per_minute = max_per_minute
        self.max_per_hour = max_per_hour
        self.minute_calls = deque()
        self.hour_calls = deque()
        self.lock = Lock()
    
    def wait_if_needed(self):
        """Block if rate limits would be exceeded"""
        with self.lock:
            now = time.time()
            
            # Remove old entries
            minute_ago = now - 60
            while self.minute_calls and self.minute_calls[0] < minute_ago:
                self.minute_calls.popleft()
            
            hour_ago = now - 3600
            while self.hour_calls and self.hour_calls[0] < hour_ago:
                self.hour_calls.popleft()
            
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
            now = time.time()  # Refresh after potential sleep
            self.minute_calls.append(now)
            self.hour_calls.append(now)


def retry_with_backoff(max_retries=3, base_delay=1, max_delay=60):
    """Decorator for retrying failed API calls with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                    
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code in [429, 503]:
                        # Rate limit or service unavailable - retry
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        logger.warning(
                            f"{func.__name__}: HTTP {e.response.status_code}, "
                            f"retry {attempt + 1}/{max_retries} in {delay}s"
                        )
                        time.sleep(delay)
                        continue
                    else:
                        # Other HTTP error - don't retry
                        raise
                        
                except requests.exceptions.RequestException as e:
                    # Network error - retry
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logger.warning(
                        f"{func.__name__}: Network error, "
                        f"retry {attempt + 1}/{max_retries} in {delay}s"
                    )
                    time.sleep(delay)
                    continue
            
            # All retries exhausted
            raise Exception(f"{func.__name__}: Failed after {max_retries} retries")
        
        return wrapper
    return decorator


class FortiFlexMSSP:
    """
    FortiFlex MSSP API Client
    
    Comprehensive client for FortiFlex v2 API with MSSP-specific features:
    - Automatic OAuth token management with refresh
    - Rate limiting (100/min, 1000/hour)
    - Retry logic with exponential backoff
    - Multi-tenant operations
    - Consumption tracking
    """
    
    # API Endpoints
    OAUTH_URL = "https://customerapiauth.fortinet.com/api/v1/oauth/token/"
    BASE_URL = "https://support.fortinet.com/ES/api/fortiflex/v2"
    ASSET_BASE_URL = "https://support.fortinet.com/ES/api/registration/v3"
    
    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        program_sn: Optional[str] = None,
        auto_refresh_token: bool = True,
        enable_rate_limiting: bool = True
    ):
        """
        Initialize FortiFlex MSSP client
        
        Args:
            username: API user username (or set FORTIFLEX_ACCESS_USERNAME env var)
            password: API user password (or set FORTIFLEX_ACCESS_PASSWORD env var)
            program_sn: Program serial number (or set FORTIFLEX_PROGRAM_SN env var)
            auto_refresh_token: Automatically refresh token before expiry
            enable_rate_limiting: Enable rate limiting (recommended)
        """
        self.username = username or os.getenv('FORTIFLEX_ACCESS_USERNAME')
        self.password = password or os.getenv('FORTIFLEX_ACCESS_PASSWORD')
        self.program_sn = program_sn or os.getenv('FORTIFLEX_PROGRAM_SN')
        
        if not self.username or not self.password:
            raise ValueError(
                "API credentials required. Provide username/password or set "
                "FORTIFLEX_ACCESS_USERNAME and FORTIFLEX_ACCESS_PASSWORD env vars."
            )
        
        self.auto_refresh_token = auto_refresh_token
        self.rate_limiter = RateLimiter() if enable_rate_limiting else None
        
        # Token management
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        
        # Asset management token (separate)
        self.asset_token = None
        self.asset_token_expires_at = None
        
        # Get initial token
        self.get_token()
    
    def _check_token_expiry(self):
        """Check if token needs refresh and refresh if needed"""
        if not self.auto_refresh_token:
            return
            
        if self.token_expires_at:
            # Refresh 5 minutes before expiry
            time_remaining = (self.token_expires_at - datetime.now()).total_seconds()
            if time_remaining < 300:  # 5 minutes
                logger.info("Token expiring soon, refreshing...")
                self.get_token()
    
    def _make_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make API request with rate limiting and retry logic
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL
            headers: Request headers
            **kwargs: Additional arguments for requests
            
        Returns:
            Response JSON
        """
        # Rate limiting
        if self.rate_limiter:
            self.rate_limiter.wait_if_needed()
        
        # Token refresh check
        self._check_token_expiry()
        
        # Make request
        response = requests.request(method, url, headers=headers, **kwargs)
        
        # Check for errors
        if response.status_code >= 400:
            logger.error(
                f"API Error: {method} {url} returned {response.status_code}\n"
                f"Response: {response.text}"
            )
        
        response.raise_for_status()
        
        return response.json()
    
    @retry_with_backoff(max_retries=3)
    def get_token(self, client_id: str = "flexvm") -> Dict[str, Any]:
        """
        Get OAuth token
        
        Args:
            client_id: OAuth client ID ("flexvm" or "assetmanagement")
            
        Returns:
            Token response dict
        """
        payload = {
            "username": self.username,
            "password": self.password,
            "client_id": client_id,
            "grant_type": "password"
        }
        
        response = requests.post(
            self.OAUTH_URL,
            headers={"Content-Type": "application/json"},
            json=payload
        )
        response.raise_for_status()
        
        data = response.json()
        
        if client_id == "flexvm":
            self.access_token = data['access_token']
            self.refresh_token = data.get('refresh_token')
            expires_in = data.get('expires_in', 3600)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
            logger.info(f"FortiFlex token obtained, expires at {self.token_expires_at}")
        else:  # assetmanagement
            self.asset_token = data['access_token']
            expires_in = data.get('expires_in', 3600)
            self.asset_token_expires_at = datetime.now() + timedelta(seconds=expires_in)
            logger.info(f"Asset Management token obtained, expires at {self.asset_token_expires_at}")
        
        return data
    
    def _get_headers(self, use_asset_token: bool = False) -> Dict[str, str]:
        """Get request headers with auth token"""
        token = self.asset_token if use_asset_token else self.access_token
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    # ==================== PROGRAMS ====================
    
    @retry_with_backoff()
    def list_programs(self) -> Dict[str, Any]:
        """Get list of FortiFlex programs"""
        url = f"{self.BASE_URL}/programs/list"
        return self._make_request(
            "POST",
            url,
            headers=self._get_headers(),
            json={}
        )
    
    @retry_with_backoff()
    def get_program_points(self, program_sn: Optional[str] = None) -> Dict[str, Any]:
        """
        Get point balance for prepaid program
        
        Note: Returns error for postpaid MSSP programs
        """
        program_sn = program_sn or self.program_sn
        if not program_sn:
            raise ValueError("program_sn required")
            
        url = f"{self.BASE_URL}/programs/points"
        return self._make_request(
            "POST",
            url,
            headers=self._get_headers(),
            json={"programSerialNumber": program_sn}
        )
    
    # ==================== CONFIGURATIONS ====================
    
    @retry_with_backoff()
    def list_configs(
        self,
        program_sn: Optional[str] = None,
        account_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        List configurations
        
        Args:
            program_sn: Program serial number
            account_id: Filter by account ID (omit for all accounts)
        """
        program_sn = program_sn or self.program_sn
        if not program_sn:
            raise ValueError("program_sn required")
            
        url = f"{self.BASE_URL}/configs/list"
        payload = {"programSerialNumber": program_sn}
        
        if account_id:
            payload["accountId"] = account_id
            
        return self._make_request(
            "POST",
            url,
            headers=self._get_headers(),
            json=payload
        )
    
    @retry_with_backoff()
    def create_config(
        self,
        name: str,
        product_type_id: int,
        parameters: List[Dict[str, Any]],
        program_sn: Optional[str] = None,
        account_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create new configuration
        
        Args:
            name: Configuration name
            product_type_id: Product type ID (101=FGT HW, 102=FAP, 103=FSW, 206=EDR)
            parameters: List of parameter dicts [{"id": X, "value": "Y"}]
            program_sn: Program serial number
            account_id: Account ID for multi-tenant
        """
        program_sn = program_sn or self.program_sn
        if not program_sn:
            raise ValueError("program_sn required")
            
        url = f"{self.BASE_URL}/configs/create"
        payload = {
            "programSerialNumber": program_sn,
            "name": name,
            "productTypeId": product_type_id,
            "parameters": parameters
        }
        
        if account_id:
            payload["accountId"] = account_id
            
        logger.info(f"Creating config: {name} (product_type={product_type_id})")
        
        return self._make_request(
            "POST",
            url,
            headers=self._get_headers(),
            json=payload
        )
    
    @retry_with_backoff()
    def update_config(
        self,
        config_id: int,
        name: Optional[str] = None,
        parameters: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Update configuration
        
        WARNING: Affects ALL entitlements using this config!
        
        Args:
            config_id: Configuration ID
            name: New name (optional)
            parameters: New parameters (optional)
        """
        url = f"{self.BASE_URL}/configs/update"
        payload = {"id": config_id}
        
        if name:
            payload["name"] = name
        if parameters:
            payload["parameters"] = parameters
            
        logger.warning(f"Updating config {config_id} - affects all associated entitlements")
        
        return self._make_request(
            "POST",
            url,
            headers=self._get_headers(),
            json=payload
        )
    
    @retry_with_backoff()
    def enable_config(self, config_id: int) -> Dict[str, Any]:
        """Enable configuration"""
        url = f"{self.BASE_URL}/configs/enable"
        return self._make_request(
            "POST",
            url,
            headers=self._get_headers(),
            json={"id": config_id}
        )
    
    @retry_with_backoff()
    def disable_config(self, config_id: int) -> Dict[str, Any]:
        """Disable configuration"""
        url = f"{self.BASE_URL}/configs/disable"
        logger.warning(f"Disabling config {config_id}")
        return self._make_request(
            "POST",
            url,
            headers=self._get_headers(),
            json={"id": config_id}
        )
    
    # ==================== ENTITLEMENTS ====================
    
    @retry_with_backoff()
    def list_entitlements(
        self,
        config_id: Optional[int] = None,
        serial_number: Optional[str] = None,
        account_id: Optional[int] = None,
        program_sn: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List entitlements (VMs/hardware)
        
        Args:
            config_id: Filter by config ID
            serial_number: Filter by serial number
            account_id: Filter by account ID
            program_sn: Program serial number
        """
        program_sn = program_sn or self.program_sn
        if not program_sn:
            raise ValueError("program_sn required")
            
        url = f"{self.BASE_URL}/entitlements/list"
        payload = {"programSerialNumber": program_sn}
        
        if config_id:
            payload["configId"] = config_id
        if serial_number:
            payload["serialNumber"] = serial_number
        if account_id:
            payload["accountId"] = account_id
            
        return self._make_request(
            "POST",
            url,
            headers=self._get_headers(),
            json=payload
        )
    
    @retry_with_backoff()
    def create_hardware_entitlements(
        self,
        config_id: int,
        serial_numbers: List[str],
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create hardware entitlements
        
        Args:
            config_id: Configuration ID
            serial_numbers: List of device serial numbers
            end_date: End date (YYYY-MM-DD format, None = use program end date)
        """
        url = f"{self.BASE_URL}/entitlements/hardware/create"
        payload = {
            "configId": config_id,
            "serialNumbers": serial_numbers,
            "endDate": end_date
        }
        
        logger.info(f"Creating {len(serial_numbers)} hardware entitlements for config {config_id}")
        
        return self._make_request(
            "POST",
            url,
            headers=self._get_headers(),
            json=payload
        )
    
    @retry_with_backoff()
    def create_cloud_entitlements(
        self,
        config_id: int,
        count: int = 1,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create cloud/VM entitlements
        
        Args:
            config_id: Configuration ID
            count: Number of VMs to create
            end_date: End date (YYYY-MM-DD format, None = use program end date)
        """
        url = f"{self.BASE_URL}/entitlements/cloud/create"
        payload = {
            "configId": config_id,
            "count": count,
            "endDate": end_date
        }
        
        logger.info(f"Creating {count} cloud entitlements for config {config_id}")
        
        return self._make_request(
            "POST",
            url,
            headers=self._get_headers(),
            json=payload
        )
    
    @retry_with_backoff()
    def update_entitlement(
        self,
        serial_number: str,
        config_id: Optional[int] = None,
        description: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update entitlement
        
        Args:
            serial_number: Device/VM serial number
            config_id: New configuration ID (to change service level)
            description: New description
            end_date: New end date
        """
        url = f"{self.BASE_URL}/entitlements/update"
        payload = {"serialNumber": serial_number}
        
        if config_id:
            payload["configId"] = config_id
        if description:
            payload["description"] = description
        if end_date:
            payload["endDate"] = end_date
            
        return self._make_request(
            "POST",
            url,
            headers=self._get_headers(),
            json=payload
        )
    
    @retry_with_backoff()
    def stop_entitlement(self, serial_number: str) -> Dict[str, Any]:
        """
        Stop entitlement (billing stops next day)
        
        Args:
            serial_number: Device/VM serial number
        """
        url = f"{self.BASE_URL}/entitlements/stop"
        logger.info(f"Stopping entitlement: {serial_number}")
        
        return self._make_request(
            "POST",
            url,
            headers=self._get_headers(),
            json={"serialNumber": serial_number}
        )
    
    @retry_with_backoff()
    def reactivate_entitlement(self, serial_number: str) -> Dict[str, Any]:
        """
        Reactivate stopped entitlement (billing resumes same day)
        
        Args:
            serial_number: Device/VM serial number
        """
        url = f"{self.BASE_URL}/entitlements/reactivate"
        logger.info(f"Reactivating entitlement: {serial_number}")
        
        return self._make_request(
            "POST",
            url,
            headers=self._get_headers(),
            json={"serialNumber": serial_number}
        )
    
    @retry_with_backoff()
    def regenerate_token(self, serial_number: str) -> Dict[str, Any]:
        """
        Regenerate license token for VM
        
        Args:
            serial_number: VM serial number
        """
        url = f"{self.BASE_URL}/entitlements/token"
        return self._make_request(
            "POST",
            url,
            headers=self._get_headers(),
            json={"serialNumber": serial_number}
        )
    
    # ==================== CONSUMPTION / BILLING ====================
    
    @retry_with_backoff()
    def get_entitlement_points(
        self,
        start_date: str,
        end_date: str,
        config_id: Optional[int] = None,
        serial_number: Optional[str] = None,
        account_id: Optional[int] = None,
        program_sn: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get point consumption for entitlements
        
        CRITICAL for MSSP: Pull daily for billing. Portal only keeps 3 months history!
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            config_id: Filter by config ID
            serial_number: Filter by serial number
            account_id: Filter by account ID
            program_sn: Program serial number
        """
        program_sn = program_sn or self.program_sn
        if not program_sn:
            raise ValueError("program_sn required")
            
        url = f"{self.BASE_URL}/entitlements/points"
        payload = {
            "programSerialNumber": program_sn,
            "startDate": start_date,
            "endDate": end_date
        }
        
        if config_id:
            payload["configId"] = config_id
        if serial_number:
            payload["serialNumber"] = serial_number
        if account_id:
            payload["accountId"] = account_id
            
        return self._make_request(
            "POST",
            url,
            headers=self._get_headers(),
            json=payload
        )
    
    def get_yesterday_consumption(
        self,
        account_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get yesterday's point consumption
        
        Convenience method for daily billing jobs
        """
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")
        
        return self.get_entitlement_points(
            start_date=yesterday,
            end_date=today,
            account_id=account_id
        )
    
    # ==================== TOOLS ====================
    
    @retry_with_backoff()
    def calculate_points(
        self,
        product_type_id: int,
        parameters: List[Dict[str, Any]],
        count: int = 1,
        program_sn: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate point cost estimate
        
        Args:
            product_type_id: Product type ID
            parameters: Parameter list
            count: Number of devices
            program_sn: Program serial number
        """
        program_sn = program_sn or self.program_sn
        if not program_sn:
            raise ValueError("program_sn required")
            
        url = f"{self.BASE_URL}/tools/calc"
        payload = {
            "programSerialNumber": program_sn,
            "productTypeId": product_type_id,
            "parameters": parameters,
            "count": count
        }
        
        return self._make_request(
            "POST",
            url,
            headers=self._get_headers(),
            json=payload
        )
    
    # ==================== MSSP-SPECIFIC HELPERS ====================
    
    def get_multi_tenant_view(self) -> Dict[int, List[Dict[str, Any]]]:
        """
        Get configurations grouped by account (tenant)
        
        Returns:
            Dict mapping account_id to list of configs
        """
        configs = self.list_configs()
        
        by_account = {}
        for config in configs.get('configs', []):
            account_id = config['accountId']
            if account_id not in by_account:
                by_account[account_id] = []
            by_account[account_id].append(config)
        
        return by_account
    
    def suspend_customer(self, account_id: int) -> Dict[str, Any]:
        """
        Suspend all entitlements for a customer
        
        Args:
            account_id: Customer account ID
            
        Returns:
            Dict with suspended serial numbers
        """
        entitlements = self.list_entitlements(account_id=account_id)
        
        results = {
            'account_id': account_id,
            'suspended': [],
            'errors': []
        }
        
        for ent in entitlements.get('entitlements', []):
            if ent['status'] == 'ACTIVE':
                try:
                    self.stop_entitlement(ent['serialNumber'])
                    results['suspended'].append(ent['serialNumber'])
                except Exception as e:
                    results['errors'].append({
                        'serial': ent['serialNumber'],
                        'error': str(e)
                    })
        
        logger.info(f"Suspended {len(results['suspended'])} entitlements for account {account_id}")
        
        return results
    
    def reactivate_customer(self, account_id: int) -> Dict[str, Any]:
        """
        Reactivate all stopped entitlements for a customer
        
        Args:
            account_id: Customer account ID
            
        Returns:
            Dict with reactivated serial numbers
        """
        entitlements = self.list_entitlements(account_id=account_id)
        
        results = {
            'account_id': account_id,
            'reactivated': [],
            'errors': []
        }
        
        for ent in entitlements.get('entitlements', []):
            if ent['status'] == 'STOPPED':
                try:
                    self.reactivate_entitlement(ent['serialNumber'])
                    results['reactivated'].append(ent['serialNumber'])
                except Exception as e:
                    results['errors'].append({
                        'serial': ent['serialNumber'],
                        'error': str(e)
                    })
        
        logger.info(f"Reactivated {len(results['reactivated'])} entitlements for account {account_id}")
        
        return results


# ==================== EXAMPLE USAGE ====================

if __name__ == "__main__":
    # Initialize client (reads from environment variables)
    client = FortiFlexMSSP()
    
    # Example 1: List all programs
    print("\n=== Programs ===")
    programs = client.list_programs()
    for prog in programs.get('programs', []):
        print(f"  {prog['serialNumber']}: {prog.get('startDate')} to {prog.get('endDate')}")
    
    # Example 2: Create FortiGate configuration
    print("\n=== Create Configuration ===")
    fgt_config = client.create_config(
        name="Example-FGT-60F-UTP",
        product_type_id=101,
        account_id=12345,
        parameters=[
            {"id": 27, "value": "FGT60F"},
            {"id": 28, "value": "FGHWUTP"},
            {"id": 29, "value": "NONE"}
        ]
    )
    print(f"  Created config ID: {fgt_config['configs']['id']}")
    
    # Example 3: Get yesterday's consumption
    print("\n=== Yesterday's Consumption ===")
    consumption = client.get_yesterday_consumption()
    total_points = sum(e['points'] for e in consumption.get('entitlements', []))
    print(f"  Total points: {total_points}")
    
    # Example 4: Multi-tenant view
    print("\n=== Multi-Tenant View ===")
    tenants = client.get_multi_tenant_view()
    for account_id, configs in tenants.items():
        print(f"  Account {account_id}: {len(configs)} configs")
