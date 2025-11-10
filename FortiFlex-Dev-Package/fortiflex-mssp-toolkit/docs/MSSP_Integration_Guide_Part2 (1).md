# FortiFlex MSSP API Integration Guide - Part 2

**Version:** 1.1
**Date:** November 2025
**Status:** ✅ Updated for FortiFlex 25.1.0 with November 2025 bug fixes

> **📌 Important**: This guide reflects November 2025 API updates. See [BUGFIX_USE_CASES.md](../BUGFIX_USE_CASES.md) for recent compatibility patches.

---

## Use Case 4: Daily Consumption Data Pull (Billing)

**Business Scenario:** Pull daily point consumption for all customers to generate monthly invoices. **CRITICAL for MSSP:** Portal only keeps 3 months of history - you MUST store this data!

**Frequency:** Daily automated job (recommended 6:00 AM PST/PDT)

### Step 1: Pull Yesterday's Consumption

```python
from datetime import datetime, timedelta

def get_entitlement_points(self, account_id, config_id=None, serial_number=None,
                           start_date=None, end_date=None):
    """Get point consumption for entitlements"""
    url = f"{self.base_url}/entitlements/points"
    headers = {
        "Authorization": f"Bearer {self.token}",
        "Content-Type": "application/json"
    }

    payload = {
        "programSerialNumber": self.program_sn,
        "accountId": account_id,  # REQUIRED (added Nov 2025)
        "startDate": start_date,
        "endDate": end_date
    }

    if config_id:
        payload["configId"] = config_id
    if serial_number:
        payload["serialNumber"] = serial_number
        
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

# Get yesterday's consumption
yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
today = datetime.now().strftime("%Y-%m-%d")

consumption = client.get_entitlement_points(
    account_id=YOUR_ACCOUNT_ID,  # Required parameter (Nov 2025)
    start_date=yesterday,
    end_date=today
)

> **⚠️ API Change (Nov 2025)**: `account_id` is now required for consumption queries. See [BUGFIX_USE_CASES.md - PATCH 4](../BUGFIX_USE_CASES.md#patch-4-use-case-7---added-account_id-parameter).

print(f"Consumption for {yesterday}:")
for entitlement in consumption['entitlements']:
    print(f"  {entitlement['serialNumber']}: {entitlement['points']} points")
```

### Step 2: Aggregate by Customer

```python
import psycopg2
from decimal import Decimal

def store_daily_consumption(db_conn, consumption_data, date):
    """Store consumption data in database"""
    cursor = db_conn.cursor()
    
    for ent in consumption_data['entitlements']:
        cursor.execute("""
            INSERT INTO daily_consumption 
            (date, serial_number, account_id, points, recorded_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (date, serial_number) 
            DO UPDATE SET points = EXCLUDED.points
        """, (
            date,
            ent['serialNumber'],
            ent['accountId'],
            Decimal(str(ent['points']))
        ))
    
    db_conn.commit()
    cursor.close()

# Connect to database
db = psycopg2.connect("dbname=fortiflex user=app password=xxx")

# Store yesterday's consumption
store_daily_consumption(db, consumption, yesterday)

# Generate customer report
cursor = db.cursor()
cursor.execute("""
    SELECT 
        c.customer_name,
        c.account_id,
        SUM(dc.points) as daily_points,
        COUNT(dc.serial_number) as device_count
    FROM daily_consumption dc
    JOIN customers c ON c.account_id = dc.account_id
    WHERE dc.date = %s
    GROUP BY c.customer_name, c.account_id
    ORDER BY daily_points DESC
""", (yesterday,))

print(f"\nCustomer Daily Summary - {yesterday}")
print("-" * 60)
for row in cursor.fetchall():
    customer, account_id, points, devices = row
    print(f"{customer:30} | {devices:3} devices | {points:8.2f} pts")

cursor.close()
db.close()
```

### Step 3: Monthly Invoice Generation

