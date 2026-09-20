-- ====================================================================
-- PROJECT: E-Commerce Business Intelligence & Customer Analytics
-- SCRIPT: 01_schema_setup.sql
-- DESCRIPTION: Relational schema DDL, indexing, and analytical views
-- ====================================================================

-- 1. Table Definitions (Star Schema / Relational Model)

CREATE TABLE IF NOT EXISTS dim_customers (
    customer_id VARCHAR(20) PRIMARY KEY,
    first_name VARCHAR(50),
    email VARCHAR(100),
    signup_date DATE NOT NULL,
    region VARCHAR(50),
    acquisition_channel VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS dim_products (
    product_id INTEGER PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    unit_cost DECIMAL(10, 2) NOT NULL,
    margin_percentage DECIMAL(5, 2)
);

CREATE TABLE IF NOT EXISTS fact_orders (
    order_id VARCHAR(20) PRIMARY KEY,
    customer_id VARCHAR(20) NOT NULL,
    order_date TIMESTAMP NOT NULL,
    order_date_only DATE NOT NULL,
    order_status VARCHAR(20) NOT NULL,
    payment_method VARCHAR(30),
    subtotal DECIMAL(10, 2) NOT NULL,
    discount_amount DECIMAL(10, 2) DEFAULT 0.00,
    shipping_fee DECIMAL(10, 2) DEFAULT 0.00,
    total_amount DECIMAL(10, 2) NOT NULL,
    total_cost DECIMAL(10, 2) NOT NULL,
    gross_profit DECIMAL(10, 2) NOT NULL,
    order_sequence INTEGER NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES dim_customers(customer_id)
);

CREATE TABLE IF NOT EXISTS fact_order_items (
    item_id VARCHAR(20) PRIMARY KEY,
    order_id VARCHAR(20) NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    unit_cost DECIMAL(10, 2) NOT NULL,
    line_subtotal DECIMAL(10, 2) NOT NULL,
    line_cost DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES fact_orders(order_id),
    FOREIGN KEY (product_id) REFERENCES dim_products(product_id)
);

-- 2. Performance Indexes
CREATE INDEX IF NOT EXISTS idx_orders_cust ON fact_orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_date ON fact_orders(order_date_only);
CREATE INDEX IF NOT EXISTS idx_orders_status ON fact_orders(order_status);
CREATE INDEX IF NOT EXISTS idx_items_order ON fact_order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_items_product ON fact_order_items(product_id);

-- 3. Analytical Views for Reporting & Dashboards

-- View: Customer Level Lifetime Aggregation
DROP VIEW IF EXISTS vw_customer_order_summary;
CREATE VIEW vw_customer_order_summary AS
SELECT 
    c.customer_id,
    c.region,
    c.acquisition_channel,
    c.signup_date,
    MIN(o.order_date_only) AS first_order_date,
    MAX(o.order_date_only) AS last_order_date,
    COUNT(DISTINCT o.order_id) AS total_orders,
    ROUND(SUM(o.total_amount), 2) AS lifetime_spend,
    ROUND(AVG(o.total_amount), 2) AS avg_order_value,
    ROUND(SUM(o.gross_profit), 2) AS lifetime_gross_profit
FROM customers c
INNER JOIN orders o ON c.customer_id = o.customer_id
WHERE o.order_status = 'Completed'
GROUP BY c.customer_id, c.region, c.acquisition_channel, c.signup_date;

-- View: Monthly Sales & Margin Rollup
DROP VIEW IF EXISTS vw_monthly_sales_summary;
CREATE VIEW vw_monthly_sales_summary AS
SELECT 
    strftime('%Y-%m', order_date_only) AS sales_month,
    COUNT(DISTINCT order_id) AS total_orders,
    COUNT(DISTINCT customer_id) AS active_customers,
    ROUND(SUM(total_amount), 2) AS gross_revenue,
    ROUND(SUM(discount_amount), 2) AS total_discounts,
    ROUND(SUM(gross_profit), 2) AS total_gross_profit,
    ROUND(SUM(gross_profit) * 100.0 / NULLIF(SUM(total_amount), 0), 2) AS gross_margin_pct,
    ROUND(AVG(total_amount), 2) AS avg_order_value
FROM orders
WHERE order_status = 'Completed'
GROUP BY strftime('%Y-%m', order_date_only)
ORDER BY sales_month;
