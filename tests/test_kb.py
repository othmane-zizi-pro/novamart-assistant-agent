from app.kb import load_chunks


def test_corpus_loads_all_documents() -> None:
    chunks = load_chunks()
    doc_ids = {c.doc_id for c in chunks}
    assert doc_ids == {
        "returns-policy",
        "exchanges",
        "price-match",
        "employee-discount",
        "gift-cards",
        "warranty-claims",
        "shipping-orders",
        "escalation",
    }


def test_chunks_are_heading_scoped() -> None:
    chunks = load_chunks()
    electronics = [c for c in chunks if c.chunk_id == "returns-policy#electronics"]
    assert len(electronics) == 1
    assert "restocking fee" in electronics[0].text
    assert all(len(c.text.split()) <= 400 for c in chunks)


def test_chunk_ids_are_unique() -> None:
    chunks = load_chunks()
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))
