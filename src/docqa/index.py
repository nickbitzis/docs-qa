"""Chunking and BM25 retrieval, written from scratch with the standard library."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

STOPWORDS = frozenset(
    ["a", "about", "after", "all", "also", "an", "and", "any", "are", "as", "at", "be", "been", "before", "being", "both", "but", "by", "can", "could", "did", "do", "does", "done", "each", "for", "from", "get", "got", "had", "has", "have", "how", "i", "if", "in", "into", "is", "it", "its", "just", "me", "more", "most", "my", "no", "not", "of", "on", "only", "or", "other", "our", "over", "same", "should", "so", "some", "such", "than", "that", "the", "their", "them", "then", "there", "these", "they", "this", "through", "to", "too", "under", "up", "us", "very", "was", "way", "we", "were", "what", "when", "where", "which", "who", "why", "will", "with", "would", "you", "your"]
)


@dataclass(frozen=True)
class Chunk:
    id: str
    doc: str
    title: str
    heading: str
    text: str

    @property
    def label(self) -> str:
        return f"{self.title} > {self.heading}" if self.heading else self.title


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def chunk_markdown(doc: str, markdown: str) -> list[Chunk]:
    """Split a Markdown document into one chunk per `##` section.

    Text before the first `##` becomes an intro chunk. Section-sized chunks
    keep each answer's context together and make citations point somewhere
    a reader can find.
    """
    title = doc
    sections: list[tuple[str, list[str]]] = [("", [])]
    for line in markdown.splitlines():
        if line.startswith("# ") and title == doc:
            title = line[2:].strip()
        elif line.startswith("## "):
            sections.append((line[3:].strip(), []))
        else:
            sections[-1][1].append(line)
    chunks = []
    for heading, body in sections:
        text = " ".join(" ".join(body).split())
        if text:
            chunks.append(Chunk(f"{doc}#{slug(heading) or 'intro'}", doc, title, heading, text))
    return chunks


def load_corpus(folder: str | Path) -> list[Chunk]:
    chunks = []
    for path in sorted(Path(folder).glob("*.md")):
        chunks.extend(chunk_markdown(path.stem, path.read_text()))
    if not chunks:
        raise ValueError(f"No Markdown files found in {folder}.")
    return chunks


IRREGULAR = {"kept": "keep", "paid": "pay", "sent": "send", "ran": "run", "made": "make", "lost": "lose"}


def stem(word: str) -> str:
    """A deliberately small suffix stripper. Good enough to match 'exports' with 'export'."""
    if word in IRREGULAR:
        return IRREGULAR[word]
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            word = word[: -len(suffix)]
            break
    return word


def tokenize(text: str) -> list[str]:
    return [stem(t) for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOPWORDS]


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float


class BM25Index:
    """Okapi BM25 over chunks. Headings are indexed with the body so a question
    that names a section ("rate limits") finds it even if the body uses other words."""

    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1, self.b = k1, b
        self.docs = [Counter(tokenize(f"{c.title} {c.heading} {c.heading} {c.text}")) for c in chunks]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg_len = sum(self.lengths) / len(self.lengths)
        df = Counter(term for d in self.docs for term in d)
        n = len(chunks)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def score(self, query_terms: list[str], i: int) -> float:
        doc, length = self.docs[i], self.lengths[i]
        total = 0.0
        for term in query_terms:
            tf = doc.get(term, 0)
            if not tf:
                continue
            norm = tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * length / self.avg_len))
            total += self.idf[term] * norm
        return total

    def search(self, query: str, k: int = 3) -> list[Hit]:
        terms = tokenize(query)
        scored = [Hit(c, self.score(terms, i)) for i, c in enumerate(self.chunks)]
        scored = [h for h in scored if h.score > 0]
        scored.sort(key=lambda h: (-h.score, h.chunk.id))
        return scored[:k]
