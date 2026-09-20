-- ====================================================================
-- PROJECT: E-Commerce Business Intelligence & Customer Analytics
-- SCRIPT: 03_rfm_customer_segmentation.sql
-- DESCRIPTION: RFM (Recency, Frequency, Monetary) Customer Segmentation
-- Demonstrates: Window Functions (NTILE), Conditional Logic (CASE WHEN),
-- Revenue Distribution, and Customer Segmentation Scoring.
-- ====================================================================

-- Step 1: Calculate raw Recency, Frequency, and Monetary values per customer.
WITH customer_rfm_raw AS (
    SELECT 
        c.customer_id,
        c.first_name,
        c.region,
        c.acquisition_channel,
        -- Recency: Days between customer's last order and the snapshot reference date (max date in dataset)
        julianday((SELECT MAX(order_date_only) FROM orders WHERE order_status = 'Completed')) - 
        julianday(MAX(o.order_date_only)) AS recency_days,
        -- Frequency: Total distinct completed orders
        COUNT(DISTINCT o.order_id) AS frequency_orders,
        -- Monetary: Total gross spend
        ROUND(SUM(o.total_amount), 2) AS monetary_spend,
        -- Profitability: Total gross profit
        ROUND(SUM(o.gross_profit), 2) AS total_profit
    FROM customers c
    INNER JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.order_status = 'Completed'
    GROUP BY c.customer_id, c.first_name, c.region, c.acquisition_channel
),

-- Step 2: Assign Quintile Scores (1 to 5) using NTILE Window Functions
-- Recency: Lower days = Higher score (5 is most recent)
-- Frequency: Higher count = Higher score (5 is most frequent)
-- Monetary: Higher spend = Higher score (5 is highest spend)
rfm_scores AS (
    SELECT 
        customer_id,
        first_name,
        region,
        acquisition_channel,
        recency_days,
        frequency_orders,
        monetary_spend,
        total_profit,
        NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
        NTILE(5) OVER (ORDER BY frequency_orders ASC) AS f_score,
        NTILE(5) OVER (ORDER BY monetary_spend ASC) AS m_score
    FROM customer_rfm_raw
),

-- Step 3: Assign Strategic Customer Segments based on RFM Scores
customer_segments AS (
    SELECT 
        customer_id,
        first_name,
        region,
        acquisition_channel,
        ROUND(recency_days, 1) AS recency_days,
        frequency_orders,
        monetary_spend,
        total_profit,
        r_score,
        f_score,
        m_score,
        (cast(r_score as text) || cast(f_score as text) || cast(m_score as text)) AS rfm_cell,
        CASE 
            WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customers'
            WHEN r_score >= 4 AND f_score <= 2 THEN 'Promising New Customers'
            WHEN r_score >= 3 AND f_score <= 3 AND m_score >= 3 THEN 'Potential Loyalists'
            WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk Customers'
            WHEN r_score <= 2 AND f_score <= 2 AND m_score >= 3 THEN 'High-Value Dormant'
            ELSE 'Lost / Hibernating'
        END AS customer_segment
    FROM rfm_scores
)

-- Step 4: Executive Segment Breakdown (Customer Share vs. Revenue Share)
SELECT 
    customer_segment,
    COUNT(customer_id) AS total_customers,
    ROUND(COUNT(customer_id) * 100.0 / (SELECT COUNT(*) FROM customer_segments), 2) AS customer_share_pct,
    ROUND(SUM(monetary_spend), 2) AS segment_revenue,
    ROUND(SUM(monetary_spend) * 100.0 / (SELECT SUM(monetary_spend) FROM customer_segments), 2) AS revenue_share_pct,
    ROUND(AVG(monetary_spend), 2) AS avg_customer_spend,
    ROUND(AVG(frequency_orders), 1) AS avg_order_frequency,
    ROUND(AVG(recency_days), 1) AS avg_recency_days
FROM customer_segments
GROUP BY customer_segment
ORDER BY segment_revenue DESC;
