CREATE TABLE IF NOT EXISTS payment_gateways (
    id SERIAL PRIMARY KEY,
    gateway_name VARCHAR(50) UNIQUE NOT NULL,
    api_key TEXT,
    api_secret TEXT,
    is_active BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS invoices (
    id SERIAL PRIMARY KEY,
    invoice_number VARCHAR(50) UNIQUE,
    user_email VARCHAR(255),
    plan VARCHAR(50),
    amount DECIMAL(10, 2),
    invoice_data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
