-- FortiFlex MSSP Toolkit - PostgreSQL Database Schema
--
-- This schema provides long-term storage for FortiFlex consumption data
-- beyond the 3-month retention period in the FortiFlex portal.
--
-- Prerequisites:
--   1. PostgreSQL 12+ installed and running
--   2. Database created: CREATE DATABASE fortiflex;
--   3. User with appropriate permissions
--
-- Installation:
--   psql -U postgres -d fortiflex -f database/schema.sql

-- ============================================================================
-- TABLE: consumption_daily
-- ============================================================================
-- Stores daily point consumption for each entitlement
-- Primary use: Historical trend analysis and billing

CREATE TABLE IF NOT EXISTS consumption_daily (
    id SERIAL PRIMARY KEY,
    serial_number VARCHAR(50) NOT NULL,
    account_id INTEGER NOT NULL,
    config_id INTEGER,
    date DATE NOT NULL,
    points NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    recorded_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Ensure we don't duplicate daily records for the same device
    CONSTRAINT consumption_daily_unique UNIQUE (serial_number, date)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_consumption_serial ON consumption_daily(serial_number);
CREATE INDEX IF NOT EXISTS idx_consumption_date ON consumption_daily(date);
CREATE INDEX IF NOT EXISTS idx_consumption_account ON consumption_daily(account_id);
CREATE INDEX IF NOT EXISTS idx_consumption_recorded ON consumption_daily(recorded_at);

-- Comments for documentation
COMMENT ON TABLE consumption_daily IS 'Daily consumption data for billing and historical analysis';
COMMENT ON COLUMN consumption_daily.serial_number IS 'Device serial number (e.g., FMVMMLTM12345)';
COMMENT ON COLUMN consumption_daily.account_id IS 'FortiFlex account ID';
COMMENT ON COLUMN consumption_daily.config_id IS 'Configuration ID used by this device';
COMMENT ON COLUMN consumption_daily.date IS 'Consumption date (PST/PDT timezone)';
COMMENT ON COLUMN consumption_daily.points IS 'Points consumed on this date';
COMMENT ON COLUMN consumption_daily.recorded_at IS 'When this record was inserted (for audit purposes)';

-- ============================================================================
-- TABLE: configurations
-- ============================================================================
-- Stores configuration templates (product specifications)
-- Primary use: Track configuration changes over time

CREATE TABLE IF NOT EXISTS configurations (
    config_id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    product_type_id INTEGER NOT NULL,
    product_type_name VARCHAR(100),
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Store full configuration as JSON for reference
    configuration_json JSONB
);

CREATE INDEX IF NOT EXISTS idx_config_account ON configurations(account_id);
CREATE INDEX IF NOT EXISTS idx_config_status ON configurations(status);
CREATE INDEX IF NOT EXISTS idx_config_product_type ON configurations(product_type_id);

COMMENT ON TABLE configurations IS 'Configuration templates for devices';
COMMENT ON COLUMN configurations.config_id IS 'FortiFlex configuration ID';
COMMENT ON COLUMN configurations.product_type_id IS '1=FGT-VM, 101=FGT-HW, 102=FAP-HW, etc';
COMMENT ON COLUMN configurations.configuration_json IS 'Full API response for audit trail';

-- ============================================================================
-- TABLE: entitlements
-- ============================================================================
-- Stores active entitlements (devices)
-- Primary use: Track device lifecycle and status changes

CREATE TABLE IF NOT EXISTS entitlements (
    id SERIAL PRIMARY KEY,
    serial_number VARCHAR(50) UNIQUE NOT NULL,
    config_id INTEGER REFERENCES configurations(config_id),
    account_id INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL,
    description VARCHAR(255),
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Store full entitlement data as JSON
    entitlement_json JSONB
);

CREATE INDEX IF NOT EXISTS idx_entitlement_serial ON entitlements(serial_number);
CREATE INDEX IF NOT EXISTS idx_entitlement_config ON entitlements(config_id);
CREATE INDEX IF NOT EXISTS idx_entitlement_account ON entitlements(account_id);
CREATE INDEX IF NOT EXISTS idx_entitlement_status ON entitlements(status);

COMMENT ON TABLE entitlements IS 'Active device entitlements (licenses)';
COMMENT ON COLUMN entitlements.serial_number IS 'Device serial number';
COMMENT ON COLUMN entitlements.status IS 'ACTIVE, STOPPED, PENDING, etc';
COMMENT ON COLUMN entitlements.entitlement_json IS 'Full API response for audit trail';

-- ============================================================================
-- TABLE: program_balance
-- ============================================================================
-- Stores daily program point balance snapshots
-- Primary use: Track consumption trends vs available balance

CREATE TABLE IF NOT EXISTS program_balance (
    id SERIAL PRIMARY KEY,
    program_serial_number VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    total_points NUMERIC(12, 2) NOT NULL,
    consumed_points NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    remaining_points NUMERIC(12, 2) NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT program_balance_unique UNIQUE (program_serial_number, date)
);

CREATE INDEX IF NOT EXISTS idx_program_balance_date ON program_balance(date);
CREATE INDEX IF NOT EXISTS idx_program_balance_program ON program_balance(program_serial_number);

COMMENT ON TABLE program_balance IS 'Daily snapshots of program point balance';
COMMENT ON COLUMN program_balance.program_serial_number IS 'FortiFlex program serial (ELAVMSXXXXXXXX)';
COMMENT ON COLUMN program_balance.total_points IS 'Total points allocated to program';
COMMENT ON COLUMN program_balance.consumed_points IS 'Points consumed to date';
COMMENT ON COLUMN program_balance.remaining_points IS 'Points remaining';

-- ============================================================================
-- VIEW: monthly_consumption_summary
-- ============================================================================
-- Aggregate consumption by month for billing reports

CREATE OR REPLACE VIEW monthly_consumption_summary AS
SELECT
    serial_number,
    account_id,
    DATE_TRUNC('month', date) AS month,
    SUM(points) AS total_points,
    COUNT(DISTINCT date) AS days_active,
    AVG(points) AS avg_daily_points,
    MIN(date) AS first_active_date,
    MAX(date) AS last_active_date
FROM consumption_daily
GROUP BY serial_number, account_id, DATE_TRUNC('month', date)
ORDER BY month DESC, total_points DESC;

COMMENT ON VIEW monthly_consumption_summary IS 'Monthly consumption aggregates for billing';

-- ============================================================================
-- VIEW: account_consumption_summary
-- ============================================================================
-- Aggregate consumption by account for customer billing

CREATE OR REPLACE VIEW account_consumption_summary AS
SELECT
    account_id,
    DATE_TRUNC('month', date) AS month,
    COUNT(DISTINCT serial_number) AS device_count,
    SUM(points) AS total_points,
    AVG(points) AS avg_daily_points
FROM consumption_daily
GROUP BY account_id, DATE_TRUNC('month', date)
ORDER BY month DESC, account_id;

COMMENT ON VIEW account_consumption_summary IS 'Account-level monthly consumption for invoicing';

-- ============================================================================
-- FUNCTION: update_updated_at_column()
-- ============================================================================
-- Automatically update updated_at timestamp on row modification

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to tables with updated_at column
CREATE TRIGGER update_configurations_updated_at BEFORE UPDATE ON configurations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_entitlements_updated_at BEFORE UPDATE ON entitlements
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- SAMPLE QUERIES
-- ============================================================================

-- Get last 30 days consumption for all devices
-- SELECT * FROM consumption_daily WHERE date >= CURRENT_DATE - INTERVAL '30 days' ORDER BY date DESC;

-- Get monthly totals for specific account
-- SELECT month, device_count, total_points FROM account_consumption_summary WHERE account_id = 12345;

-- Find devices with highest consumption last month
-- SELECT serial_number, total_points FROM monthly_consumption_summary
-- WHERE month = DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
-- ORDER BY total_points DESC LIMIT 10;

-- Track program balance over time
-- SELECT date, remaining_points FROM program_balance ORDER BY date DESC LIMIT 30;

-- ============================================================================
-- MAINTENANCE
-- ============================================================================

-- Vacuum and analyze for performance (run monthly)
-- VACUUM ANALYZE consumption_daily;
-- VACUUM ANALYZE configurations;
-- VACUUM ANALYZE entitlements;

-- Check database size
-- SELECT pg_size_pretty(pg_database_size('fortiflex')) AS database_size;

-- Check table sizes
-- SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
-- FROM pg_tables WHERE schemaname = 'public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
