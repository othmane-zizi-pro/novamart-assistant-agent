from app.orders import get_order


def test_known_order_returns_details() -> None:
    order = get_order("NM-10052")
    assert order["status"] == "shipped"
    assert order["tracking_number"] == "CS-88213307"


def test_lookup_normalizes_case_and_whitespace() -> None:
    assert get_order("  nm-10041 ")["status"] == "processing"


def test_unknown_order_returns_structured_error() -> None:
    result = get_order("NM-99999")
    assert result["error"] == "not_found"
    assert "status" not in result