```python
def generate_monthly_invoice(db_conn, account_id, year, month):
    """Generate monthly invoice for customer"""
    cursor = db_conn.cursor()
    
    # Get monthly totals by product type
    cursor.execute("""
        SELECT 
            pt.product_type_name,
            pt.product_type_id,
            COUNT(DISTINCT dc.serial_number) as device_count,
            SUM(dc.points) as total_points,
            AVG(dc.points) as avg_daily_points
        FROM daily_consumption dc
        JOIN entitlements e ON e.serial_number = dc.serial_number
        JOIN configurations cfg ON cfg.config_id = e.config_id
        JOIN product_types pt ON pt.product_type_id = cfg.product_type_id
        WHERE dc.account_id = %s
          AND EXTRACT(YEAR FROM dc.date) = %s
          AND EXTRACT(MONTH FROM dc.date) = %s
        GROUP BY pt.product_type_name, pt.product_type_id
        ORDER BY total_points DESC
    """, (account_id, year, month))
    
    invoice_lines = cursor.fetchall()
    
    # Calculate totals
    total_points = sum(line[3] for line in invoice_lines)
    point_rate = 0.50  # $0.50 per point (example)
    total_amount = total_points * point_rate
    
    print(f"\nINVOICE - {year}-{month:02d}")
    print("=" * 70)
    print(f"Account ID: {account_id}")
    print("-" * 70)
    print(f"{'Product':<30} {'Devices':>10} {'Points':>15} {'Amount':>12}")
    print("-" * 70)
    
    for product, prod_id, devices, points, avg in invoice_lines:
        amount = points * point_rate
        print(f"{product:<30} {devices:>10} {points:>15.2f} ${amount:>11.2f}")
    
    print("-" * 70)
    print(f"{'TOTAL':<30} {' ':>10} {total_points:>15.2f} ${total_amount:>11.2f}")
    print("=" * 70)
    
    cursor.close()
    return {
        'account_id': account_id,
        'year': year,
        'month': month,
        'total_points': float(total_points),
        'total_amount': float(total_amount),
        'line_items': invoice_lines
    }

# Generate November 2025 invoice for customer
invoice = generate_monthly_invoice(db, account_id=12345, year=2025, month=11)
```

### Automated Daily Job Script

```python
#!/usr/bin/env python3
"""
Daily FortiFlex Consumption Collection Job
Run daily at 6:00 AM PST/PDT via cron
"""

import sys
import logging
from datetime import datetime, timedelta
import requests

# Setup logging
logging.basicConfig(
    filename='/var/log/fortiflex-daily-job.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    try:
        # Get OAuth token
        token = get_oauth_token()
        client = FortiFlexClient(token, "ELAVMS0000XXXXXX")
        
        # Get yesterday's date
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        logging.info(f"Collecting consumption data for {yesterday}")
        
        # Pull consumption for all configs
        configs = client.list_configs()
        
        total_records = 0
        for config in configs['configs']:
            consumption = client.get_entitlement_points(
                config_id=config['id'],
                start_date=yesterday,
                end_date=yesterday
            )
            
            # Store in database
            records = store_daily_consumption(db, consumption, yesterday)
            total_records += records
            
            logging.info(f"Config {config['id']} ({config['name']}): {records} records")
        
        logging.info(f"✅ Successfully collected {total_records} consumption records")
        
        # Check for anomalies
        check_consumption_anomalies(db, yesterday)
        
        return 0
        
    except Exception as e:
        logging.error(f"❌ Daily job failed: {str(e)}", exc_info=True)
        # Send alert email/slack
        send_alert(f"FortiFlex daily job failed: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

---

## Use Case 5: Customer Suspension/Offboarding

**Business Scenario:** Customer hasn't paid or cancels service. Suspend their licenses to stop billing.

> **✅ Updated (Nov 2025)**: Now uses consumption-based discovery instead of deprecated `list_entitlements()`. See [BUGFIX_USE_CASES.md - PATCH 5](../BUGFIX_USE_CASES.md#patch-5-use-case-5---consumption-based-entitlement-discovery).

**Important**: FortiFlex API v2 doesn't provide a direct way to list entitlements. Use consumption data (last 90 days) to find active devices.

### Scenario A: Temporary Suspension (Reversible)

**Use when:** Payment late, temporary service hold

```python
def stop_entitlement(self, serial_number):
    """Stop an entitlement (billing stops next day)"""
    url = f"{self.base_url}/entitlements/stop"
    headers = {
        "Authorization": f"Bearer {self.token}",
        "Content-Type": "application/json"
    }
    
    payload = {"serialNumber": serial_number}
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

