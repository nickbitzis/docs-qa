"""Command line entry point: `docqa ask`, `docqa search`, `docqa eval`."""

from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path

from . import __version__
from .answer import claude_answer, extractive_answer
from .evaluate import evaluate, load_questions
from .index import BM25Index, load_corpus

HERE = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = HERE / "corpus"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="docqa", description="Question answering over a folder of Markdown docs.")
    p.add_argument("--version", action="version", version=f"docqa {__version__}")
    p.add_argument("--corpus", default=str(DEFAULT_CORPUS), help="folder of .md files (default: the bundled sample docs)")
    sub = p.add_subparsers(dest="command", required=True)

    ask = sub.add_parser("ask", help="answer a question with citations")
    ask.add_argument("question")
    ask.add_argument("-k", type=int, default=3, help="sources to retrieve, default 3")
    ask.add_argument("--offline", action="store_true", help="skip the model and answer with extracted sentences")
    ask.add_argument("--model", default="claude-opus-5-5")

    search = sub.add_parser("search", help="show the ranked sections for a query")
    search.add_argument("query")
    search.add_argument("-k", type=int, default=5)

    ev = sub.add_parser("eval", help="measure retrieval quality on labeled questions")
    ev.add_argument("questions", help="JSONL file with question and expected fields")
    ev.add_argument("-k", type=int, default=3)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        index = BM25Index(load_corpus(args.corpus))
        if args.command == "search":
            for n, hit in enumerate(index.search(args.query, args.k), start=1):
                print(f"{n}. {hit.score:5.2f}  {hit.chunk.id}  ({hit.chunk.label})")
            return 0

        if args.command == "eval":
            result = evaluate(index, load_questions(args.questions), args.k)
            print(f"{len(result.rows)} questions, k={result.k}")
            print(f"recall@{result.k}: {result.recall:.0%}   MRR: {result.mrr:.2f}")
            for q in result.misses:
                print(f"  missed: {q.question!r} (expected {q.expected})")
            return 0

        hits = index.search(args.question, args.k)
        answer = extractive_answer(args.question, hits, index.idf) if args.offline else claude_answer(args.question, hits, args.model)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(textwrap.fill(answer.text, width=88))
    if answer.sources:
        print("\nSources")
        for n, hit in enumerate(answer.sources, start=1):
            mark = "*" if n in answer.citations else " "
            print(f" {mark}[{n}] {hit.chunk.label}  ({hit.chunk.id})")
    if answer.invalid_citations:
        print(f"\nwarning: the answer cites sources that were not provided: {answer.invalid_citations}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
