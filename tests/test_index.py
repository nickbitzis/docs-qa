from pathlib import Path

import pytest

from docqa.index import BM25Index, Chunk, chunk_markdown, load_corpus, slug, stem, tokenize

CORPUS = Path(__file__).parents[1] / "corpus"


def test_chunk_markdown_splits_on_sections():
    md = "# Title\n\nIntro text.\n\n## First part\nAlpha\nbeta.\n\n## Empty\n\n## Second\nGamma."
    chunks = chunk_markdown("doc", md)
    assert [c.id for c in chunks] == ["doc#intro", "doc#first-part", "doc#second"]
    assert chunks[1].text == "Alpha beta."
    assert chunks[1].label == "Title > First part"
    assert chunks[0].label == "Title"


def test_slug():
    assert slug("Plans & Billing!") == "plans-billing"


def test_stem_and_tokenize():
    assert stem("exports") == stem("export") == "export"
    assert stem("kept") == stem("keeps") == "keep"
    assert stem("is") == "is"  # too short to strip
    assert tokenize("How do I export the Boards?") == ["export", "board"]


def test_load_corpus():
    chunks = load_corpus(CORPUS)
    assert len(chunks) == 30
    assert len({c.id for c in chunks}) == len(chunks)


def test_load_corpus_empty(tmp_path):
    with pytest.raises(ValueError):
        load_corpus(tmp_path)


def test_bm25_prefers_rare_terms_and_ranks():
    chunks = [
        Chunk("a", "a", "A", "", "the cat sat on the mat"),
        Chunk("b", "b", "B", "", "the dog sat on the log"),
        Chunk("c", "c", "C", "", "cats and dogs and cats again"),
    ]
    index = BM25Index(chunks)
    hits = index.search("cat")
    assert [h.chunk.id for h in hits] == ["c", "a"]
    assert hits[0].score > hits[1].score
    assert index.search("zebra") == []


def test_bm25_length_normalization():
    short = Chunk("short", "s", "S", "", "refund policy")
    long = Chunk("long", "l", "L", "", "refund " + "filler words here " * 30)
    other = Chunk("other", "o", "O", "", "nothing relevant")
    hits = BM25Index([short, long, other]).search("refund")
    assert hits[0].chunk.id == "short"


def test_headings_are_searchable():
    index = BM25Index(load_corpus(CORPUS))
    assert index.search("rate limits", 1)[0].chunk.id == "api#rate-limits"
