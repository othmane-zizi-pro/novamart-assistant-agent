"""API tests with the agent stubbed out: they cover the HTTP contract, the
rate limiter, and the document endpoint, not the model."""

from fastapi.testclient import TestClient

import app.api as api_module
from app.agent import AgentReply
from app.main import create_app


class StubService:
    async def ask(self, session_id: str, message: str) -> AgentReply:
        return AgentReply(
            answer="Electronics return within 15 days [returns-policy].",
            citations=["returns-policy"],
            tool_calls=[{"name": "search_knowledge_base", "args": {"query": message}}],
            refused=False,
            latency_ms=1200,
        )


def make_client(monkeypatch) -> TestClient:
    monkeypatch.setattr(api_module, "_service", StubService())
    monkeypatch.setattr(api_module, "_request_log", __import__("collections").defaultdict(
        __import__("collections").deque
    ))
    return TestClient(create_app())


def test_chat_round_trip(monkeypatch) -> None:
    client = make_client(monkeypatch)
    response = client.post("/api/chat", json={"message": "TV return window?"})
    assert response.status_code == 200
    body = response.json()
    assert body["citations"] == ["returns-policy"]
    assert body["session_id"].startswith("session-")
    assert not body["refused"]


def test_chat_preserves_session_id(monkeypatch) -> None:
    client = make_client(monkeypatch)
    response = client.post("/api/chat", json={"message": "hi", "session_id": "session-abc"})
    assert response.json()["session_id"] == "session-abc"


def test_chat_rejects_empty_and_oversized_messages(monkeypatch) -> None:
    client = make_client(monkeypatch)
    assert client.post("/api/chat", json={"message": ""}).status_code == 422
    assert client.post("/api/chat", json={"message": "x" * 2001}).status_code == 422


def test_rate_limit_kicks_in(monkeypatch) -> None:
    client = make_client(monkeypatch)
    statuses = [
        client.post("/api/chat", json={"message": "hello"}).status_code for _ in range(25)
    ]
    assert statuses.count(429) == 5


def test_document_endpoint_serves_corpus(monkeypatch) -> None:
    client = make_client(monkeypatch)
    response = client.get("/api/documents/returns-policy")
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Returns and Refunds Policy"
    assert any("restocking" in s["text"] for s in body["sections"])
    assert client.get("/api/documents/nope").status_code == 404
