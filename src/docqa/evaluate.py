"""Retrieval evaluation: does the right section show up, and how high?"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .index import BM25Index


@dataclass(frozen=True)
class Question:
    question: str
    expected: str  # chunk id, e.g. "billing#invoices-and-refunds"


@dataclass
class EvalResult:
    k: int
    rows: list[tuple[Question, int | None]]  # 1-based rank of the expected chunk, None if missed

    @property
    def recall(self) -> float:
        return sum(r is not None for _, r in self.rows) / len(self.rows)

    @property
    def mrr(self) -> float:
        return sum(1 / r for _, r in self.rows if r) / len(self.rows)

    @property
    def misses(self) -> list[Question]:
        return [q for q, r in self.rows if r is None]


def load_questions(path: str | Path) -> list[Question]:
    out = []
    for n, line in enumerate(Path(path).read_text().splitlines(), start=1):
        if line.strip():
            try:
                row = json.loads(line)
                out.append(Question(row["question"], row["expected"]))
            except (json.JSONDecodeError, KeyError) as exc:
                raise ValueError(f"{path} line {n}: need question and expected fields") from exc
    return out


def evaluate(index: BM25Index, questions: list[Question], k: int = 3) -> EvalResult:
    known = {c.id for c in index.chunks}
    unknown = sorted({q.expected for q in questions} - known)
    if unknown:
        raise ValueError(f"Expected chunk ids not in the corpus: {unknown}")
    rows = []
    for q in questions:
        ids = [h.chunk.id for h in index.search(q.question, k)]
        rows.append((q, ids.index(q.expected) + 1 if q.expected in ids else None))
    return EvalResult(k, rows)