def reactivate_entitlement(self, serial_number):
    """Reactivate a stopped entitlement (billing resumes same day)"""
    url = f"{self.base_url}/entitlements/reactivate"
    headers = {
        "Authorization": f"Bearer {self.token}",
        "Content-Type": "application/json"
    }
    
    payload = {"serialNumber": serial_number}
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

# Suspend all customer devices
customer_serials = [
    "FGT60FTK20001234", "FGT60FTK20001235", "FGT60FTK20001236",
    "S124FPTK20001001", "S124FPTK20001002"
    # ... etc
]

for serial in customer_serials:
    result = client.stop_entitlement(serial)
    print(f"✅ Suspended: {serial}")
    print(f"   Status: {result['entitlements'][0]['status']}")  # STOPPED
    print(f"   Billing stops: Tomorrow")

# Later: Reactivate when payment received
for serial in customer_serials:
    result = client.reactivate_entitlement(serial)
    print(f"✅ Reactivated: {serial}")
    print(f"   Billing resumes: Today")
```

### Scenario B: Disable Configuration (All Devices)

**Use when:** Want to suspend all devices using a config

```python
def disable_config(self, config_id):
    """Disable configuration (affects all entitlements)"""
    url = f"{self.base_url}/configs/disable"
    headers = {
        "Authorization": f"Bearer {self.token}",
        "Content-Type": "application/json"
    }
    
    payload = {"id": config_id}
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

def enable_config(self, config_id):
    """Enable configuration"""
    url = f"{self.base_url}/configs/enable"
    headers = {
        "Authorization": f"Bearer {self.token}",
        "Content-Type": "application/json"
    }
    
    payload = {"id": config_id}
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

# Disable customer's FortiGate config
result = client.disable_config(config_id=12345)
print(f"✅ Config disabled")
print(f"   All entitlements using this config are now DISABLED")

# Re-enable later
result = client.enable_config(config_id=12345)
print(f"✅ Config enabled")
```

### Scenario C: Permanent Offboarding

**Use when:** Customer permanently churned, clean up resources

```python
# Step 1: Stop all entitlements first
for serial in customer_serials:
    client.stop_entitlement(serial)

# Step 2: Wait for final billing cycle to complete
print("⏳ Waiting for final billing cycle...")
time.sleep(86400)  # Wait 24 hours

# Step 3: Document final consumption
final_consumption = client.get_entitlement_points(
    account_id=YOUR_ACCOUNT_ID,
    start_date="2025-11-01",
    end_date="2025-11-30"
)

# Step 4: Generate final invoice
final_invoice = generate_monthly_invoice(db, account_id=YOUR_ACCOUNT_ID, year=2025, month=11)
save_invoice_pdf(final_invoice, f"final_invoice_{YOUR_ACCOUNT_ID}_2025_11.pdf")

# Step 5: Disable configs (optional - keeps for reference)
for config in customer_configs:
    client.disable_config(config['id'])

