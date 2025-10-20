-- ==========================================
-- ECHOFORT FIXED MIGRATION v008
-- Creates all new features with proper structure
-- Date: October 20, 2025
-- ==========================================

-- 1. SUBSCRIPTIONS TABLE (for revenue tracking)
CREATE TABLE IF NOT EXISTS subscriptions (
    subscription_id SERIAL PRIMARY KEY,
    user_id INTEGER,
    plan VARCHAR(50) NOT NULL CHECK (plan IN ('basic', 'personal', 'family')),
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'cancelled', 'expired', 'trial')),
    started_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    auto_renew BOOLEAN DEFAULT TRUE,
    payment_method VARCHAR(50),
    last_payment_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_plan ON subscriptions(plan);
CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);

-- 2. EMPLOYEE SALARIES TABLE (simplified - no foreign key initially)
CREATE TABLE IF NOT EXISTS employee_salaries (
    salary_id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL,
    employee_name VARCHAR(255) NOT NULL,
    department VARCHAR(100),
    role VARCHAR(100),
    base_salary DECIMAL(12, 2) NOT NULL,
    allowances DECIMAL(12, 2) DEFAULT 0.00,
    deductions DECIMAL(12, 2) DEFAULT 0.00,
    net_salary DECIMAL(12, 2) GENERATED ALWAYS AS (base_salary + allowances - deductions) STORED,
    effective_from DATE NOT NULL,
    effective_to DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_employee_salaries_emp ON employee_salaries(employee_id);
CREATE INDEX IF NOT EXISTS idx_employee_salaries_active ON employee_salaries(is_active);

-- 3. PAYROLL RECORDS TABLE
CREATE TABLE IF NOT EXISTS payroll_records (
    payroll_id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL,
    employee_name VARCHAR(255) NOT NULL,
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    year INTEGER NOT NULL CHECK (year >= 2024),
    base_salary DECIMAL(12, 2) NOT NULL,
    allowances DECIMAL(12, 2) DEFAULT 0.00,
    deductions DECIMAL(12, 2) DEFAULT 0.00,
    gross_salary DECIMAL(12, 2) GENERATED ALWAYS AS (base_salary + allowances) STORED,
    net_salary DECIMAL(12, 2) GENERATED ALWAYS AS (base_salary + allowances - deductions) STORED,
    payment_date DATE,
    payment_status VARCHAR(50) DEFAULT 'pending' CHECK (payment_status IN ('pending', 'processing', 'paid', 'failed')),
    payment_method VARCHAR(50),
    transaction_id VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(employee_id, month, year)
);

CREATE INDEX IF NOT EXISTS idx_payroll_month_year ON payroll_records(month, year);
CREATE INDEX IF NOT EXISTS idx_payroll_employee ON payroll_records(employee_id);
CREATE INDEX IF NOT EXISTS idx_payroll_status ON payroll_records(payment_status);

-- 4. EXPENSES TABLE
CREATE TABLE IF NOT EXISTS expenses (
    expense_id SERIAL PRIMARY KEY,
    category VARCHAR(100) NOT NULL,
    subcategory VARCHAR(100),
    description TEXT NOT NULL,
    amount DECIMAL(12, 2) NOT NULL,
    date DATE NOT NULL,
    payment_method VARCHAR(50),
    vendor_name VARCHAR(255),
    invoice_number VARCHAR(100),
    is_recurring BOOLEAN DEFAULT FALSE,
    recurring_period VARCHAR(50),
    approved_by INTEGER,
    approval_date TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'paid')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category);
CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date);
CREATE INDEX IF NOT EXISTS idx_expenses_status ON expenses(status);

-- 5. INFRASTRUCTURE COSTS TABLE
CREATE TABLE IF NOT EXISTS infrastructure_costs (
    cost_id SERIAL PRIMARY KEY,
    service VARCHAR(100) NOT NULL,
    provider VARCHAR(100) NOT NULL,
    amount DECIMAL(12, 2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'INR',
    billing_cycle VARCHAR(50) DEFAULT 'monthly' CHECK (billing_cycle IN ('hourly', 'daily', 'monthly', 'yearly', 'one-time')),
    date DATE NOT NULL,
    description TEXT,
    usage_metrics JSONB,
    cost_per_user DECIMAL(12, 2),
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_infra_costs_service ON infrastructure_costs(service);
CREATE INDEX IF NOT EXISTS idx_infra_costs_date ON infrastructure_costs(date);
CREATE INDEX IF NOT EXISTS idx_infra_costs_active ON infrastructure_costs(is_active);

-- 6. AI INTERACTIONS LOG
CREATE TABLE IF NOT EXISTS ai_interactions (
    interaction_id SERIAL PRIMARY KEY,
    admin_id INTEGER,
    message TEXT NOT NULL,
    response TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    execution_time_ms INTEGER,
    success BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_ai_interactions_timestamp ON ai_interactions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_ai_interactions_admin ON ai_interactions(admin_id);

-- 7. AI LEARNING DATA
CREATE TABLE IF NOT EXISTS ai_learning (
    learning_id SERIAL PRIMARY KEY,
    feedback_type VARCHAR(100) NOT NULL,
    data JSONB NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    processed BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_ai_learning_type ON ai_learning(feedback_type);
CREATE INDEX IF NOT EXISTS idx_ai_learning_timestamp ON ai_learning(timestamp DESC);

-- Insert sample data for testing
INSERT INTO subscriptions (user_id, plan, status, started_at) VALUES
(1, 'basic', 'active', NOW() - INTERVAL '30 days'),
(2, 'personal', 'active', NOW() - INTERVAL '60 days'),
(3, 'family', 'active', NOW() - INTERVAL '90 days')
ON CONFLICT DO NOTHING;

INSERT INTO employee_salaries (employee_id, employee_name, department, role, base_salary, allowances, deductions, effective_from) VALUES
(1, 'Justin Vicky', 'Engineering', 'Founder & CEO', 100000.00, 10000.00, 5000.00, '2025-01-01'),
(2, 'Developer 1', 'Engineering', 'Senior Developer', 80000.00, 8000.00, 4000.00, '2025-01-01'),
(3, 'Designer 1', 'Design', 'UI/UX Designer', 60000.00, 6000.00, 3000.00, '2025-01-01')
ON CONFLICT DO NOTHING;

INSERT INTO infrastructure_costs (service, provider, amount, date, description) VALUES
('Railway Hosting', 'Railway', 2000.00, DATE_TRUNC('month', NOW()), 'Backend API hosting'),
('PostgreSQL Database', 'Railway', 1500.00, DATE_TRUNC('month', NOW()), 'Production database'),
('OpenAI API', 'OpenAI', 3000.00, DATE_TRUNC('month', NOW()), 'AI processing costs')
ON CONFLICT DO NOTHING;

INSERT INTO expenses (category, subcategory, description, amount, date, status) VALUES
('Operations', 'Software', 'Development tools subscription', 5000.00, DATE_TRUNC('month', NOW()), 'approved'),
('Marketing', 'Advertising', 'Google Ads campaign', 10000.00, DATE_TRUNC('month', NOW()), 'approved'),
('Operations', 'Utilities', 'Office internet', 2000.00, DATE_TRUNC('month', NOW()), 'approved')
ON CONFLICT DO NOTHING;

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ Migration 008 completed successfully!';
    RAISE NOTICE '📊 Created: subscriptions, employee_salaries, payroll_records, expenses, infrastructure_costs';
    RAISE NOTICE '🤖 Created: ai_interactions, ai_learning';
    RAISE NOTICE '📈 Sample data inserted for testing';
END $$;
