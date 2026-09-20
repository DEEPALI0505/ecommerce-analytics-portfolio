-- ====================================================================
-- PROJECT: E-Commerce Business Intelligence & Customer Analytics
-- SCRIPT: 02_cohort_retention_analysis.sql
-- DESCRIPTION: Monthly Customer Cohort Retention Analysis (Heatmap Query)
-- Demonstrates: Common Table Expressions (CTEs), Window Functions,
-- Date Math, and Conditional Retention Rate Calculation.
-- ====================================================================

-- Step 1: Assign each customer to a Cohort based on the month of their FIRST completed purchase.
WITH customer_first_purchase AS (
    SELECT 
        customer_id,
        MIN(order_date_only) AS first_order_date,
        strftime('%Y-%m', MIN(order_date_only)) AS cohort_month
    FROM orders
    WHERE order_status = 'Completed'
    GROUP BY customer_id
),

-- Step 2: Track all subsequent purchase months for each customer and calculate the Cohort Index (Month Offset: 0, 1, 2, ...).
customer_activities AS (
    SELECT 
        o.customer_id,
        cfp.cohort_month,
        strftime('%Y-%m', o.order_date_only) AS order_month,
        -- Calculate the difference in calendar months between order month and cohort month
        (cast(strftime('%Y', o.order_date_only) as integer) - cast(substr(cfp.cohort_month, 1, 4) as integer)) * 12 +
        (cast(strftime('%m', o.order_date_only) as integer) - cast(substr(cfp.cohort_month, 6, 2) as integer)) AS cohort_index
    FROM orders o
    INNER JOIN customer_first_purchase cfp ON o.customer_id = cfp.customer_id
    WHERE o.order_status = 'Completed'
),

-- Step 3: Calculate the total base size (Month 0) for each Cohort.
cohort_sizes AS (
    SELECT 
        cohort_month,
        COUNT(DISTINCT customer_id) AS cohort_size
    FROM customer_first_purchase
    GROUP BY cohort_month
),

-- Step 4: Count active customers returning in each cohort index month.
cohort_activity_summary AS (
    SELECT 
        ca.cohort_month,
        ca.cohort_index,
        COUNT(DISTINCT ca.customer_id) AS active_customers
    FROM customer_activities ca
    GROUP BY ca.cohort_month, ca.cohort_index
)

-- Step 5: Final Result - Cohort Retention Table with Raw Counts and Retention Percentages.
SELECT 
    cas.cohort_month,
    cs.cohort_size AS initial_customers,
    cas.cohort_index AS month_offset,
    cas.active_customers,
    ROUND(cas.active_customers * 100.0 / cs.cohort_size, 2) AS retention_rate_pct
FROM cohort_activity_summary cas
INNER JOIN cohort_sizes cs ON cas.cohort_month = cs.cohort_month
ORDER BY cas.cohort_month, cas.cohort_index;


-- ====================================================================
-- BONUS: PIVOTED VIEW OF RETENTION RATES (Month 0 to Month 6)
-- Ideal for immediate copy-paste into Excel or BI dashboards
-- ====================================================================
WITH customer_first_purchase AS (
    SELECT 
        customer_id,
        strftime('%Y-%m', MIN(order_date_only)) AS cohort_month
    FROM orders
    WHERE order_status = 'Completed'
    GROUP BY customer_id
),
customer_monthly_orders AS (
    SELECT 
        o.customer_id,
        cfp.cohort_month,
        (cast(strftime('%Y', o.order_date_only) as integer) - cast(substr(cfp.cohort_month, 1, 4) as integer)) * 12 +
        (cast(strftime('%m', o.order_date_only) as integer) - cast(substr(cfp.cohort_month, 6, 2) as integer)) AS cohort_index
    FROM orders o
    INNER JOIN customer_first_purchase cfp ON o.customer_id = cfp.customer_id
    WHERE o.order_status = 'Completed'
    GROUP BY o.customer_id, cfp.cohort_month, cohort_index
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(DISTINCT customer_id) AS cohort_size
    FROM customer_first_purchase
    GROUP BY cohort_month
)
SELECT 
    c.cohort_month,
    cs.cohort_size,
    ROUND(COUNT(DISTINCT CASE WHEN c.cohort_index = 0 THEN c.customer_id END) * 100.0 / cs.cohort_size, 1) AS m0_retention_pct,
    ROUND(COUNT(DISTINCT CASE WHEN c.cohort_index = 1 THEN c.customer_id END) * 100.0 / cs.cohort_size, 1) AS m1_retention_pct,
    ROUND(COUNT(DISTINCT CASE WHEN c.cohort_index = 2 THEN c.customer_id END) * 100.0 / cs.cohort_size, 1) AS m2_retention_pct,
    ROUND(COUNT(DISTINCT CASE WHEN c.cohort_index = 3 THEN c.customer_id END) * 100.0 / cs.cohort_size, 1) AS m3_retention_pct,
    ROUND(COUNT(DISTINCT CASE WHEN c.cohort_index = 4 THEN c.customer_id END) * 100.0 / cs.cohort_size, 1) AS m4_retention_pct,
    ROUND(COUNT(DISTINCT CASE WHEN c.cohort_index = 5 THEN c.customer_id END) * 100.0 / cs.cohort_size, 1) AS m5_retention_pct,
    ROUND(COUNT(DISTINCT CASE WHEN c.cohort_index = 6 THEN c.customer_id END) * 100.0 / cs.cohort_size, 1) AS m6_retention_pct
FROM customer_monthly_orders c
INNER JOIN cohort_sizes cs ON c.cohort_month = cs.cohort_month
GROUP BY c.cohort_month, cs.cohort_size
ORDER BY c.cohort_month;