print("✅ Customer offboarding complete")
```

---

## Use Case 6: Multi-Tenant Operations View

**Business Scenario:** MSSP operations team needs visibility across all customers.

### View All Customer Configurations

```python
def get_multi_tenant_view(self):
    """Get configurations for all tenant accounts"""
    # Omit accountId to get ALL tenants under program
    configs = self.list_configs()  # No account_id parameter
    
    # Group by account
    by_account = {}
    for config in configs['configs']:
        account_id = config['accountId']
        if account_id not in by_account:
            by_account[account_id] = []
        by_account[account_id].append(config)
    
    return by_account

# Get all customers
all_customers = client.get_multi_tenant_view()

print(f"Total Customers: {len(all_customers)}")
print("\nCustomer Summary:")
print("-" * 80)

for account_id, configs in all_customers.items():
    print(f"\nAccount ID: {account_id}")
    
    # Count by product type
    product_counts = {}
    for config in configs:
        prod_name = config['productType']['name']
        product_counts[prod_name] = product_counts.get(prod_name, 0) + 1
    
    for prod, count in product_counts.items():
        print(f"  - {prod}: {count} configs")
```

### Cross-Customer Consumption Report

```python
def get_top_consumers(db_conn, start_date, end_date, limit=10):
    """Get top consuming customers"""
    cursor = db_conn.cursor()
    
    cursor.execute("""
        SELECT 
            c.customer_name,
            c.account_id,
            SUM(dc.points) as total_points,
            COUNT(DISTINCT dc.serial_number) as device_count,
            SUM(dc.points) / COUNT(DISTINCT dc.date) as avg_daily_points
        FROM daily_consumption dc
        JOIN customers c ON c.account_id = dc.account_id
        WHERE dc.date BETWEEN %s AND %s
        GROUP BY c.customer_name, c.account_id
        ORDER BY total_points DESC
        LIMIT %s
    """, (start_date, end_date, limit))
    
    return cursor.fetchall()

# Get top 10 consumers for November
top_customers = get_top_consumers(db, "2025-11-01", "2025-11-30", limit=10)

print("\nTop 10 Customers - November 2025")
print("=" * 80)
print(f"{'Customer':<30} {'Devices':>10} {'Total Points':>15} {'Avg Daily':>12}")
print("-" * 80)

for customer, account_id, points, devices, avg_daily in top_customers:
    print(f"{customer:<30} {devices:>10} {points:>15.2f} {avg_daily:>12.2f}")
```

### Real-Time Dashboard Metrics

```python
def get_dashboard_metrics(self, db_conn):
    """Get real-time metrics for ops dashboard"""
    cursor = db_conn.cursor()
    
    # Total active customers
    cursor.execute("SELECT COUNT(DISTINCT account_id) FROM daily_consumption WHERE date = CURRENT_DATE - 1")
    active_customers = cursor.fetchone()[0]
    
    # Total active devices
    cursor.execute("SELECT COUNT(DISTINCT serial_number) FROM daily_consumption WHERE date = CURRENT_DATE - 1")
    active_devices = cursor.fetchone()[0]
    
    # Yesterday's consumption
    cursor.execute("SELECT SUM(points) FROM daily_consumption WHERE date = CURRENT_DATE - 1")
    yesterday_points = cursor.fetchone()[0] or 0
    
    # Month-to-date consumption
    cursor.execute("""
        SELECT SUM(points) FROM daily_consumption 
        WHERE date >= DATE_TRUNC('month', CURRENT_DATE)
    """)
    mtd_points = cursor.fetchone()[0] or 0
    
    # Projected monthly total
    cursor.execute("SELECT EXTRACT(DAY FROM CURRENT_DATE)")
    days_elapsed = cursor.fetchone()[0]
    days_in_month = 30  # Simplified
    projected_monthly = (mtd_points / days_elapsed) * days_in_month if days_elapsed > 0 else 0
    
    cursor.close()
    
    return {
        'active_customers': active_customers,
        'active_devices': active_devices,
        'yesterday_points': float(yesterday_points),
        'mtd_points': float(mtd_points),
        'projected_monthly': float(projected_monthly)
    }

# Display dashboard
metrics = client.get_dashboard_metrics(db)

