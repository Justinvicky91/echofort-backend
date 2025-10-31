-- Migration 014: Employees Table for Role-Based Access
-- Supports Super Admin, Admin, and Employee roles

CREATE TABLE IF NOT EXISTS employees (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL, -- super_admin, admin, marketing, customer_support, accounting, hr
    department VARCHAR(100),
    is_super_admin BOOLEAN DEFAULT false,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_employees_username ON employees(username);
CREATE INDEX IF NOT EXISTS idx_employees_role ON employees(role);
CREATE INDEX IF NOT EXISTS idx_employees_active ON employees(active);
CREATE INDEX IF NOT EXISTS idx_employees_super_admin ON employees(is_super_admin);

-- Add comments
COMMENT ON TABLE employees IS 'Employee accounts with role-based access';
COMMENT ON COLUMN employees.role IS 'Employee role: super_admin, admin, marketing, customer_support, accounting, hr';
COMMENT ON COLUMN employees.is_super_admin IS 'Super admin flag - only one super admin should exist';

