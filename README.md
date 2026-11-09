# Ask the retail data — a governed AI analyst

Type a business question in plain English. The agent writes the SQL, checks it, runs it on a read-only copy of the data, fixes its own query if it fails, and answers with the number, a chart and the SQL behind it.

> "Which 5 categories made the most gross profit in 2025?"
> → a ranked table, a bar chart, a one-line answer, and the exact query that produced it.

Built on the same data and KPI definitions as my [retail performance pack](https://loay-elsafty.netlify.app/retail-performance-pack/), so the agent's numbers agree with the dashboard to the dollar.

## Why it's built this way

Most "chat with your data" demos are a prompt and a database connection. That breaks in the ways a business cares about: the model invents its own definition of revenue, a bad query runs, nobody can check where a number came from. This one is built around four rules:

| Rule | How |
|---|---|
| **One definition per KPI** | A semantic layer ([`analyst/semantic.py`](analyst/semantic.py)) defines net sales, gross margin, AOV, return rate and the rest once, and goes with every question. It also carries data-quality notes, e.g. Spain is stored as both "Spain" and "España". |
| **Nothing unsafe runs** | Every query is parsed with sqlglot and must be a single read-only `SELECT` on the three known tables: no DDL/DML, no file access, no other schemas, and a row cap ([`analyst/guard.py`](analyst/guard.py)). The database is also opened read-only. |
| **It fixes its own mistakes** | If a query is rejected or errors, the error goes back to the model for up to two more attempts ([`analyst/agent.py`](analyst/agent.py)). |
| **Every number is auditable** | The answer is written only from the query result, and the SQL is shown with it. If the data can't answer the question (marketing spend, satisfaction scores), it says so instead of guessing. |

## Does it work? The evaluation

Twenty business questions, each with a hand-written "golden" query ([`eval/questions.yaml`](eval/questions.yaml)):

- 4 easy (totals, yearly margin, order counts)
- 8 medium (joins, rankings, monthly trends, AOV by traffic source)
- 6 hard (year-on-year growth, top-10 brand share, repeat customers, the Spain/España trap)
- 2 the agent should refuse (no spend or satisfaction data)

An answer passes only if its result holds the same values as the golden query's (within 0.5%, in the right order for rankings). Column names and extra columns don't matter. Refusals pass only if no SQL was run.

```
python eval/run_eval.py            # live model → eval/results.md
python eval/run_eval.py --oracle   # feeds the golden SQL back in: proves the harness scores 20/20
```

**Live result: 19/20** with Claude Sonnet 5.5 (9 Nov 2026): 4/4 easy, 8/8 medium, 5/6 hard, 2/2 correct refusals, including the Spain/España trap. The one miss (q16, the month with the highest 2025 return rate) passed when asked again, so it's a consistency gap between runs rather than a wrong definition. Full table in [`eval/results.md`](eval/results.md).

The scorer itself is tested: wrong numbers, wrong order and missing rows all fail ([`tests/`](tests/)).

## The data

[TheLook e-commerce](https://console.cloud.google.com/marketplace/product/bigquery-public-data/thelook-ecommerce), Google's public BigQuery dataset for a fictional online clothing retailer. The public tables are regenerated daily, so this repo uses a frozen export of the retail pack's governed fact table (2023-01-01 to 2025-12-31), split into a small star schema:

| Table | Rows | Grain |
|---|---|---|
| `fct_sales` | 86,904 | one row per item sold |
| `dim_product` | 27,564 | one row per product |
| `dim_customer` | 45,230 | one row per customer |

`build_db.py` rebuilds `data/retail.duckdb` from the CSVs in `data/raw/` and fails unless the totals reconcile (86,904 items, $3,870,406 net sales).

## Run it

```bash
pip install -r requirements.txt
python build_db.py data/raw/*.csv          # builds data/retail.duckdb and checks it reconciles
export ANTHROPIC_API_KEY=sk-ant-...        # or ANALYST_PROVIDER=openai + OPENAI_API_KEY

streamlit run app.py                       # web app
python ask.py "What was the return rate by month in 2025?"   # command line
python -m pytest -q                        # 22 tests, no API key needed
```

## Project layout

```
analyst/
  semantic.py   tables, KPI definitions, rules: the model's only source of truth
  guard.py      SQL guardrails (parse, read-only, allowed tables, row cap)
  agent.py      question -> SQL -> check -> run -> self-correct -> answer
  llm.py        Claude by default, OpenAI optional, scripted fake for tests
app.py          Streamlit front end
ask.py          command line
build_db.py     builds and reconciles the DuckDB database
eval/           20 questions, golden SQL, scorer, results
tests/          guardrail, data, agent-loop and scorer tests
```

## What I'd add next

- **Clarifying questions** when a request is ambiguous ("best customers" by sales or by margin?) instead of a stated assumption.
- **Larger evaluation set** with paraphrases of each question, to measure consistency, not just accuracy.
- **Warehouse connection**: the same agent pointed at BigQuery directly, with cost limits per query.

---
Loay Elsafty · [loay-elsafty.netlify.app](https://loay-elsafty.netlify.app) · [linkedin.com/in/loay-elsafty](https://www.linkedin.com/in/loay-elsafty)

## Try it in the browser

The agent also runs entirely client-side at **[loay-elsafty.netlify.app/ai-analyst](https://loay-elsafty.netlify.app/ai-analyst/)**: same semantic layer and guardrails in JavaScript, SQL on SQLite in your browser, recorded runs for visitors without a key. See [`web/`](web/).
