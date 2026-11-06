from pathlib import Path

import pytest

from docqa.cli import main
from docqa.evaluate import Question, evaluate, load_questions
from docqa.index import BM25Index, load_corpus

ROOT = Path(__file__).parents[1]
INDEX = BM25Index(load_corpus(ROOT / "corpus"))


def test_bundled_questions_meet_the_bar():
    result = evaluate(INDEX, load_questions(ROOT / "examples" / "questions.jsonl"), k=3)
    assert result.recall == 1.0
    assert result.mrr >= 0.9


def test_recall_and_mrr_math():
    qs = [Question("rate limits 429", "api#rate-limits"), Question("zebra", "api#pagination")]
    result = evaluate(INDEX, qs, k=3)
    assert result.recall == 0.5
    assert result.mrr == 0.5
    assert [q.question for q in result.misses] == ["zebra"]


def test_unknown_expected_id():
    with pytest.raises(ValueError, match="not in the corpus"):
        evaluate(INDEX, [Question("x", "nope#nope")])


def test_bad_questions_file(tmp_path):
    f = tmp_path / "q.jsonl"
    f.write_text('{"question": "x"}\n')
    with pytest.raises(ValueError, match="line 1"):
        load_questions(f)


def test_cli_offline_ask(capsys):
    assert main(["ask", "--offline", "How long are backups kept?"]) == 0
    out = capsys.readouterr().out
    assert "35 days" in out and "*[1] Security, backups, and retention > Backups" in out


def test_cli_search_and_eval(capsys):
    assert main(["search", "webhook retries", "-k", "2"]) == 0
    assert "api#webhooks" in capsys.readouterr().out
    assert main(["eval", str(ROOT / "examples" / "questions.jsonl")]) == 0
    assert "recall@3: 100%" in capsys.readouterr().out


def test_cli_bad_corpus(capsys, tmp_path):
    assert main(["--corpus", str(tmp_path), "search", "x"]) == 2
    assert "No Markdown files" in capsys.readouterr().err
