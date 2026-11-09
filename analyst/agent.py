"""The analyst loop: question -> SQL -> checked -> run -> (fix if it fails) -> answer.

1. The model gets the semantic layer and the question, and returns JSON:
   the SQL, a suggested chart and a one-line note on any assumption.
2. The guardrails check the SQL; the query runs on a read-only database.
3. If the query is rejected or errors, the error goes back to the model,
   which gets up to two more attempts.
4. The model writes a short answer using only the numbers in the result.
   Every answer is returned with the SQL behind it, so it can be audited.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

import duckdb
import pandas as pd

from . import guard
from .llm import LLM
from .semantic import schema_prompt

DB_PATH = "data/retail.duckdb"
MAX_ATTEMPTS = 3

SQL_SYSTEM = f"""You are a careful retail data analyst. Turn the user's business question into one DuckDB SQL query over the tables below.

{schema_prompt()}

Reply with JSON only, no prose and no code fences:
{{"sql": "<one SELECT query>", "chart": {{"type": "bar|line|none", "x": "<column>", "y": "<column>"}}, "assumption": "<one short sentence on any interpretation you made, or empty>"}}
If the question cannot be answered from these tables, reply {{"sql": "", "chart": {{"type": "none"}}, "assumption": "<why not>"}}."""

ANSWER_SYSTEM = """You are a retail analyst writing for a busy manager.
Answer the question in 1-3 short sentences using ONLY the numbers in the query result provided.
Lead with the answer. Format money as $1,234 and percentages with one decimal. Do not invent numbers, causes or recommendations that the result does not show."""


@dataclass
class Result:
    question: str
    sql: str = ""
    data: pd.DataFrame | None = None
    answer: str = ""
    chart: dict = field(default_factory=lambda: {"type": "none"})
    assumption: str = ""
    attempts: int = 0
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.data is not None and not self.error


def _parse_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("The model did not return JSON.")
    return json.loads(m.group(0))


class Analyst:
    def __init__(self, llm: LLM, db_path: str = DB_PATH):
        self.llm = llm
        self.db_path = db_path

    def _run(self, sql: str) -> pd.DataFrame:
        con = duckdb.connect(self.db_path, read_only=True)
        try:
            return con.execute(sql).df()
        finally:
            con.close()

    def ask(self, question: str, answer: bool = True) -> Result:
        res = Result(question=question)
        messages = [{"role": "user", "content": question}]
        for attempt in range(1, MAX_ATTEMPTS + 1):
            res.attempts = attempt
            reply = self.llm.complete(SQL_SYSTEM, messages)
            messages.append({"role": "assistant", "content": reply})
            try:
                plan = _parse_json(reply)
                res.sql = (plan.get("sql") or "").strip()
                res.chart = plan.get("chart") or {"type": "none"}
                res.assumption = plan.get("assumption") or ""
                if not res.sql:
                    res.error = res.assumption or "The question can't be answered from this data."
                    return res
                safe_sql = guard.check(res.sql)
                res.data = self._run(safe_sql)
                res.error = ""
                break
            except (ValueError, guard.UnsafeQuery, duckdb.Error) as e:
                res.data, res.error = None, f"{type(e).__name__}: {e}"
                messages.append({
                    "role": "user",
                    "content": f"That failed with: {res.error}\nFix it and reply with the same JSON format.",
                })
        if res.ok and answer:
            res.answer = self._summarise(question, res)
        return res

    def _summarise(self, question: str, res: Result) -> str:
        table = res.data.head(25).to_csv(index=False)
        prompt = f"Question: {question}\n\nSQL used:\n{res.sql}\n\nQuery result ({len(res.data)} rows, first 25 shown):\n{table}"
        if res.assumption:
            prompt += f"\nAssumption made: {res.assumption}"
        return self.llm.complete(ANSWER_SYSTEM, [{"role": "user", "content": prompt}]).strip()


def chart(res: Result):
    """Return a matplotlib figure for the suggested chart, or None."""
    c = res.chart or {}
    df = res.data
    if df is None or c.get("type") not in ("bar", "line") or len(df) < 2:
        return None
    x, y = c.get("x"), c.get("y")
    if x not in df.columns or y not in df.columns:
        return None
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 3.6))
    d = df.head(30)
    if c["type"] == "line":
        ax.plot(d[x].astype(str), d[y], color="#1f4fd8", linewidth=2)
    else:
        ax.bar(d[x].astype(str), d[y], color="#1f4fd8")
    ax.set_xlabel(x.replace("_", " "))
    ax.set_ylabel(y.replace("_", " "))
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="x", labelrotation=45 if len(d) > 6 else 0, labelsize=8)
    fig.tight_layout()
    return fig
