from pathlib import Path
from types import SimpleNamespace

from docqa.answer import Answer, build_prompt, claude_answer, extractive_answer, parse_citations
from docqa.index import BM25Index, load_corpus

INDEX = BM25Index(load_corpus(Path(__file__).parents[1] / "corpus"))


def ask_offline(q):
    return extractive_answer(q, INDEX.search(q, 3), INDEX.idf)


def test_parse_citations():
    assert parse_citations("A [1]. B [2, 3]. Again [1].") == [1, 2, 3]
    assert parse_citations("no cites") == []


def test_grounding():
    hits = INDEX.search("refund", 2)
    assert Answer("x [1]", hits, "t", [1]).grounded
    assert not Answer("x", hits, "t", []).grounded
    bad = Answer("x [5]", hits, "t", [5])
    assert bad.invalid_citations == [5] and not bad.grounded


def test_prompt_numbers_sources():
    hits = INDEX.search("webhook signature api", 2)
    assert len(hits) == 2
    prompt = build_prompt("How are webhooks signed?", hits)
    assert prompt.startswith("<sources>\n[1] REST API > Webhooks")
    assert "[2]" in prompt and prompt.endswith("Question: How are webhooks signed?")


def test_extractive_answers_from_the_right_section():
    a = ask_offline("I was charged twice, when do I get a refund?")
    assert "5 business days" in a.text
    assert a.grounded


def test_extractive_says_when_docs_do_not_cover_it():
    a = ask_offline("Does Larkspur have a mobile app?")
    assert a.text == "The docs don't cover that."
    assert a.citations == []


def test_extractive_without_hits():
    assert extractive_answer("anything", []).sources == []


class FakeClient:
    def __init__(self, text, stop_reason="end_turn"):
        self.calls = []
        self.text, self.stop_reason = text, stop_reason
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **params):
        self.calls.append(params)
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=self.text)],
            stop_reason=self.stop_reason,
        )


def test_claude_answer_request_and_citations():
    client = FakeClient("Backups are kept for 35 days [1].")
    hits = INDEX.search("How long are backups kept?", 3)
    a = claude_answer("How long are backups kept?", hits, client=client)
    assert a.grounded and a.citations == [1] and a.mode == "claude"
    params = client.calls[0]
    assert params["model"] == "claude-opus-5-5"
    assert "only the numbered sources" in params["system"]
    assert params["messages"][0]["content"].startswith("<sources>")
    assert params["fallbacks"] == "default"


def test_claude_answer_flags_made_up_citations():
    client = FakeClient("Yes [7].")
    a = claude_answer("q", INDEX.search("backups", 2), client=client)
    assert a.invalid_citations == [7]


def test_claude_answer_handles_refusal_and_no_hits():
    a = claude_answer("q", INDEX.search("backups", 2), client=FakeClient("", stop_reason="refusal"))
    assert "declined" in a.text
    client = FakeClient("unused")
    assert claude_answer("q", [], client=client).text == "The docs don't cover that."
    assert client.calls == []
