// Netlify Function: the only server-side piece of the AI analyst demo.
// It holds the Anthropic key, pins the system prompts (so it can't be used as a general proxy),
// caps use per visitor and per day, and forwards one model call. Everything else runs in the browser.
const PROMPTS = __PROMPTS__;
const MODEL = process.env.ANALYST_MODEL || "claude-haiku-5-5";
const PER_VISITOR = +(process.env.ANALYST_PER_VISITOR || 10);   // calls per IP per UTC day (2 per question)
const PER_DAY = +(process.env.ANALYST_PER_DAY || 400);          // calls per UTC day, all visitors
const MAX_CHARS = 24000;
const used = { day: "", ips: new Map(), total: 0 };            // per warm instance; the Anthropic spend limit is the hard cap

const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json", "cache-control": "no-store" } });

function tick(ip) {
  const day = new Date().toISOString().slice(0, 10);
  if (used.day !== day) { used.day = day; used.ips.clear(); used.total = 0; }
  const n = (used.ips.get(ip) || 0);
  if (n >= PER_VISITOR * 2) return "You've used today's questions for this demo. The recorded answers still work, or come back tomorrow.";
  if (used.total >= PER_DAY) return "The live demo has reached today's budget. Please use the recorded answers.";
  used.ips.set(ip, n + 1); used.total += 1; return null;
}

export default async (req, context) => {
  const key = process.env.ANTHROPIC_API_KEY;
  if (req.method === "GET") return json({ ok: !!key, model: MODEL, per_visitor: PER_VISITOR });
  if (req.method !== "POST") return json({ error: "POST only" }, 405);
  if (!key) return json({ error: "Live mode is not configured on this site." }, 503);
  let body; try { body = await req.json(); } catch { return json({ error: "Bad request" }, 400); }
  const { kind, messages } = body || {};
  if (!PROMPTS[kind] || !Array.isArray(messages) || !messages.length || messages.length > 8) return json({ error: "Bad request" }, 400);
  let chars = 0;
  for (const m of messages) { if (!m || !["user", "assistant"].includes(m.role) || typeof m.content !== "string") return json({ error: "Bad request" }, 400); chars += m.content.length; }
  if (chars > MAX_CHARS) return json({ error: "Question too long" }, 413);
  const ip = (context && context.ip) || req.headers.get("x-nf-client-connection-ip") || req.headers.get("x-forwarded-for") || "unknown";
  const limited = tick(ip); if (limited) return json({ error: limited }, 429);
  const r = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: { "content-type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01" },
    body: JSON.stringify({ model: MODEL, max_tokens: 1200, system: PROMPTS[kind], messages }),
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) {
    const msg = j.error?.message || "";
    const friendly = /credit|billing|quota|rate/i.test(msg) ? "The live demo's budget is used up for now. Please use the recorded answers." : "The model call failed. Please try again or use the recorded answers.";
    return json({ error: friendly }, 502);
  }
  return json({ text: (j.content || []).filter(b => b.type === "text").map(b => b.text).join("") });
};
