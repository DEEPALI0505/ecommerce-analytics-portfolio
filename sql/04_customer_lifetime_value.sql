-- ====================================================================
-- PROJECT: E-Commerce Business Intelligence & Customer Analytics
-- SCRIPT: 04_customer_lifetime_value.sql
-- DESCRIPTION: Customer Lifetime Value (LTV) & Repurchase Behavior
-- Demonstrates: Window Functions (SUM OVER, LAG OVER, ROW_NUMBER),
-- Inter-Purchase Time Variance, and Churn Drop-Off Rates.
-- ====================================================================

-- Query 1: Running Cumulative Spend & Inter-Purchase Days per Customer
WITH ordered_transactions AS (
    SELECT 
        order_id,
        customer_id,
        order_date_only,
        total_amount,
        gross_profit,
        order_sequence,
        -- Running cumulative spend for this customer
        ROUND(SUM(total_amount) OVER (
            PARTITION BY customer_id 
            ORDER BY order_date_only, order_id
        ), 2) AS running_cumulative_spend,
        -- Previous order date for inter-purchase interval calculation
        LAG(order_date_only, 1) OVER (
            PARTITION BY customer_id 
            ORDER BY order_date_only, order_id
        ) AS prev_order_date
    FROM orders
    WHERE order_status = 'Completed'
)
SELECT 
    order_id,
    customer_id,
    order_date_only,
    order_sequence,
    total_amount,
    running_cumulative_spend,
    prev_order_date,
    CASE 
        WHEN prev_order_date IS NOT NULL 
        THEN cast(julianday(order_date_only) - julianday(prev_order_date) as integer)
        ELSE NULL 
    END AS days_since_prior_order
FROM ordered_transactions
LIMIT 25;


-- Query 2: Repurchase Funnel & Churn Drop-Off by Order Sequence
-- Answering: "What % of customers survive to make a 2nd, 3rd, or 4th purchase?"
WITH customer_max_sequence AS (
    SELECT 
        customer_id,
        MAX(order_sequence) AS max_order_reached
    FROM orders
    WHERE order_status = 'Completed'
    GROUP BY customer_id
),
sequence_counts AS (
    SELECT 
        seq.order_num,
        COUNT(cms.customer_id) AS customers_reached_order
    FROM (
        SELECT 1 AS order_num UNION ALL
        SELECT 2 UNION ALL
        SELECT 3 UNION ALL
        SELECT 4 UNION ALL
        SELECT 5 UNION ALL
        SELECT 6
    ) seq
    LEFT JOIN customer_max_sequence cms ON cms.max_order_reached >= seq.order_num
    GROUP BY seq.order_num
)
SELECT 
    order_num AS order_sequence_milestone,
    customers_reached_order,
    ROUND(customers_reached_order * 100.0 / (SELECT MAX(customers_reached_order) FROM sequence_counts), 2) AS survival_rate_pct,
    ROUND(100.0 - (customers_reached_order * 100.0 / 
        LAG(customers_reached_order, 1, customers_reached_order) OVER (ORDER BY order_num)), 2) AS marginal_churn_rate_pct
FROM sequence_counts
ORDER BY order_sequence_milestone;


-- Query 3: Average Inter-Purchase Days between Consecutive Orders
WITH purchase_intervals AS (
    SELECT 
        order_sequence,
        cast(julianday(order_date_only) - julianday(LAG(order_date_only, 1) OVER (
            PARTITION BY customer_id 
            ORDER BY order_date_only, order_id
        )) as integer) AS days_between_orders
    FROM orders
    WHERE order_status = 'Completed'
)
SELECT 
    order_sequence AS order_transition_to,
    COUNT(*) AS total_transitions,
    ROUND(AVG(days_between_orders), 1) AS avg_days_to_repurchase,
    ROUND(MIN(days_between_orders), 0) AS min_days,
    ROUND(MAX(days_between_orders), 0) AS max_days
FROM purchase_intervals
WHERE days_between_orders IS NOT NULL AND order_sequence <= 5
GROUP BY order_sequence
ORDER BY order_transition_to;
