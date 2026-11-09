# The browser demo

The same agent, ported to run entirely in the visitor's browser: the semantic layer and
guardrails are JavaScript, the SQL runs on SQLite (sql.js) over the same three tables,
and only the model call leaves the page.

Live at **https://loay-elsafty.netlify.app/ai-analyst/** with three modes:

| Mode | Model call goes to | Cost to the site |
|---|---|---|
| Recorded answers | nowhere: real runs replayed step by step | none |
| Live | `netlify/functions/llm.mjs`, which holds the key, pins the system prompts and caps use per visitor and per day | a few cents a day, hard-capped by the Anthropic spend limit |
| Your own key | api.anthropic.com directly from the browser | none |

Files:
- `index.template.html`: the page. `guard()` mirrors `analyst/guard.py` for SQLite; `ask()` is the loop in `analyst/agent.py`.
- `netlify/functions/llm.template.mjs`: the proxy. Accepts only `{kind: "sql"|"answer", messages}`, so it cannot be used as a general model proxy.
- `prompts.json`: generated from `analyst/semantic.py` with SQLite-dialect rules.
- `record_demo.py`: drives the page with a real key and saves `recordings.json` for replay mode.
- `build.py`: inlines prompts and recordings into the deployable files.

The database file (`retail.db.gz`, 2.8 MB) is built from `data/retail.duckdb` and served from the retail pack's folder on the site.