print("\n" + "=" * 60)
print("FORTIFLEX MSSP DASHBOARD")
print("=" * 60)
print(f"Active Customers:        {metrics['active_customers']:>10}")
print(f"Active Devices:          {metrics['active_devices']:>10}")
print(f"Yesterday's Usage:       {metrics['yesterday_points']:>10.2f} points")
print(f"Month-to-Date:           {metrics['mtd_points']:>10.2f} points")
print(f"Projected Monthly:       {metrics['projected_monthly']:>10.2f} points")
print("=" * 60)
```

---

## Use Case 7: Program Balance Monitoring

**Business Scenario:** For prepaid programs, monitor point balance and alert when low. For MSSP postpaid, track consumption vs. minimum commitment.

> **✅ Updated (Nov 2025)**: Removed deprecated `list_programs()` API call. Program info now provided via credentials. See [BUGFIX_USE_CASES.md - PATCHES 1 & 4](../BUGFIX_USE_CASES.md).

### Prepaid Program Monitoring

```python
def check_program_balance(self):
    """Check prepaid program point balance"""
    result = self.get_program_points()
    
    balance = result['programs'][0]['pointBalance']
    
    # Calculate days remaining at current burn rate
    daily_rate = get_average_daily_consumption(db, days=7)
    days_remaining = balance / daily_rate if daily_rate > 0 else 999
    
    # Alert thresholds
    if days_remaining < 7:
        level = "CRITICAL"
        send_alert(f"🚨 {level}: Only {days_remaining:.1f} days of points remaining!")
    elif days_remaining < 15:
        level = "WARNING"
        send_alert(f"⚠️  {level}: {days_remaining:.1f} days of points remaining")
    elif days_remaining < 30:
        level = "INFO"
        send_alert(f"ℹ️  {level}: {days_remaining:.1f} days of points remaining")
    
    print(f"Point Balance: {balance:,.2f}")
    print(f"Daily Burn Rate: {daily_rate:.2f}")
    print(f"Days Remaining: {days_remaining:.1f}")
    print(f"Alert Level: {level}")
```

### MSSP Postpaid Monitoring

```python
def check_mssp_commitment(db_conn, year):
    """Check MSSP minimum 50,000 points/year commitment"""
    cursor = db_conn.cursor()
    
    # Year-to-date consumption
    cursor.execute("""
        SELECT SUM(points) FROM daily_consumption
        WHERE EXTRACT(YEAR FROM date) = %s
    """, (year,))
    ytd_consumption = cursor.fetchone()[0] or 0
    
    # Days elapsed in year
    cursor.execute("SELECT CURRENT_DATE - DATE_TRUNC('year', CURRENT_DATE)")
    days_elapsed = cursor.fetchone()[0].days
    
    # Projected annual total
    days_in_year = 365
    projected_annual = (ytd_consumption / days_elapsed) * days_in_year if days_elapsed > 0 else 0
    
    # Minimum commitment
    minimum_annual = 50000
    
    # Status
    on_track = projected_annual >= minimum_annual
    shortfall = minimum_annual - projected_annual if not on_track else 0
    
    cursor.close()
    
    print(f"\nMSSP Annual Commitment Status - {year}")
    print("=" * 60)
    print(f"YTD Consumption:         {ytd_consumption:>15,.2f} points")
    print(f"Days Elapsed:            {days_elapsed:>15} days")
    print(f"Projected Annual:        {projected_annual:>15,.2f} points")
    print(f"Minimum Commitment:      {minimum_annual:>15,.2f} points")
    print(f"Status:                  {'✅ ON TRACK' if on_track else '❌ BELOW TARGET'}")
    
    if not on_track:
        print(f"Shortfall:               {shortfall:>15,.2f} points")
        print(f"\n⚠️  Need to increase consumption or true-up at year-end")
    
    return {
        'ytd': float(ytd_consumption),
        'projected': float(projected_annual),
        'minimum': minimum_annual,
        'on_track': on_track,
        'shortfall': float(shortfall)
    }
