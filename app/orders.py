"""Mock order-status service.

Stands in for NovaMart's order management system (OMS). The fixture data covers
every status the shipping policy documents, including the edge the policy cares
about: an order delayed more than 7 days past its promised date. Unknown order
numbers return a structured error, never an invented order.
"""

from typing import Any

_ORDERS: dict[str, dict[str, Any]] = {
    "NM-10041": {
        "status": "processing",
        "customer_email": "dana.cole@example.com",
        "promised_date": "2026-08-27",
        "items": ["NovaTech 27in Monitor", "HDMI cable 2m"],
        "carrier": None,
        "tracking_number": None,
    },
    "NM-10052": {
        "status": "shipped",
        "customer_email": "sam.perez@example.com",
        "promised_date": "2026-08-23",
        "items": ["Air fryer 5.5L"],
        "carrier": "CanShip",
        "tracking_number": "CS-88213307",
    },
    "NM-10063": {
        "status": "delivered",
        "customer_email": "lea.tran@example.com",
        "promised_date": "2026-08-15",
        "items": ["Running shoes size 9", "Wool socks 3-pack"],
        "carrier": "CanShip",
        "tracking_number": "CS-88102931",
    },
    "NM-10077": {
        "status": "delayed",
        "customer_email": "omar.haddad@example.com",
        "promised_date": "2026-08-10",
        "items": ["NovaHome standing desk"],
        "carrier": "FreightPro",
        "tracking_number": "FP-4471820",
    },
    "NM-10089": {
        "status": "cancelled",
        "customer_email": "june.abara@example.com",
        "promised_date": "2026-08-19",
        "items": ["Espresso machine"],
        "carrier": None,
        "tracking_number": None,
    },
    "NM-10095": {
        "status": "delayed",
        "customer_email": "kim.osei@example.com",
        "promised_date": "2026-08-18",
        "items": ["Gaming laptop 16in"],
        "carrier": "CanShip",
        "tracking_number": "CS-88991045",
    },
}


def get_order(order_number: str) -> dict[str, Any]:
    """Look up an order by its NM-XXXXX number and return its current state."""
    normalized = order_number.strip().upper()
    order = _ORDERS.get(normalized)
    if order is None:
        return {
            "error": "not_found",
            "order_number": normalized,
            "message": "No order with this number exists in the order system.",
        }
    return {"order_number": normalized, **order}
