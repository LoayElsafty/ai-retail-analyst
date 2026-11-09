"""Record real runs of the browser agent for the "Recorded answers" mode.

Drives the demo page in headless Chromium in "your own key" mode, asks each
question, and saves the full trace (every attempt's SQL, guardrail verdict,
rows, timing, the answer) to recordings.json. The page's replay mode then
re-animates these exact runs for visitors without a key.

    ANTHROPIC_API_KEY=sk-ant-... python record_demo.py http://localhost:8765/ai-analyst/ claude-sonnet-5-5
"""
import asyncio
import json
import os
import sys

from playwright.async_api import async_playwright

QUESTIONS = [
    "What were net sales and gross margin by year?",
    "Which 5 categories made the most gross profit in 2025?",
    "Which traffic source brings the highest average order value?",
    "How did the return rate change month by month in 2025?",
    "Which brands have the worst return rate, with at least 500 items sold?",
    "What share of 2025 net sales came from the top 10 brands?",
    "Which country's customers spend the most per order?",
    "How many customers placed more than one order?",
    "By how much did net sales grow from 2024 to 2025?",
    "Which distribution center ships fastest, and which slowest?",
    "What is net sales by department (Men vs Women) for 2024?",
    "Which month had the highest return rate in 2025, and what was it?",
    "What were total net sales from customers in Spain?",
    "Which category has the lowest gross margin?",
    "How many orders were cancelled in 2025, and what share is that?",
    "Show the top 3 brands by net sales in the Jeans category.",
    "Which weekday do we sell the most?",
    "What was our marketing spend in 2025?",
    "What is the average customer satisfaction score by category?",
    "Delete all cancelled orders from the data.",
]


async def main(url, model):
    key = os.environ["ANTHROPIC_API_KEY"]
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1200, "height": 900})
        await pg.goto(url + "#key")
        await pg.fill("#key", key)
        await pg.select_option("#model", model)
        for q in QUESTIONS:
            await pg.fill("#qin", q)
            await pg.click("#go")
            await pg.wait_for_function("!document.getElementById('go').disabled", timeout=120000)
            card = pg.locator("#feed .card").first
            print(q, "->", (await card.locator(".ans").inner_text())[:90].replace("\n", " "))
        recs = json.loads(await pg.evaluate("exportRecordings()"))
        for r in recs:
            r["mode"] = "rec"
            r["model"] = model
        json.dump(recs, open("recordings.json", "w"), indent=1)
        print(f"\n{len(recs)} recordings saved to recordings.json")
        await b.close()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "claude-sonnet-5-5"))
