-- ====================================================================
-- PROJECT: E-Commerce Business Intelligence & Customer Analytics
-- SCRIPT: 05_market_basket_analysis.sql
-- DESCRIPTION: Market Basket Analysis & Product Affinity Pairs
-- Demonstrates: Self-Joins, Co-Occurrence Aggregations, Support &
-- Association Metrics for Cross-Selling and Bundling Recommendations.
-- ====================================================================

-- Step 1: Self-join order_items to identify product pairs in the same order.
-- Condition: a.product_id < b.product_id avoids duplicate bidirectional counting (A-B and B-A).
WITH completed_orders AS (
    SELECT order_id
    FROM orders
    WHERE order_status = 'Completed'
),
product_pairs AS (
    SELECT 
        a.order_id,
        a.product_id AS product_a_id,
        pa.product_name AS product_a_name,
        pa.category AS category_a,
        b.product_id AS product_b_id,
        pb.product_name AS product_b_name,
        pb.category AS category_b
    FROM order_items a
    INNER JOIN order_items b 
        ON a.order_id = b.order_id 
        AND a.product_id < b.product_id
    INNER JOIN completed_orders co 
        ON a.order_id = co.order_id
    INNER JOIN products pa 
        ON a.product_id = pa.product_id
    INNER JOIN products pb 
        ON b.product_id = pb.product_id
),

-- Step 2: Calculate individual product purchase frequency across all orders.
product_frequencies AS (
    SELECT 
        oi.product_id,
        COUNT(DISTINCT oi.order_id) AS single_order_count
    FROM order_items oi
    INNER JOIN completed_orders co ON oi.order_id = co.order_id
    GROUP BY oi.product_id
),

-- Step 3: Count distinct total completed orders in system for support calculation.
total_orders_benchmark AS (
    SELECT COUNT(DISTINCT order_id) AS total_orders
    FROM completed_orders
)

-- Step 4: Aggregate pair frequency and compute Association Metrics (Support and Co-Purchase Rate).
SELECT 
    pp.product_a_id,
    pp.product_a_name,
    pp.category_a,
    pp.product_b_id,
    pp.product_b_name,
    pp.category_b,
    COUNT(DISTINCT pp.order_id) AS times_bought_together,
    pfa.single_order_count AS orders_with_product_a,
    pfb.single_order_count AS orders_with_product_b,
    ROUND(COUNT(DISTINCT pp.order_id) * 100.0 / tob.total_orders, 2) AS basket_support_pct,
    -- Confidence (A -> B): % of times Product A buyer also bought Product B
    ROUND(COUNT(DISTINCT pp.order_id) * 100.0 / pfa.single_order_count, 1) AS confidence_a_to_b_pct,
    -- Confidence (B -> A): % of times Product B buyer also bought Product A
    ROUND(COUNT(DISTINCT pp.order_id) * 100.0 / pfb.single_order_count, 1) AS confidence_b_to_a_pct
FROM product_pairs pp
INNER JOIN product_frequencies pfa ON pp.product_a_id = pfa.product_id
INNER JOIN product_frequencies pfb ON pp.product_b_id = pfb.product_id
CROSS JOIN total_orders_benchmark tob
GROUP BY 
    pp.product_a_id, pp.product_a_name, pp.category_a,
    pp.product_b_id, pp.product_b_name, pp.category_b,
    pfa.single_order_count, pfb.single_order_count, tob.total_orders
HAVING COUNT(DISTINCT pp.order_id) >= 10
ORDER BY times_bought_together DESC
LIMIT 20;
