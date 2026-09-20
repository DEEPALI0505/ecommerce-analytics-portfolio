"""
01_statistical_analysis.py
Performs rigorous statistical hypothesis testing on e-commerce transaction data.
Focuses on actionable business questions:
1. Promotional Discount Impact: Does discounting lift basket size or just erode gross margin?
2. Acquisition Channel Quality: Does repeat purchase conversion depend on the acquisition channel?
3. Multi-Item First Basket Effect: Does cross-selling on Order 1 increase Customer Lifetime Value?
"""

import sqlite3
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "ecommerce.db"
OUTPUT_DIR = BASE_DIR / "reports"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("  E-COMMERCE ADVANCED STATISTICAL HYPOTHESIS TESTING REPORT")
print("=" * 70)

conn = sqlite3.connect(DB_PATH)

# Load data into pandas DataFrames
orders_df = pd.read_sql_query(
    """
    SELECT 
        order_id,
        customer_id,
        order_date_only,
        subtotal,
        discount_amount,
        shipping_fee,
        total_amount,
        total_cost,
        gross_profit,
        order_sequence,
        CASE WHEN discount_amount > 0 THEN 1 ELSE 0 END AS has_discount
    FROM orders
    WHERE order_status = 'Completed';
    """,
    conn
)

customers_df = pd.read_sql_query(
    """
    SELECT 
        c.customer_id,
        c.region,
        c.acquisition_channel,
        c.signup_date,
        COUNT(DISTINCT o.order_id) AS total_orders,
        ROUND(SUM(o.total_amount), 2) AS total_spend,
        CASE WHEN COUNT(DISTINCT o.order_id) > 1 THEN 1 ELSE 0 END AS is_repeat_buyer
    FROM customers c
    LEFT JOIN orders o ON c.customer_id = o.customer_id AND o.order_status = 'Completed'
    GROUP BY c.customer_id, c.region, c.acquisition_channel, c.signup_date;
    """,
    conn
)

first_orders_df = pd.read_sql_query(
    """
    WITH first_orders AS (
        SELECT order_id, customer_id
        FROM orders
        WHERE order_sequence = 1 AND order_status = 'Completed'
    ),
    first_order_item_counts AS (
        SELECT 
            fo.customer_id,
            fo.order_id,
            COUNT(oi.item_id) AS items_in_first_order
        FROM first_orders fo
        JOIN order_items oi ON fo.order_id = oi.order_id
        GROUP BY fo.customer_id, fo.order_id
    )
    SELECT 
        foc.customer_id,
        foc.items_in_first_order,
        CASE WHEN foc.items_in_first_order > 1 THEN 'Multi-Item Basket' ELSE 'Single-Item Basket' END AS first_basket_type,
        c.total_orders,
        c.total_spend AS lifetime_spend
    FROM first_order_item_counts foc
    JOIN (
        SELECT customer_id, COUNT(order_id) AS total_orders, SUM(total_amount) AS total_spend
        FROM orders
        WHERE order_status = 'Completed'
        GROUP BY customer_id
    ) c ON foc.customer_id = c.customer_id;
    """,
    conn
)

conn.close()

results_summary = []

# ====================================================================
# HYPOTHESIS 1: Discount Impact on Order Value & Profitability
# H0: Mean total order amount is identical between discounted and non-discounted orders.
# H1: Mean total order amount is significantly different.
# ====================================================================
print("\n[HYPOTHESIS 1] Promotional Discount Impact on Basket Size & Gross Margin")
print("-" * 70)

disc_group = orders_df[orders_df["has_discount"] == 1]
no_disc_group = orders_df[orders_df["has_discount"] == 0]

t_stat, p_val_ttest = stats.ttest_ind(disc_group["total_amount"], no_disc_group["total_amount"], equal_var=False)
u_stat, p_val_mwu = stats.mannwhitneyu(disc_group["total_amount"], no_disc_group["total_amount"])

disc_aov = disc_group["total_amount"].mean()
no_disc_aov = no_disc_group["total_amount"].mean()
aov_lift_pct = ((disc_aov - no_disc_aov) / no_disc_aov) * 100

disc_margin_pct = (disc_group["gross_profit"].sum() / disc_group["total_amount"].sum()) * 100
no_disc_margin_pct = (no_disc_group["gross_profit"].sum() / no_disc_group["total_amount"].sum()) * 100

print(f"Sample Sizes: Discounted Orders = {len(disc_group):,}, Full-Price Orders = {len(no_disc_group):,}")
print(f"Discounted Orders AOV:    ${disc_aov:.2f} (Gross Margin: {disc_margin_pct:.1f}%)")
print(f"Full-Price Orders AOV:    ${no_disc_aov:.2f} (Gross Margin: {no_disc_margin_pct:.1f}%)")
print(f"AOV Difference / Lift:    {aov_lift_pct:+.2f}%")
print(f"Welch's t-test:           t = {t_stat:.4f}, p-value = {p_val_ttest:.4e}")
print(f"Mann-Whitney U test:      U = {u_stat:.2f}, p-value = {p_val_mwu:.4e}")

h1_status = "Statistically Significant (p < 0.05)" if p_val_ttest < 0.05 else "Not Statistically Significant (p >= 0.05)"
print(f"Conclusion: {h1_status}")

