"""The semantic layer: what the tables mean and how every KPI is defined.

The model never guesses a business rule. Net sales, margin and return rate are
defined once here, exactly as in the retail performance pack, and sent with
every question. This is what keeps the agent's numbers consistent with the
dashboard.
"""

TABLES = {
    "fct_sales": {
        "grain": "one row per item sold (order line), 2023-01-01 to 2025-12-31",
        "columns": {
            "order_item_id": "primary key",
            "order_id": "order the item belongs to (an order can have several items)",
            "customer_id": "joins to dim_customer.customer_id",
            "product_id": "joins to dim_product.product_id",
            "order_date": "DATE the item was ordered",
            "status": "one of 'Complete', 'Shipped', 'Processing', 'Returned', 'Cancelled'",
            "gross_sales": "sale price in USD; 0 when status = 'Cancelled'",
            "net_sales": "sale price in USD; 0 when status is 'Cancelled' or 'Returned'",
            "cost_of_goods": "product cost in USD; 0 when status is 'Cancelled' or 'Returned'",
            "gross_profit": "net_sales - cost_of_goods",
            "days_to_ship": "days from order to shipment (NULL if not shipped)",
            "days_to_deliver": "days from shipment to delivery (NULL if not delivered)",
        },
    },
    "dim_product": {
        "grain": "one row per product",
        "columns": {
            "product_id": "primary key",
            "department": "'Men' or 'Women'",
            "category": "e.g. 'Jeans', 'Outerwear & Coats', 'Swim', 'Intimates'",
            "brand": "product brand",
            "distribution_center": "warehouse that ships the product, e.g. 'Memphis TN'",
        },
    },
    "dim_customer": {
        "grain": "one row per customer",
        "columns": {
            "customer_id": "primary key",
            "country": "customer country, e.g. 'United States', 'China', 'Brasil' (Brazil). Spain appears as both 'Spain' and 'España': treat them as one country",
            "traffic_source": "how the customer first arrived: 'Search', 'Organic', 'Facebook', 'Email', 'Display'",
        },
    },
}

METRICS = {
    "net sales / revenue / sales": "SUM(net_sales). Excludes cancelled and returned items. Use this unless gross sales is asked for.",
    "gross sales": "SUM(gross_sales). Excludes cancelled items only.",
    "gross profit": "SUM(gross_profit)",
    "gross margin %": "SUM(gross_profit) / NULLIF(SUM(net_sales), 0) * 100",
    "orders": "COUNT(DISTINCT order_id) over items that are not cancelled",
    "items sold / units": "COUNT(*) over items whose status is not 'Cancelled' or 'Returned'",
    "average order value (AOV)": "SUM(net_sales) / COUNT(DISTINCT order_id) over items not cancelled or returned",
    "return rate %": "COUNT(*) FILTER (WHERE status = 'Returned') / COUNT(*) FILTER (WHERE status <> 'Cancelled') * 100",
    "cancellation rate %": "COUNT(*) FILTER (WHERE status = 'Cancelled') / COUNT(*) * 100",
    "customers / buyers": "COUNT(DISTINCT customer_id) over items not cancelled",
    "average days to ship": "AVG(days_to_ship)",
}

RULES = [
    "Write DuckDB SQL. Use only the three tables above.",
    "Read-only: a single SELECT (CTEs allowed). Never modify data.",
    "Years and months come from order_date, e.g. EXTRACT(YEAR FROM order_date), DATE_TRUNC('month', order_date).",
    "'Last year' means 2025, the latest full year in the data; 'this year' is not available.",
    "Round money to 2 decimals and percentages to 1 decimal.",
    "Give every column a clear snake_case alias.",
    "For rankings, ORDER BY the measure and use LIMIT.",
]


def schema_prompt() -> str:
    """Render the semantic layer as text for the model."""
    lines = ["## Tables"]
    for name, t in TABLES.items():
        lines.append(f"\n### {name} ({t['grain']})")
        for col, desc in t["columns"].items():
            lines.append(f"- {col}: {desc}")
    lines.append("\n## Metric definitions (always use these)")
    for m, d in METRICS.items():
        lines.append(f"- {m}: {d}")
    lines.append("\n## Rules")
    lines += [f"- {r}" for r in RULES]
    return "\n".join(lines)


ALLOWED_TABLES = set(TABLES)
