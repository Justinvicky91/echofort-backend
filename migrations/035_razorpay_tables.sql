-- Razorpay Orders and Refunds Tables

CREATE TABLE IF NOT EXISTS razorpay_orders (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(100) UNIQUE NOT NULL,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    plan VARCHAR(50) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'INR',
    status VARCHAR(20) DEFAULT 'created',
    payment_id VARCHAR(100),
    is_trial BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS refunds (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    payment_id VARCHAR(100) NOT NULL,
    refund_id VARCHAR(100) UNIQUE NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'processing',
    reason TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP
);

-- Indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_razorpay_orders_user_id ON razorpay_orders(user_id);
CREATE INDEX IF NOT EXISTS idx_razorpay_orders_status ON razorpay_orders(status);
CREATE INDEX IF NOT EXISTS idx_refunds_user_id ON refunds(user_id);
CREATE INDEX IF NOT EXISTS idx_refunds_status ON refunds(status);

COMMENT ON TABLE razorpay_orders IS 'Razorpay payment orders tracking';
COMMENT ON TABLE refunds IS 'Refund requests and processing status';
