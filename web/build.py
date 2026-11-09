"""Build the browser demo: inline the prompts (and any recordings) into the page and the Netlify function.

    python web/build.py            # writes web/dist/ai-analyst/index.html and web/dist/netlify/functions/llm.mjs

prompts.json is generated from analyst/semantic.py (SQLite-dialect rules added) so the
browser agent and the Python agent share one set of KPI definitions.
"""
import json
import os
from pathlib import Path

W = Path(__file__).parent
prompts = (W / "prompts.json").read_text()
recs = (W / "recordings.json").read_text() if (W / "recordings.json").exists() else "[]"
out = W / "dist"
(out / "ai-analyst").mkdir(parents=True, exist_ok=True)
(out / "netlify" / "functions").mkdir(parents=True, exist_ok=True)
(out / "ai-analyst" / "index.html").write_text((W / "index.template.html").read_text().replace("__PROMPTS__", prompts).replace("__RECORDINGS__", recs))
(out / "netlify" / "functions" / "llm.mjs").write_text((W / "netlify" / "functions" / "llm.template.mjs").read_text().replace("__PROMPTS__", prompts))
print("built", out, "recordings:", len(json.loads(recs)))
