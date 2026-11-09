"""Score the analyst on the 20 questions in eval/questions.yaml.

    python eval/run_eval.py                 # real model (needs an API key)
    python eval/run_eval.py --oracle        # feeds the golden SQL back in: checks the harness itself

Writes eval/results.md and prints the score.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import duckdb
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analyst import Analyst  # noqa: E402
from analyst.llm import ScriptedLLM, default_llm  # noqa: E402

DB = str(ROOT / "data" / "retail.duckdb")
TOL = 0.005  # 0.5% relative tolerance on numbers


def load_questions():
    return yaml.safe_load((ROOT / "eval" / "questions.yaml").read_text())


def _norm(series: pd.Series):
    out = []
    for v in series.tolist():
        if v is None or (isinstance(v, float) and math.isnan(v)):
            out.append(None)
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            out.append(float(v))
        else:
            out.append(str(v)[:10] if hasattr(v, "year") else str(v))
    return out


def _same(a, b) -> bool:
    if a is None or b is None:
        return a is b
    if isinstance(a, float) and isinstance(b, float):
        return abs(a - b) <= max(TOL * max(abs(a), abs(b)), 0.051)
    return str(a).strip().lower() == str(b).strip().lower()


def _col_match(gold: list, pred: list, ordered: bool) -> bool:
    if len(gold) != len(pred):
        return False
    if ordered:
        return all(_same(g, p) for g, p in zip(gold, pred))
    key = lambda v: (v is None, str(type(v)), v if v is not None else 0)  # noqa: E731
    return all(_same(g, p) for g, p in zip(sorted(gold, key=key), sorted(pred, key=key)))


def results_match(gold: pd.DataFrame, pred: pd.DataFrame, ordered: bool) -> bool:
    """Every golden column must appear (by its values) somewhere in the prediction."""
    if len(gold) != len(pred):
        return False
    pred_cols = [_norm(pred[c]) for c in pred.columns]
    for c in gold.columns:
        g = _norm(gold[c])
        if not any(_col_match(g, p, ordered) for p in pred_cols):
            return False
    return True


def run(oracle: bool = False):
    qs = load_questions()
    con = duckdb.connect(DB, read_only=True)
    rows, passed = [], 0
    for q in qs:
        answerable = q.get("answerable", True)
        gold = con.execute(q["sql"]).df() if answerable else None
        if oracle:
            reply = json.dumps({"sql": q.get("sql", ""), "chart": {"type": "none"},
                                "assumption": "" if answerable else "No such data in the tables."})
            llm = ScriptedLLM([reply])
        else:
            llm = default_llm()
        t0 = time.time()
        try:
            res = Analyst(llm, DB).ask(q["question"], answer=False)
            if answerable:
                ok = res.ok and results_match(gold, res.data, q.get("ordered", False))
            else:
                ok = not res.ok and not res.sql
            err = res.error
        except Exception as e:  # count crashes as failures, keep going
            ok, res, err = False, None, f"{type(e).__name__}: {e}"
        passed += ok
        rows.append({
            "id": q["id"], "level": q["level"], "pass": "✅" if ok else "❌",
            "attempts": getattr(res, "attempts", 0), "secs": round(time.time() - t0, 1),
            "question": q["question"], "error": (err or "")[:120],
            "sql": getattr(res, "sql", ""),
            "got": (res.data.head(3).to_dict("records") if getattr(res, "data", None) is not None else None),
        })
        print(f"{q['id']} {rows[-1]['pass']} {q['question']}")
    con.close()

    df = pd.DataFrame(rows)
    by_level = df.groupby("level", sort=False)["pass"].apply(lambda s: f"{(s == '✅').sum()}/{len(s)}")
    if oracle:
        mode = "oracle (golden SQL fed back: harness check only)"
    else:
        m = default_llm()
        mode = f"live model: {getattr(m, 'model', type(m).__name__)}, {time.strftime('%Y-%m-%d')}"
    md = [f"# Evaluation results ({mode})", "",
          f"**Score: {passed}/{len(qs)}**", "",
          "| Level | Passed |", "|---|---|", *[f"| {k} | {v} |" for k, v in by_level.items()], "",
          df.drop(columns=["error", "sql", "got"]).to_markdown(index=False)]
    fails = df[df["pass"] == "❌"]
    if len(fails):
        md += ["", "## Failures", *[f"- **{r.id}** {r.question} — {r.error or 'wrong result'}\n  - got: `{r.got}`\n  - SQL: `{' '.join(str(r.sql).split())}`" for r in fails.itertuples()]]
    out = ROOT / "eval" / ("results_oracle.md" if oracle else "results.md")
    out.write_text("\n".join(md) + "\n")
    print(f"\nScore: {passed}/{len(qs)}  → {out.relative_to(ROOT)}")
    return passed, len(qs)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--oracle", action="store_true")
    run(ap.parse_args().oracle)
