"""
export_dashboard_data.py
Extracts pre-computed aggregations from SQLite database into clean JSON
for high-speed, instant interactive rendering in the web dashboard.
"""

import json
import sqlite3
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "ecommerce.db"
OUTPUT_JSON = BASE_DIR / "dashboard" / "data.json"

conn = sqlite3.connect(DB_PATH)

# 1. Overall Executive KPIs
kpis_df = pd.read_sql_query(
    """
    SELECT 
        ROUND(SUM(total_amount), 2) AS total_gmv,
        COUNT(DISTINCT order_id) AS total_orders,
        COUNT(DISTINCT customer_id) AS total_customers,
        ROUND(AVG(total_amount), 2) AS avg_order_value,
        ROUND(SUM(gross_profit), 2) AS total_gross_profit,
        ROUND(SUM(gross_profit) * 100.0 / SUM(total_amount), 1) AS gross_margin_pct
    FROM orders
    WHERE order_status = 'Completed';
    """,
    conn
)

# 2. Repeat Customer Rate
repeat_df = pd.read_sql_query(
    """
    WITH order_counts AS (
        SELECT customer_id, COUNT(order_id) AS cnt
        FROM orders
        WHERE order_status = 'Completed'
        GROUP BY customer_id
    )
    SELECT 
        COUNT(CASE WHEN cnt > 1 THEN 1 END) AS repeat_customers,
        COUNT(*) AS total_customers,
        ROUND(COUNT(CASE WHEN cnt > 1 THEN 1 END) * 100.0 / COUNT(*), 1) AS repeat_rate_pct
    FROM order_counts;
    """,
    conn
)

# 3. Monthly Trend (Revenue, Profit, Orders)
monthly_df = pd.read_sql_query(
    """
    SELECT 
        strftime('%Y-%m', order_date_only) AS month,
        ROUND(SUM(total_amount), 2) AS revenue,
        ROUND(SUM(gross_profit), 2) AS profit,
        COUNT(DISTINCT order_id) AS orders,
        COUNT(DISTINCT customer_id) AS active_customers,
        ROUND(AVG(total_amount), 2) AS aov
    FROM orders
    WHERE order_status = 'Completed'
    GROUP BY strftime('%Y-%m', order_date_only)
    ORDER BY month;
    """,
    conn
)

# 4. Category Performance
category_df = pd.read_sql_query(
    """
    SELECT 
        p.category,
        ROUND(SUM(oi.line_subtotal), 2) AS total_sales,
        ROUND(SUM(oi.line_subtotal - oi.line_cost), 2) AS category_profit,
        SUM(oi.quantity) AS units_sold,
        COUNT(DISTINCT oi.order_id) AS order_appearances
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    JOIN orders o ON oi.order_id = o.order_id
    WHERE o.order_status = 'Completed'
    GROUP BY p.category
    ORDER BY total_sales DESC;
    """,
    conn
)

# 5. Cohort Retention Matrix
cohort_matrix_df = pd.read_sql_query(
    """
    WITH first_purchase AS (
        SELECT 
            customer_id,
            strftime('%Y-%m', MIN(order_date_only)) AS cohort_month
        FROM orders
        WHERE order_status = 'Completed'
        GROUP BY customer_id
    ),
    activities AS (
        SELECT 
            o.customer_id,
            fp.cohort_month,
            (cast(strftime('%Y', o.order_date_only) as integer) - cast(substr(fp.cohort_month, 1, 4) as integer)) * 12 +
            (cast(strftime('%m', o.order_date_only) as integer) - cast(substr(fp.cohort_month, 6, 2) as integer)) AS cohort_index
        FROM orders o
        JOIN first_purchase fp ON o.customer_id = fp.customer_id
        WHERE o.order_status = 'Completed'
    ),
    cohort_sizes AS (
        SELECT cohort_month, COUNT(DISTINCT customer_id) AS cohort_size
        FROM first_purchase
        GROUP BY cohort_month
    )
    SELECT 
        a.cohort_month,
        cs.cohort_size,
        a.cohort_index,
        COUNT(DISTINCT a.customer_id) AS active_users,
        ROUND(COUNT(DISTINCT a.customer_id) * 100.0 / cs.cohort_size, 1) AS retention_pct
    FROM activities a
    JOIN cohort_sizes cs ON a.cohort_month = cs.cohort_month
    WHERE a.cohort_index <= 12
    GROUP BY a.cohort_month, cs.cohort_size, a.cohort_index
    ORDER BY a.cohort_month, a.cohort_index;
    """,
    conn
)

