#  AuraCommerce: End-to-End E-Commerce Business Intelligence & Customer Analytics

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![SQL](https://img.shields.io/badge/SQL-Advanced_Window_Functions-orange.svg?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![PowerBI](https://img.shields.io/badge/Power_BI-DAX_Measures-yellow.svg)](https://powerbi.microsoft.com/)
[![Tableau](https://img.shields.io/badge/Tableau-LOD_Expressions-E97627.svg?logo=tableau&logoColor=white)](https://www.tableau.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Portfolio Project for Senior / Mid-Level Data Analyst Roles**  
> An end-to-end commercial analytics engagement investigating customer retention, discount price elasticity, RFM lifecycle segmentation, and cross-sell affinities across 24 months of e-commerce transactions (\$1.23M GMV, 4,000 customers).

---

## Executive Summary & Key Results

| Core Business Question | Diagnostic Finding | Statistical Validation | Recommended Business Action | Projected ROI |
| :--- | :--- | :--- | :--- | :--- |
| **Do promotional discounts increase basket size?** | Discounted orders average \$139.86 vs. \$143.68 for full-price, while **eroding margins by 5.2%**. | Welch's $t$-test ($p = 0.223$, not significant) | Sunset blanket % codes; switch to **\$175 minimum cart thresholds**. | **+\$25,500** profit saved |
| **Where does customer churn happen?** | **55.75% of churn** happens between Order 1 and Order 2; repeat purchase survival climbs to 71% after Order 2. | Cohort retention matrix & inter-purchase interval analysis | Automated **Day-35 re-engagement flow** (median repurchase is 46.5 days). | **+\$53,400** 2-yr LTV lift |
| **Does multi-item first basket boost LTV?** | First-time buyers purchasing 2+ items achieve **\$371.31 LTV vs. \$265.36** (+39.9% lift). | Mann-Whitney U test ($p = 3.12 \times 10^{-66}$) | Deploy **1-Click Checkout Bundles** on top affinity SKU pairs. | **+\$29,510** incremental LTV |
| **How concentrated is revenue?** | **Champions (18.2% of base)** generate **43.99% (\$540K)** of revenue; 754 customers are At Risk (\$278K pool). | SQL `NTILE(5)` RFM quintile scoring | High-touch **VIP reactivation credit** for high-value dormant buyers. | **+\$34,600** immediate recovery |

---

##  Architecture & Project Structure

```
ecommerce_analytics_portfolio/
├── data/
│   ├── raw/                             # Normalized entity CSVs (customers, products, orders, order_items)
│   ├── processed/                       # Analytics master star-schema denormalized table
│   └── ecommerce.db                     # High-performance indexed SQLite database
├── sql/
│   ├── 01_schema_setup.sql              # DDL, foreign keys, indexes & reporting views
│   ├── 02_cohort_retention_analysis.sql # Monthly cohort retention triangle (CTEs, date math)
│   ├── 03_rfm_customer_segmentation.sql # NTILE(5) scoring, customer lifecycle segmentation
│   ├── 04_customer_lifetime_value.sql   # LAG() inter-purchase intervals, cumulative spend
│   └── 05_market_basket_analysis.sql    # Self-join co-purchase pairs, support & confidence
├── analysis/
│   └── 01_statistical_analysis.py       # Formal hypothesis testing (t-tests, Chi-Square, Mann-Whitney U)
├── dashboard/
│   ├── index.html                       # Standalone interactive executive BI dashboard (Tailwind + Chart.js)
│   ├── data.json                        # Pre-aggregated dashboard payload for high-speed rendering
│   ├── serve_dashboard.py               # Zero-dependency local web server launcher
│   └── powerbi_tableau_blueprint.md     # Ready-to-copy DAX formulas & Tableau LOD calculated fields
├── reports/
│   ├── executive_insights_report.md     # C-Suite briefing memo with 30-60-90 day roadmap
│   └── statistical_test_results.csv     # Exported statistical hypothesis test results
├── scripts/
│   ├── generate_data.py                 # Multi-year synthetic data generator
│   ├── test_sql_queries.py              # Automated SQL verification script
│   └── export_dashboard_data.py         # Database-to-JSON aggregator
├── requirements.txt                     # Project dependencies
└── README.md                            # Documentation
```

---

##  Highlighted SQL Queries

### 1. Monthly Cohort Retention Heatmap Query
```sql
WITH customer_first_purchase AS (
    SELECT 
        customer_id,
        strftime('%Y-%m', MIN(order_date_only)) AS cohort_month
    FROM orders
    WHERE order_status = 'Completed'
    GROUP BY customer_id
),
customer_activities AS (
    SELECT 
        o.customer_id,
        cfp.cohort_month,
        (cast(strftime('%Y', o.order_date_only) as integer) - cast(substr(cfp.cohort_month, 1, 4) as integer)) * 12 +
        (cast(strftime('%m', o.order_date_only) as integer) - cast(substr(cfp.cohort_month, 6, 2) as integer)) AS cohort_index
    FROM orders o
    JOIN customer_first_purchase cfp ON o.customer_id = cfp.customer_id
    WHERE o.order_status = 'Completed'
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(DISTINCT customer_id) AS cohort_size
    FROM customer_first_purchase
    GROUP BY cohort_month
)
SELECT 
    ca.cohort_month,
    cs.cohort_size,
    ca.cohort_index,
    COUNT(DISTINCT ca.customer_id) AS active_customers,
    ROUND(COUNT(DISTINCT ca.customer_id) * 100.0 / cs.cohort_size, 2) AS retention_rate_pct
FROM customer_activities ca
JOIN cohort_sizes cs ON ca.cohort_month = cs.cohort_month
GROUP BY ca.cohort_month, cs.cohort_size, ca.cohort_index
ORDER BY ca.cohort_month, ca.cohort_index;
```

### 2. RFM Customer Segmentation with `NTILE(5)`
```sql
WITH customer_rfm_raw AS (
    SELECT 
        c.customer_id,
        julianday((SELECT MAX(order_date_only) FROM orders WHERE order_status = 'Completed')) - 
        julianday(MAX(o.order_date_only)) AS recency_days,
        COUNT(DISTINCT o.order_id) AS frequency_orders,
        ROUND(SUM(o.total_amount), 2) AS monetary_spend
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.order_status = 'Completed'
    GROUP BY c.customer_id
),
rfm_scores AS (
    SELECT 
        customer_id,
        recency_days, frequency_orders, monetary_spend,
        NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
        NTILE(5) OVER (ORDER BY frequency_orders ASC) AS f_score,
        NTILE(5) OVER (ORDER BY monetary_spend ASC) AS m_score
    FROM customer_rfm_raw
)
SELECT 
    CASE 
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customers'
        WHEN r_score >= 4 AND f_score <= 2 THEN 'Promising New'
        WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk Customers'
        ELSE 'Lost / Hibernating'
    END AS segment,
    COUNT(customer_id) AS total_customers,
    ROUND(SUM(monetary_spend), 2) AS total_revenue,
    ROUND(AVG(monetary_spend), 2) AS avg_spend
FROM rfm_scores
GROUP BY 1
ORDER BY total_revenue DESC;
```

---

##  Statistical Hypothesis Testing

All hypotheses were formally evaluated in Python using `scipy.stats`:

1. **Promotional Discount Elasticity:**
   * **Test:** Welch's Two-Sample $t$-test & Mann-Whitney U test.
   * **Result:** $t = -1.218, p = 0.223$. Fail to reject $H_0$. Discounts do not lift order volume, but reduce gross margin from 61.2% to 56.0%.
2. **Channel Quality & Repeat Purchase Independence:**
   * **Test:** Chi-Square Test of Independence ($\chi^2 = 2.5134, df = 4, p = 0.642, V = 0.0145$).
   * **Result:** Repeat purchase rates across Paid Search (40.8%), Organic (43.3%), Social (40.3%), and Email (41.6%) are consistent.
3. **Multi-Item First Basket Effect on 2-Year LTV:**
   * **Test:** One-tailed Mann-Whitney U test.
   * **Result:** $U = 2,276,517.5, p = 3.12 \times 10^{-66}$ (Statistically Significant). Multi-item buyers average **\$371.31** lifetime spend vs. **\$265.36** for single-item buyers (+39.9% lift).

---

##  Quickstart & Reproduction Guide

### 1. Clone & Set Up Environment
```bash
git clone https://github.com/yourusername/ecommerce-analytics-portfolio.git
cd ecommerce-analytics-portfolio

# Optional virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### 2. Run Data Pipeline & SQL Verification
```bash
# 1. Regenerate raw dataset and indexed SQLite database
python scripts/generate_data.py

# 2. Execute and verify all analytical SQL queries
python scripts/test_sql_queries.py

# 3. Run formal statistical hypothesis tests
python analysis/01_statistical_analysis.py
```

### 3. Launch Interactive BI Dashboard
```bash
python dashboard/serve_dashboard.py
```
*Your default web browser will automatically open to `http://localhost:8080` with the live interactive dashboard!*

---

##  Power BI & Tableau Integration
* See the [Power BI & Tableau Blueprint](dashboard/powerbi_tableau_blueprint.md) for full DAX formulas, Star Schema setup, and Tableau Level of Detail (LOD) calculations.
* Import `data/processed/ecommerce_analytics_master.csv` directly into Power BI or Tableau to recreate all visualizations in under 10 minutes.

---

##  License
This project is open-source under the [MIT License](LICENSE).
