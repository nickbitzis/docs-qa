"""Turn retrieved chunks into an answer, with Claude or with a simple extractive fallback."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .index import Hit, tokenize

SYSTEM = """You answer questions about a product using only the numbered sources provided.
Cite every claim with the source number in square brackets, like [2].
If the sources do not contain the answer, say "The docs don't cover that." and stop.
Keep answers to three sentences or fewer."""


def build_prompt(question: str, hits: list[Hit]) -> str:
    blocks = [f"[{n}] {h.chunk.label}\n{h.chunk.text}" for n, h in enumerate(hits, start=1)]
    return "<sources>\n" + "\n\n".join(blocks) + "\n</sources>\n\nQuestion: " + question


@dataclass
class Answer:
    text: str
    sources: list[Hit]
    mode: str
    citations: list[int] = field(default_factory=list)

    @property
    def invalid_citations(self) -> list[int]:
        return [c for c in self.citations if not 1 <= c <= len(self.sources)]

    @property
    def grounded(self) -> bool:
        """True when the answer cites at least one source and every citation is real."""
        return bool(self.citations) and not self.invalid_citations


def parse_citations(text: str) -> list[int]:
    seen: list[int] = []
    for group in re.findall(r"\[(\d+(?:\s*,\s*\d+)*)\]", text):
        for n in group.split(","):
            if int(n) not in seen:
                seen.append(int(n))
    return seen


def extractive_answer(
    question: str,
    hits: list[Hit],
    idf: dict[str, float] | None = None,
    max_sentences: int = 2,
    min_weight: float = 2.0,
) -> Answer:
    """Pick the sentences that best match the question.

    No model involved. It is useful offline and as a baseline to compare the
    generated answer against. Matching terms are weighted by IDF, so a rare
    word like "backups" counts for a lot and the product name counts for
    little. A sentence needs a total weight of `min_weight` to be used.
    Without an IDF table every term weighs 1.
    """
    if not hits:
        return Answer("The docs don't cover that.", [], "extractive")
    q = set(tokenize(question))
    weight = (lambda t: idf.get(t, 0.0)) if idf else (lambda t: 1.0)
    scored = []
    for n, h in enumerate(hits, start=1):
        for pos, sentence in enumerate(re.split(r"(?<=[.!?])\s+", h.chunk.text)):
            w = sum(weight(t) for t in q & set(tokenize(sentence)))
            if w >= min_weight:
                # Earlier sources and earlier sentences win ties.
                scored.append((w, -n, -pos, sentence, n))
    if not scored:
        return Answer("The docs don't cover that.", hits, "extractive")
    best = sorted(scored, reverse=True)[:max_sentences]
    text = " ".join(f"{s} [{n}]" for *_, s, n in sorted(best, key=lambda x: (-x[1], -x[2])))
    return Answer(text, hits, "extractive", parse_citations(text))


def claude_answer(question: str, hits: list[Hit], model: str = "claude-opus-5-5", client=None) -> Answer:
    """Ask Claude to answer from the retrieved sources only.

    Credentials come from the environment (ANTHROPIC_API_KEY or a saved
    `ant auth login` profile).
    """
    if not hits:
        return Answer("The docs don't cover that.", [], "claude")
    if client is None:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - depends on install extras
            raise RuntimeError("Install the Claude extra first: uv sync --extra claude") from exc
        client = anthropic.Anthropic()
    response = client.beta.messages.create(
        model=model,
        max_tokens=1024,
        system=SYSTEM,
        messages=[{"role": "user", "content": build_prompt(question, hits)}],
        output_config={"effort": "low"},
        # If the primary model declines, the API retries on a fallback model in the same call.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if response.stop_reason == "refusal":
        return Answer("The model declined to answer this question.", hits, "claude")
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    return Answer(text, hits, "claude", parse_citations(text))