# 6. RFM Segmentation Summary
rfm_df = pd.read_sql_query(
    """
    WITH customer_rfm_raw AS (
        SELECT 
            c.customer_id,
            c.region,
            c.acquisition_channel,
            julianday((SELECT MAX(order_date_only) FROM orders WHERE order_status = 'Completed')) - 
            julianday(MAX(o.order_date_only)) AS recency_days,
            COUNT(DISTINCT o.order_id) AS frequency_orders,
            ROUND(SUM(o.total_amount), 2) AS monetary_spend
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        WHERE o.order_status = 'Completed'
        GROUP BY c.customer_id, c.region, c.acquisition_channel
    ),
    rfm_scores AS (
        SELECT 
            customer_id,
            region,
            acquisition_channel,
            recency_days,
            frequency_orders,
            monetary_spend,
            NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
            NTILE(5) OVER (ORDER BY frequency_orders ASC) AS f_score,
            NTILE(5) OVER (ORDER BY monetary_spend ASC) AS m_score
        FROM customer_rfm_raw
    ),
    customer_segments AS (
        SELECT 
            customer_id,
            region,
            acquisition_channel,
            ROUND(recency_days, 0) AS recency,
            frequency_orders AS frequency,
            monetary_spend AS monetary,
            r_score, f_score, m_score,
            CASE 
                WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
                WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customers'
                WHEN r_score >= 4 AND f_score <= 2 THEN 'Promising New'
                WHEN r_score >= 3 AND f_score <= 3 AND m_score >= 3 THEN 'Potential Loyalists'
                WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk Customers'
                WHEN r_score <= 2 AND f_score <= 2 AND m_score >= 3 THEN 'High-Value Dormant'
                ELSE 'Lost / Hibernating'
            END AS segment
        FROM rfm_scores
    )
    SELECT 
        segment,
        COUNT(customer_id) AS customer_count,
        ROUND(SUM(monetary), 2) AS total_revenue,
        ROUND(AVG(monetary), 2) AS avg_spend,
        ROUND(AVG(frequency), 1) AS avg_orders,
        ROUND(AVG(recency), 0) AS avg_recency_days
    FROM customer_segments
    GROUP BY segment
    ORDER BY total_revenue DESC;
    """,
    conn
)

# 7. Top Market Basket Affinity Pairs
basket_df = pd.read_sql_query(
    """
    WITH completed_orders AS (
        SELECT order_id FROM orders WHERE order_status = 'Completed'
    ),
    product_pairs AS (
        SELECT 
            a.product_id AS p1_id,
            pa.product_name AS p1_name,
            pa.category AS p1_cat,
            b.product_id AS p2_id,
            pb.product_name AS p2_name,
            pb.category AS p2_cat,
            COUNT(DISTINCT a.order_id) AS co_orders
        FROM order_items a
        JOIN order_items b ON a.order_id = b.order_id AND a.product_id < b.product_id
        JOIN completed_orders co ON a.order_id = co.order_id
        JOIN products pa ON a.product_id = pa.product_id
        JOIN products pb ON b.product_id = pb.product_id
        GROUP BY a.product_id, pa.product_name, pa.category, b.product_id, pb.product_name, pb.category
    )
    SELECT 
        p1_name,
        p1_cat,
        p2_name,
        p2_cat,
        co_orders,
        ROUND(co_orders * 100.0 / (SELECT COUNT(*) FROM completed_orders), 2) AS support_pct
    FROM product_pairs
    ORDER BY co_orders DESC
    LIMIT 10;
    """,
    conn
)

# 8. Channel Distribution
channel_df = pd.read_sql_query(
    """
    SELECT 
        c.acquisition_channel,
        COUNT(DISTINCT c.customer_id) AS customers,
        COUNT(DISTINCT o.order_id) AS orders,
        ROUND(SUM(o.total_amount), 2) AS revenue,
        ROUND(AVG(o.total_amount), 2) AS aov
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.order_status = 'Completed'
    GROUP BY c.acquisition_channel
    ORDER BY revenue DESC;
    """,
    conn
)

conn.close()

data_payload = {
    "kpis": kpis_df.to_dict(orient="records")[0],
    "repeat_rate": repeat_df.to_dict(orient="records")[0],
    "monthly_trend": monthly_df.to_dict(orient="records"),
    "category_performance": category_df.to_dict(orient="records"),
    "cohort_matrix": cohort_matrix_df.to_dict(orient="records"),
    "rfm_segments": rfm_df.to_dict(orient="records"),
    "market_basket": basket_df.to_dict(orient="records"),
    "channels": channel_df.to_dict(orient="records")
}

OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(data_payload, f, indent=2)

print(f"[SUCCESS] Exported rich dashboard data payload to: {OUTPUT_JSON}")
