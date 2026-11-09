"""Guardrails: every query the model writes is checked before it runs.

1. It must parse as DuckDB SQL.
2. It must be exactly one read-only statement (SELECT, optionally with CTEs).
3. It may only read the tables in the semantic layer.
4. Results are capped with a LIMIT so a bad query cannot flood the app.

The database is also opened read-only, so even a query that slipped past
these checks could not change data.
"""
import sqlglot
from sqlglot import exp

from .semantic import ALLOWED_TABLES

MAX_ROWS = 1000

_FORBIDDEN = (
    exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter,
    exp.Command, exp.Merge, exp.Copy, exp.Pragma, exp.Set, exp.Use,
)


class UnsafeQuery(ValueError):
    """Raised when a generated query fails a guardrail."""


def check(sql: str) -> str:
    """Validate `sql` and return a safe, row-capped version of it."""
    sql = sql.strip().rstrip(";").strip()
    if not sql:
        raise UnsafeQuery("Empty query.")
    try:
        statements = sqlglot.parse(sql, read="duckdb")
    except sqlglot.errors.ParseError as e:
        raise UnsafeQuery(f"Could not parse SQL: {e}") from e
    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        raise UnsafeQuery("Exactly one statement is allowed.")
    tree = statements[0]
    if not isinstance(tree, (exp.Select, exp.Union, exp.Except, exp.Intersect)):
        raise UnsafeQuery(f"Only SELECT queries are allowed, got {tree.key.upper()}.")
    for node in tree.walk():
        if isinstance(node, _FORBIDDEN):
            raise UnsafeQuery(f"Forbidden operation: {node.key.upper()}.")

    cte_names = {c.alias_or_name.lower() for c in tree.find_all(exp.CTE)}
    for table in tree.find_all(exp.Table):
        name = table.name.lower()
        if not name:  # table functions such as range() or read_csv()
            raise UnsafeQuery("Table functions are not allowed.")
        if name in cte_names:
            continue
        if table.args.get("db") or table.args.get("catalog"):
            raise UnsafeQuery(f"Qualified table names are not allowed: {table.sql()}.")
        if name not in ALLOWED_TABLES:
            raise UnsafeQuery(f"Unknown table '{table.name}'. Allowed: {', '.join(sorted(ALLOWED_TABLES))}.")
    for fn in tree.find_all(exp.Anonymous):
        if fn.name.lower() in {"read_csv", "read_csv_auto", "read_parquet", "read_json", "read_text", "glob"}:
            raise UnsafeQuery(f"File access is not allowed: {fn.name}.")

    limit = tree.args.get("limit")
    if isinstance(tree, exp.Select) and limit is None:
        return tree.limit(MAX_ROWS).sql(dialect="duckdb")
    if limit is not None:
        try:
            if int(limit.expression.name) <= MAX_ROWS:
                return sql
        except (AttributeError, ValueError):
            pass
    return f"SELECT * FROM (\n{sql}\n) AS q LIMIT {MAX_ROWS}"