```

---

## Error Handling Reference

### Common Error Codes

| Error Code | Message | Cause | Solution |
|------------|---------|-------|----------|
| **-1** | Invalid security token | Token expired | Refresh OAuth token |
| **-1** | Authorization denied | No permissions | Check IAM permissions for API user |
| **-1** | Invalid parameter value | Wrong parameter ID/value | Verify parameter IDs for product type |
| **-10** | Exceed max requests in minute | >100 requests/min | Implement rate limiting |
| **-11** | Exceed max requests in hour | >1000 requests/hour | Implement rate limiting |
| **-12** | Failed token process | Multiple simultaneous requests | Serialize API calls |
| **-30** | Exceed max error | >10 errors/hour | Fix validation errors |

### Rate Limiting Implementation

```python
import time
from collections import deque
from threading import Lock

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
                time.sleep(max(0, sleep_time))
                
            if len(self.hour_calls) >= self.max_per_hour:
                sleep_time = 3600 - (now - self.hour_calls[0])
                time.sleep(max(0, sleep_time))
            
            # Record this call
            self.minute_calls.append(now)
            self.hour_calls.append(now)

# Usage
rate_limiter = RateLimiter()

def api_call_with_rate_limit(func, *args, **kwargs):
    """Wrapper for API calls with rate limiting"""
    rate_limiter.wait_if_needed()
    return func(*args, **kwargs)

# Create configs with rate limiting
for customer in customers:
    api_call_with_rate_limit(
        client.create_config,
        name=customer['name'],
        product_type_id=101,
        parameters=customer['params']
    )
```

### Retry Logic with Exponential Backoff

```python
import time
from functools import wraps

def retry_with_backoff(max_retries=3, base_delay=1, max_delay=60):
    """Decorator for retrying failed API calls"""
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
                        print(f"⚠️  Retry {attempt + 1}/{max_retries} in {delay}s...")
                        time.sleep(delay)
                        continue
                    else:
                        # Other HTTP error - don't retry
                        raise
                        
                except requests.exceptions.RequestException as e:
                    # Network error - retry
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    print(f"⚠️  Network error, retry {attempt + 1}/{max_retries} in {delay}s...")
                    time.sleep(delay)
                    continue
            
            # All retries exhausted
            raise Exception(f"Failed after {max_retries} retries")
        
        return wrapper
    return decorator

# Usage
@retry_with_backoff(max_retries=3)
def create_config_with_retry(client, **kwargs):
    return client.create_config(**kwargs)
