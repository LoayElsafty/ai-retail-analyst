"""Build the analyst's DuckDB database from the frozen BigQuery export.

The export is the retail pack's governed fact table (TheLook e-commerce,
2023-01-01 to 2025-12-31, 86,904 order items). Here it is split into a small
star schema so the agent has to join, filter and aggregate like an analyst would.

Usage: python build_db.py data/raw/*.csv
"""
import sys
import duckdb

DB = "data/retail.duckdb"


def build(csv_files, db=DB):
    con = duckdb.connect(db)
    con.execute(f"CREATE OR REPLACE TEMP TABLE raw AS SELECT * FROM read_csv_auto({list(csv_files)!r}, header=true)")
    con.execute("""
        CREATE OR REPLACE TABLE dim_product AS
        SELECT DISTINCT product_id, department, category, brand, distribution_center
        FROM raw ORDER BY product_id""")
    con.execute("""
        CREATE OR REPLACE TABLE dim_customer AS
        SELECT DISTINCT user_id AS customer_id, country, traffic_source
        FROM raw ORDER BY customer_id""")
    con.execute("""
        CREATE OR REPLACE TABLE fct_sales AS
        SELECT order_item_id, order_id, user_id AS customer_id, product_id,
               order_date, status,
               gross_sales, net_sales, cost_of_goods, gross_profit,
               days_to_ship, days_to_deliver
        FROM raw ORDER BY order_item_id""")
    # Reconciliation: the star schema must give back the governed totals.
    rows, net = con.execute("SELECT COUNT(*), ROUND(SUM(net_sales), 0) FROM fct_sales").fetchone()
    assert rows == 86904, rows
    assert net == 3870406, net
    con.close()
    print(f"Built {db}: {rows:,} order items, net sales ${net:,.0f} (reconciles to the retail pack)")


if __name__ == "__main__":
    build(sys.argv[1:])
