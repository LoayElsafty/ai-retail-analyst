import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analyst import Analyst, guard  # noqa: E402
from analyst.llm import ScriptedLLM  # noqa: E402
from eval.run_eval import results_match  # noqa: E402

DB = str(ROOT / "data" / "retail.duckdb")


def plan(sql, chart=None, assumption=""):
    return json.dumps({"sql": sql, "chart": chart or {"type": "none"}, "assumption": assumption})


# ---------- guardrails ----------

@pytest.mark.parametrize("sql", [
    "DROP TABLE fct_sales",
    "DELETE FROM fct_sales",
    "INSERT INTO fct_sales VALUES (1)",
    "UPDATE fct_sales SET net_sales = 0",
    "CREATE TABLE x AS SELECT 1",
    "SELECT 1; DROP TABLE fct_sales",
    "SELECT * FROM users",
    "SELECT * FROM read_csv_auto('/etc/passwd')",
    "SELECT * FROM main.fct_sales",
    "ATTACH 'other.db'",
    "",
])
def test_guard_blocks_unsafe(sql):
    with pytest.raises(guard.UnsafeQuery):
        guard.check(sql)


def test_guard_allows_ctes_and_adds_limit():
    sql = "WITH t AS (SELECT category FROM dim_product) SELECT * FROM t"
    out = guard.check(sql)
    assert "LIMIT 1000" in out


def test_guard_keeps_small_limit():
    sql = "SELECT category FROM dim_product ORDER BY 1 LIMIT 5"
    assert guard.check(sql) == sql


# ---------- data ----------

def test_data_reconciles_to_retail_pack():
    import duckdb
    con = duckdb.connect(DB, read_only=True)
    rows, net = con.execute("SELECT COUNT(*), ROUND(SUM(net_sales)) FROM fct_sales").fetchone()
    assert rows == 86904 and net == 3870406
    orphans = con.execute("""SELECT COUNT(*) FROM fct_sales s
        LEFT JOIN dim_product p USING (product_id) LEFT JOIN dim_customer c USING (customer_id)
        WHERE p.product_id IS NULL OR c.customer_id IS NULL""").fetchone()[0]
    assert orphans == 0


# ---------- agent loop ----------

def test_agent_answers_with_sql_and_numbers():
    llm = ScriptedLLM([plan("SELECT ROUND(SUM(net_sales), 2) AS net_sales FROM fct_sales"),
                       "Net sales were $3,870,406."])
    res = Analyst(llm, DB).ask("Total net sales?")
    assert res.ok and res.attempts == 1
    assert round(res.data.iloc[0, 0]) == 3870406
    assert res.answer.startswith("Net sales")


def test_agent_fixes_a_failing_query():
    llm = ScriptedLLM([
        plan("SELECT SUM(revenue) FROM fct_sales"),          # wrong column -> DuckDB error
        plan("SELECT SUM(net_sales) AS net_sales FROM fct_sales"),
    ])
    res = Analyst(llm, DB).ask("Total net sales?", answer=False)
    assert res.ok and res.attempts == 2
    assert "failed with" in llm.calls[1][-1]["content"]


def test_agent_rejects_unsafe_sql_then_recovers():
    llm = ScriptedLLM([plan("DELETE FROM fct_sales"), plan("SELECT COUNT(*) AS n FROM fct_sales")])
    res = Analyst(llm, DB).ask("How many rows?", answer=False)
    assert res.ok and res.attempts == 2


def test_agent_gives_up_after_three_attempts():
    llm = ScriptedLLM([plan("SELECT nope FROM fct_sales")] * 3)
    res = Analyst(llm, DB).ask("?", answer=False)
    assert not res.ok and res.attempts == 3


def test_agent_declines_when_data_missing():
    llm = ScriptedLLM([plan("", assumption="There is no marketing spend data.")])
    res = Analyst(llm, DB).ask("What was marketing ROI?")
    assert not res.ok and "marketing" in res.error


def test_agent_handles_non_json_reply():
    llm = ScriptedLLM(["Sure! The answer is 42.", plan("SELECT 42 AS answer FROM fct_sales LIMIT 1")])
    res = Analyst(llm, DB).ask("?", answer=False)
    assert res.ok and res.attempts == 2


# ---------- scorer ----------

def test_scorer_accepts_renamed_and_extra_columns():
    gold = pd.DataFrame({"category": ["A", "B"], "gp": [10.0, 5.0]})
    pred = pd.DataFrame({"cat": ["A", "B"], "profit": [10.004, 5.0], "extra": [1, 2]})
    assert results_match(gold, pred, ordered=True)


def test_scorer_rejects_wrong_numbers_and_order():
    gold = pd.DataFrame({"category": ["A", "B"], "gp": [10.0, 5.0]})
    assert not results_match(gold, pd.DataFrame({"c": ["A", "B"], "g": [12.0, 5.0]}), ordered=True)
    assert not results_match(gold, pd.DataFrame({"c": ["B", "A"], "g": [5.0, 10.0]}), ordered=True)
    assert not results_match(gold, pd.DataFrame({"c": ["A"], "g": [10.0]}), ordered=False)
