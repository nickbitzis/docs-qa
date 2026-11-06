# docqa

Retrieval-augmented question answering over a folder of Markdown docs, built from scratch so every step is visible. It chunks the docs by section, ranks them with BM25, and has Claude answer from the top sources with numbered citations. It also measures retrieval quality, which is where most RAG systems actually fail.

## Why

Most RAG demos hide the pipeline behind a framework and a vector database. That makes them hard to reason about when answers go wrong. This project keeps each step small and testable:

1. **Chunk** each Markdown file into one chunk per `##` section, so a citation points at a heading a person can find.
2. **Retrieve** with Okapi BM25, written in about 50 lines. Keyword ranking is a strong, cheap baseline, and it is easy to debug.
3. **Answer** with Claude, using only the retrieved sources. It must cite each claim as `[n]` or say the docs don't cover it.
4. **Check** the answer. Citations are parsed, and any that point at a source that was never provided are flagged.
5. **Evaluate** retrieval with labeled questions, using recall@k and mean reciprocal rank.

The bundled corpus is documentation for Larkspur, a made-up task tracker. It is synthetic, so the repo has no licensing or privacy questions.

## Quick start

These commands need no API key:

```
$ uv run docqa ask --offline "I was charged twice, when do I get a refund?"
Duplicate charges are refunded in full within 5 business days. [1] Other refunds are
reviewed case by case. [1]

Sources
 *[1] Plans and billing > Invoices and refunds  (billing#invoices-and-refunds)

$ uv run docqa ask --offline "Does Larkspur have a mobile app?"
The docs don't cover that.
```

Offline mode picks the best matching sentences, weighting each matching word by how rare it is. It is a baseline, not a writer. A sentence that matches only on the product name does not count, so out-of-scope questions get an honest "not covered".

```
$ uv run docqa search "rate limit 429"
1.  9.94  api#rate-limits  (REST API > Rate limits)
2.  2.06  api#pagination  (REST API > Pagination)
3.  1.77  billing#plans  (Plans and billing > Plans)
```

## Answers from Claude

Install the optional SDK extra and provide credentials through the environment. Nothing is stored in the repo.

```bash
uv sync --extra claude
export ANTHROPIC_API_KEY=...   # or use a saved `ant auth login` profile
uv run docqa ask "What happens when I go over the API rate limit?"
```

The system prompt limits the model to the numbered sources, asks for a citation on every claim, and gives it an explicit way out when the sources don't have the answer. Requests run at low effort, since the task is short and grounded. They use the API's server-side fallback, so a declined request is retried on a fallback model in the same call. The CLI marks which sources were cited and warns if the answer cites a source number that does not exist.

Use `--model` to pick another model and `-k` to change how many sources are retrieved.

## Measuring retrieval

`examples/questions.jsonl` holds 18 questions, each labeled with the section that answers it.

```
$ uv run docqa eval examples/questions.jsonl
18 questions, k=3
recall@3: 100%   MRR: 0.94

$ uv run docqa eval examples/questions.jsonl -k 1
18 questions, k=1
recall@1: 89%   MRR: 0.89
  missed: 'How long do invitations stay valid?' (expected getting-started#invite-your-team)
  missed: 'I was charged twice, when do I get my money back?' (expected billing#invoices-and-refunds)
```

The two misses show the limit of keyword search. "Money back" never appears in the refunds section, and "valid" never appears next to "expire". These are the cases where embeddings or query rewriting earn their cost. Retrieving three sections instead of one already catches both, which is why `ask` defaults to `-k 3`. The test suite fails if recall@3 drops below 100% or MRR below 0.9, so a change to chunking or tokenizing can't quietly make retrieval worse.

## Use your own docs

Point `--corpus` at any folder of Markdown files:

```bash
uv run docqa --corpus ~/my-docs ask "How do I rotate keys?"
```

Write a few labeled questions for your docs and run `docqa eval` before you tune anything.

## Layout

```
corpus/              synthetic product docs
examples/            labeled retrieval questions
src/docqa/index.py   chunking, tokenizing, BM25
src/docqa/answer.py  prompt, Claude call, citation checks, offline baseline
src/docqa/evaluate.py recall@k and MRR
src/docqa/cli.py     ask, search, eval
```

## Tests

```bash
uv run --group dev pytest
```

24 tests, none of which call the API. The Claude path is tested against a fake client that checks the request shape, citation parsing, invented citations, and declined requests.

## License

MIT. See [LICENSE](LICENSE).
