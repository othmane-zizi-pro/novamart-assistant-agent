"""HTTP surface for the assistant.

POST /api/chat runs one turn through the shared AgentService. The service is
created lazily on first use so the process can boot (and healthz can answer)
before the embedding index exists.
"""

import time
from collections import defaultdict, deque

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.agent import AgentReply, AgentService, new_session_id
from app.kb import load_chunks

router = APIRouter(prefix="/api")

_service: AgentService | None = None

RATE_LIMIT_WINDOW_S = 60
RATE_LIMIT_MAX_REQUESTS = 20
_request_log: dict[str, deque[float]] = defaultdict(deque)


def _get_service() -> AgentService:
    global _service
    if _service is None:
        from app.search import load_search_index

        _service = AgentService(load_search_index())
    return _service


def _enforce_rate_limit(client_ip: str) -> None:
    now = time.monotonic()
    window = _request_log[client_ip]
    while window and now - window[0] > RATE_LIMIT_WINDOW_S:
        window.popleft()
    if len(window) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Too many requests, slow down.")
    window.append(now)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    citations: list[str]
    tool_calls: list[dict]
    refused: bool
    latency_ms: int


@router.post("/chat")
async def chat(request: Request, body: ChatRequest) -> ChatResponse:
    _enforce_rate_limit(request.client.host if request.client else "unknown")
    session_id = body.session_id or new_session_id()
    try:
        reply: AgentReply = await _get_service().ask(session_id, body.message)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return ChatResponse(
        session_id=session_id,
        answer=reply.answer,
        citations=reply.citations,
        tool_calls=reply.tool_calls,
        refused=reply.refused,
        latency_ms=reply.latency_ms,
    )


@router.get("/documents/{doc_id}")
async def get_document(doc_id: str) -> dict:
    for chunk in load_chunks():
        if chunk.doc_id == doc_id:
            sections = [
                {"heading": c.heading, "text": c.text}
                for c in load_chunks()
                if c.doc_id == doc_id
            ]
            return {"doc_id": doc_id, "title": chunk.doc_title, "sections": sections}
    raise HTTPException(status_code=404, detail="unknown document")
