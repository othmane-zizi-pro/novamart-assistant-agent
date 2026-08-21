"""Tests for the grounding guards around the model: citation parsing, the
refusal heuristic, and the knowledge-gap log. The model itself is judged by the
live eval suite; these guards must hold no matter what the model outputs."""

from pathlib import Path

from app.agent import REFUSAL_MARKER, _extract_citations, _is_refusal
from app.gaps import log_gap, read_gaps


def test_citations_parse_in_order_without_duplicates() -> None:
    answer = (
        "Electronics return within 15 days [returns-policy]. Even exchanges skip "
        "the restocking fee [exchanges], see also [returns-policy]."
    )
    assert _extract_citations(answer) == ["returns-policy", "exchanges"]


def test_marker_counts_as_refusal_even_with_citations() -> None:
    answer = f"This is {REFUSAL_MARKER}; ask the duty manager [escalation]."
    assert _is_refusal(answer, ["escalation"], [])


def test_uncited_unrooted_answer_counts_as_refusal() -> None:
    assert _is_refusal("Sorry, I am not sure about that.", [], [])


def test_order_lookup_grounds_an_uncited_answer() -> None:
    tool_calls = [{"name": "get_order_status", "args": {"order_number": "NM-10052"}}]
    assert not _is_refusal("Order NM-10052 is shipped.", [], tool_calls)


def test_cited_answer_is_not_a_refusal() -> None:
    assert not _is_refusal("30 days [returns-policy].", ["returns-policy"], [])


def test_gap_log_appends_entries(tmp_path: Path) -> None:
    path = tmp_path / "gaps.jsonl"
    log_gap("session-1", "what is the drone delivery policy", path=path)
    log_gap("session-1", "can customers pay in crypto", path=path)
    entries = read_gaps(path)
    assert [e["question"] for e in entries] == [
        "what is the drone delivery policy",
        "can customers pay in crypto",
    ]


def test_comma_separated_citation_lists_parse() -> None:
    answer = "The discount never stacks with a match [employee-discount, price-match]."
    assert _extract_citations(answer) == ["employee-discount", "price-match"]
