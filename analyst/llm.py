"""Thin wrapper around the language model.

Anthropic (Claude) is the default; OpenAI works too. The rest of the code only
calls `complete(system, messages)`, so swapping models is a one-line change,
and the tests use a scripted fake instead of a real model.
"""
import os


class LLM:
    def complete(self, system: str, messages: list[dict]) -> str:  # pragma: no cover - interface
        raise NotImplementedError


class AnthropicLLM(LLM):
    def __init__(self, model: str | None = None):
        import anthropic

        self.client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
        self.model = model or os.getenv("ANALYST_MODEL", "claude-sonnet-5-5")

    def complete(self, system, messages):
        r = self.client.messages.create(
            model=self.model, max_tokens=1500, system=system, messages=messages
        )
        return "".join(b.text for b in r.content if b.type == "text")


class OpenAILLM(LLM):
    def __init__(self, model: str | None = None):
        import openai

        self.client = openai.OpenAI()  # reads OPENAI_API_KEY
        self.model = model or os.getenv("ANALYST_MODEL", "gpt-4.1")

    def complete(self, system, messages):
        r = self.client.chat.completions.create(
            model=self.model, temperature=0,
            messages=[{"role": "system", "content": system}, *messages],
        )
        return r.choices[0].message.content


class ScriptedLLM(LLM):
    """Returns pre-written replies in order. Used by tests and the offline demo."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def complete(self, system, messages):
        self.calls.append(list(messages))
        if not self.replies:
            raise RuntimeError("ScriptedLLM ran out of replies")
        return self.replies.pop(0)


def default_llm() -> LLM:
    provider = os.getenv("ANALYST_PROVIDER", "anthropic").lower()
    if provider == "openai":
        return OpenAILLM()
    return AnthropicLLM()