```

---

## Data Warehouse Schema

**PostgreSQL Schema for MSSP Operations:**

```sql
-- Customers table
CREATE TABLE customers (
    account_id INTEGER PRIMARY KEY,
    customer_name VARCHAR(255) NOT NULL,
    contact_email VARCHAR(255),
    onboarded_date DATE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_customers_status ON customers(status);

-- Configurations table
CREATE TABLE configurations (
    config_id INTEGER PRIMARY KEY,
    account_id INTEGER REFERENCES customers(account_id),
    config_name VARCHAR(255) NOT NULL,
    product_type_id INTEGER NOT NULL,
    product_type_name VARCHAR(100) NOT NULL,
    parameters JSONB NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_configs_account ON configurations(account_id);
CREATE INDEX idx_configs_product_type ON configurations(product_type_id);

-- Entitlements table
CREATE TABLE entitlements (
    serial_number VARCHAR(50) PRIMARY KEY,
    config_id INTEGER REFERENCES configurations(config_id),
    account_id INTEGER REFERENCES customers(account_id),
    description TEXT,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP,
    status VARCHAR(50) NOT NULL,
    token VARCHAR(100),
    token_status VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_entitlements_config ON entitlements(config_id);
CREATE INDEX idx_entitlements_account ON entitlements(account_id);
CREATE INDEX idx_entitlements_status ON entitlements(status);

-- Daily consumption table (CRITICAL - store >3 months)
CREATE TABLE daily_consumption (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    serial_number VARCHAR(50) NOT NULL,
    account_id INTEGER NOT NULL,
    points DECIMAL(10,2) NOT NULL,
    recorded_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, serial_number)
);

CREATE INDEX idx_consumption_date ON daily_consumption(date);
CREATE INDEX idx_consumption_account ON daily_consumption(account_id);
CREATE INDEX idx_consumption_serial ON daily_consumption(serial_number);
CREATE INDEX idx_consumption_account_date ON daily_consumption(account_id, date);

-- Monthly invoices table
CREATE TABLE monthly_invoices (
    invoice_id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES customers(account_id),
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    total_points DECIMAL(12,2) NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL,
    line_items JSONB NOT NULL,
    generated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(account_id, year, month)
);

CREATE INDEX idx_invoices_account ON monthly_invoices(account_id);
CREATE INDEX idx_invoices_period ON monthly_invoices(year, month);

-- API audit log
CREATE TABLE api_audit_log (
    id SERIAL PRIMARY KEY,
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    request_payload JSONB,
    response_status INTEGER,
    response_body JSONB,
    error_message TEXT,
    called_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_endpoint ON api_audit_log(endpoint);
CREATE INDEX idx_audit_timestamp ON api_audit_log(called_at);
```

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Partner Systems                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │   PSA/CRM    │    │   Billing    │    │  Operations  │ │
│  │   System     │    │   System     │    │   Dashboard  │ │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘ │
│         │                   │                    │         │
│         └───────────────────┼────────────────────┘         │
│                             │                              │
└─────────────────────────────┼──────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              FortiFlex Integration Layer                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           API Client Service                         │  │
│  │  - OAuth token management (auto-refresh)             │  │
│  │  - Rate limiting (100/min, 1000/hour)                │  │
│  │  - Retry logic with exponential backoff              │  │
│  │  - Error handling & alerting                         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Scheduled Jobs                             │  │
│  │  - Daily consumption pull (6:00 AM PST)              │  │
│  │  - Monthly invoice generation (1st of month)         │  │
│  │  - Balance monitoring (hourly)                       │  │
│  │  - Anomaly detection                                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Data Layer                                │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐  │
│  │        PostgreSQL Database                           │  │
│  │  - Customers                                         │  │
│  │  - Configurations                                    │  │
│  │  - Entitlements                                      │  │
│  │  - Daily consumption (retain >3 months)             │  │
│  │  - Monthly invoices                                  │  │
│  │  - API audit log                                     │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Fortinet APIs                                  │
├─────────────────────────────────────────────────────────────┤
│  - FortiFlex API (configs, entitlements, points)           │
│  - Asset Management API (products, folders)                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Production-Ready Scripts

> **📦 Reference Implementation**: For production-ready, tested scripts implementing all use cases, see the `/examples` directory:
> - [EXAMPLES_SUMMARY.md](../examples/EXAMPLES_SUMMARY.md) - Complete guide with sample outputs
> - [consumption_report_v2.py](../examples/consumption_report_v2.py) - Use Case 4 implementation
> - [use_case_5_entitlement_suspension_v2.py](../examples/use_case_5_entitlement_suspension_v2.py) - Use Case 5 implementation
> - [use_case_7_program_balance_monitoring.py](../examples/use_case_7_program_balance_monitoring.py) - Use Case 7 implementation
> - All scripts tested with FortiFlex 25.1.0 (November 2025)
> - Includes error handling, rate limiting, and retry logic

---

**END OF GUIDE**

For questions or support:
- FortiFlex Documentation: https://docs.fortinet.com/document/flex-vm/
- Fortinet Support: https://support.fortinet.com
- API Documentation: https://fndn.fortinet.net
- Bug Fixes & Patches: [BUGFIX_USE_CASES.md](../BUGFIX_USE_CASES.md)