results_summary.append({
    "hypothesis": "H1: Promotional Discounts lift AOV",
    "test_type": "Welch's Two-Sample t-test",
    "statistic": round(t_stat, 4),
    "p_value": p_val_ttest,
    "verdict": h1_status,
    "business_takeaway": f"Discounted orders average ${disc_aov:.2f} vs ${no_disc_aov:.2f} (margin changes from {no_disc_margin_pct:.1f}% to {disc_margin_pct:.1f}%)."
})

# ====================================================================
# HYPOTHESIS 2: Acquisition Channel vs. Repeat Purchase Conversion
# H0: Customer repeat purchase propensity is independent of acquisition channel.
# H1: Customer repeat purchase propensity depends significantly on acquisition channel.
# ====================================================================
print("\n[HYPOTHESIS 2] Acquisition Channel Quality & Repeat Purchase Propensity")
print("-" * 70)

contingency_table = pd.crosstab(
    customers_df["acquisition_channel"],
    customers_df["is_repeat_buyer"]
)
contingency_table.columns = ["Single-Order", "Repeat-Buyer"]
contingency_table["Total"] = contingency_table.sum(axis=1)
contingency_table["Repeat_Rate_%"] = (contingency_table["Repeat-Buyer"] / contingency_table["Total"] * 100).round(2)

chi2, p_val_chi2, dof, expected = stats.chi2_contingency(
    pd.crosstab(customers_df["acquisition_channel"], customers_df["is_repeat_buyer"])
)

# Cramér's V (Effect size)
n = len(customers_df)
cramers_v = np.sqrt(chi2 / (n * (min(contingency_table.shape) - 1)))

print("Contingency Breakdown by Channel:")
print(contingency_table[["Single-Order", "Repeat-Buyer", "Total", "Repeat_Rate_%"]])
print(f"\nChi-Square Statistic:     Chi2 = {chi2:.4f}, df = {dof}, p-value = {p_val_chi2:.4e}")
print(f"Cramer's V Effect Size:   V = {cramers_v:.4f}")

h2_status = "Statistically Significant (p < 0.05)" if p_val_chi2 < 0.05 else "Not Statistically Significant (p >= 0.05)"
print(f"Conclusion: {h2_status}")

best_channel = contingency_table["Repeat_Rate_%"].idxmax()
best_rate = contingency_table["Repeat_Rate_%"].max()
worst_channel = contingency_table["Repeat_Rate_%"].idxmin()
worst_rate = contingency_table["Repeat_Rate_%"].min()

results_summary.append({
    "hypothesis": "H2: Channel affects Repeat Rate",
    "test_type": "Chi-Square Test of Independence",
    "statistic": round(chi2, 4),
    "p_value": p_val_chi2,
    "verdict": h2_status,
    "business_takeaway": f"Highest repeat rate is {best_channel} ({best_rate}%), lowest is {worst_channel} ({worst_rate}%)."
})

# ====================================================================
# HYPOTHESIS 3: Multi-Item First Basket vs. Customer Lifetime Value (LTV)
# H0: Long-term LTV is identical whether customer starts with 1 item or 2+ items.
# H1: Customers with multi-item initial baskets achieve significantly higher LTV.
# ====================================================================
print("\n[HYPOTHESIS 3] Multi-Item First Basket Effect on Long-Term Customer LTV")
print("-" * 70)

single_first = first_orders_df[first_orders_df["first_basket_type"] == "Single-Item Basket"]
multi_first = first_orders_df[first_orders_df["first_basket_type"] == "Multi-Item Basket"]

u_ltv, p_val_ltv = stats.mannwhitneyu(multi_first["lifetime_spend"], single_first["lifetime_spend"], alternative="greater")

mean_ltv_single = single_first["lifetime_spend"].mean()
mean_ltv_multi = multi_first["lifetime_spend"].mean()
ltv_lift_pct = ((mean_ltv_multi - mean_ltv_single) / mean_ltv_single) * 100

print(f"Single-Item First Basket: Sample = {len(single_first):,}, Average LTV = ${mean_ltv_single:.2f}")
print(f"Multi-Item First Basket:  Sample = {len(multi_first):,}, Average LTV = ${mean_ltv_multi:.2f}")
print(f"Lifetime Spend Lift:      {ltv_lift_pct:+.2f}%")
print(f"Mann-Whitney U Test:      U = {u_ltv:.2f}, p-value = {p_val_ltv:.4e}")

h3_status = "Statistically Significant (p < 0.05)" if p_val_ltv < 0.05 else "Not Statistically Significant (p >= 0.05)"
print(f"Conclusion: {h3_status}")

results_summary.append({
    "hypothesis": "H3: Multi-Item First Order boosts LTV",
    "test_type": "Mann-Whitney U Test (One-Tailed)",
    "statistic": round(u_ltv, 2),
    "p_value": p_val_ltv,
    "verdict": h3_status,
    "business_takeaway": f"Customers starting with 2+ items generate ${mean_ltv_multi:.2f} LTV vs ${mean_ltv_single:.2f} ({ltv_lift_pct:+.1f}% lift)."
})

print("\n" + "=" * 70)
print("  STATISTICAL TESTING COMPLETE - SUMMARY EXPORTED")
print("=" * 70)

# Export results table
summary_df = pd.DataFrame(results_summary)
summary_df.to_csv(OUTPUT_DIR / "statistical_test_results.csv", index=False)
print(f"[SUCCESS] Statistical test results saved to: {OUTPUT_DIR / 'statistical_test_results.csv'}")
