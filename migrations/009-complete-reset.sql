-- Migration 009: Complete Reset and Recreate All New Tables
-- This migration safely drops and recreates all tables for the new features
-- Created: October 20, 2025, 7:46 PM IST

-- Drop existing tables (if they exist) to start fresh
DROP TABLE IF EXISTS ai_learning CASCADE;
DROP TABLE IF EXISTS ai_actions CASCADE;
DROP TABLE IF EXISTS ai_interactions CASCADE;
DROP TABLE IF EXISTS error_logs CASCADE;
DROP TABLE IF EXISTS payroll_records CASCADE;
DROP TABLE IF EXISTS employee_salaries CASCADE;
DROP TABLE IF EXISTS infrastructure_costs CASCADE;
DROP TABLE IF EXISTS expenses CASCADE;

-- 1. Employee Salaries Table (NOW REFERENCES employees.id correctly)
CREATE TABLE employee_salaries (
    salary_id SERIAL PRIMARY KEY,
    emp_id INTEGER REFERENCES employees(id) ON DELETE CASCADE UNIQUE,
    base_salary DECIMAL(10,2) NOT NULL,
    allowances DECIMAL(10,2) DEFAULT 0.00,
    deductions DECIMAL(10,2) DEFAULT 0.00,
    net_salary DECIMAL(10,2) NOT NULL,
    effective_from DATE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 2. Payroll Records Table
CREATE TABLE payroll_records (
    payroll_id SERIAL PRIMARY KEY,
    emp_id INTEGER REFERENCES employees(id) ON DELETE CASCADE,
    month INTEGER CHECK (month BETWEEN 1 AND 12),
    year INTEGER CHECK (year >= 2025),
    base_salary DECIMAL(10,2) NOT NULL,
    allowances DECIMAL(10,2) DEFAULT 0.00,
    deductions DECIMAL(10,2) DEFAULT 0.00,
    net_salary DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'cancelled')),
    paid_on TIMESTAMP,
    payment_method VARCHAR(50),
    transaction_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (emp_id, month, year)
);

-- 3. Expenses Table
CREATE TABLE expenses (
    expense_id SERIAL PRIMARY KEY,
    category VARCHAR(50) NOT NULL CHECK (category IN ('infrastructure', 'marketing', 'operations', 'salary', 'misc')),
    amount DECIMAL(10,2) NOT NULL,
    description TEXT NOT NULL,
    date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 4. Infrastructure Costs Table
CREATE TABLE infrastructure_costs (
    cost_id SERIAL PRIMARY KEY,
    service VARCHAR(50) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    billing_period VARCHAR(20) CHECK (billing_period IN ('daily', 'monthly', 'annual')),
    date DATE NOT NULL,
    details JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 5. AI Interactions Table
CREATE TABLE ai_interactions (
    interaction_id SERIAL PRIMARY KEY,
    admin_id INTEGER,
    message TEXT NOT NULL,
    response TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- 6. AI Actions Table
CREATE TABLE ai_actions (
    action_id SERIAL PRIMARY KEY,
    action_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50),
    entity_id INTEGER,
    details JSONB,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- 7. AI Learning Table
CREATE TABLE ai_learning (
    learning_id SERIAL PRIMARY KEY,
    feedback_type VARCHAR(50) NOT NULL,
    data JSONB NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- 8. Error Logs Table (for AI bug detection)
CREATE TABLE error_logs (
    error_id SERIAL PRIMARY KEY,
    error_type VARCHAR(100) NOT NULL,
    error_message TEXT,
    stack_trace TEXT,
    user_id INTEGER,
    endpoint VARCHAR(255),
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_payroll_records_emp ON payroll_records(emp_id);
CREATE INDEX idx_payroll_records_month ON payroll_records(month, year);
CREATE INDEX idx_expenses_date ON expenses(date);
CREATE INDEX idx_expenses_category ON expenses(category);
CREATE INDEX idx_infra_costs_service ON infrastructure_costs(service);
CREATE INDEX idx_infra_costs_date ON infrastructure_costs(date);
CREATE INDEX idx_ai_interactions_admin ON ai_interactions(admin_id);
CREATE INDEX idx_ai_actions_timestamp ON ai_actions(timestamp);
CREATE INDEX idx_error_logs_timestamp ON error_logs(timestamp);
CREATE INDEX idx_error_logs_type ON error_logs(error_type);

-- Sample data for testing
INSERT INTO infrastructure_costs (service, amount, billing_period, date, details)
VALUES 
    ('railway', 500, 'monthly', CURRENT_DATE, '{"plan": "hobby", "users": 100}'),
    ('sendgrid', 150, 'monthly', CURRENT_DATE, '{"emails_sent": 5000}'),
    ('openai', 300, 'monthly', CURRENT_DATE, '{"api_calls": 10000}');

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ Migration 009 (COMPLETE RESET) completed successfully!';
    RAISE NOTICE '📊 All tables dropped and recreated with correct foreign keys';
    RAISE NOTICE '🎯 Now using employees(id) consistently across all tables';
END $$;
