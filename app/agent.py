"""The NovaMart assistant agent: an ADK agent with retrieval and order lookup.

AgentService is the single entry point every surface uses (CLI, HTTP API, eval
harness), so they all measure and serve exactly the same behavior.
"""

import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.config import AGENT_MODEL
from app.gaps import log_gap
from app.orders import get_order
from app.search import SearchIndex

REFUSAL_MARKER = "not covered by NovaMart policy documentation"

SYSTEM_INSTRUCTION = f"""
You are the NovaMart internal assistant. Your users are NovaMart STORE EMPLOYEES
asking about company policy and customer orders while helping customers.

Rules, in priority order:

1. Ground every policy answer in the documentation. For any policy question, call
   search_knowledge_base first, then answer ONLY from what it returns. Cite the source
   document id in square brackets after each fact, like [returns-policy], one document
   id per bracket. Never state a policy fact without a citation.
2. For order questions, extract the order number (format NM-XXXXX) and call
   get_order_status. Report exactly what the system returns. If the lookup fails, say
   the order was not found and suggest checking the number; never guess order details.
   When the order state triggers a documented policy (for example delayed more than 7
   days past the promised date), search the documentation and tell the employee what
   the policy requires.
3. If the documentation does not cover the question, or the search results do not
   actually answer it, say clearly that this is {REFUSAL_MARKER} and direct the
   employee to the duty manager or store operations per the escalation policy. Do not
   guess, extrapolate, or invent policy. Do not cite documents that do not answer the
   question.
4. Never promise exceptions to written policy, compensation beyond documented goodwill
   offers, or delivery dates other than what the order system shows.
5. Answer the question that was actually asked first, directly, then add adjacent
   policy only if it changes what the employee should do. Plain language, short
   paragraphs or bullets. When two policies interact (returns vs exchanges vs
   warranty), explain the distinction briefly.
6. Rules are category-specific. A rule written for one category (like the restocking
   fee, which applies to opened electronics) must never be applied to another
   category. If the documents define no rule for the asked category, state the
   general rule and say that no category-specific rule exists, instead of borrowing
   one from a different category.
7. Questions unrelated to NovaMart store operations (personal advice, other companies,
   general trivia) are out of scope: decline briefly and say what you can help with.
""".strip()


@dataclass
class AgentReply:
    answer: str
    citations: list[str] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    refused: bool = False
    latency_ms: int = 0


class AgentService:
    def __init__(self, search_index: SearchIndex):
        self._search_index = search_index

        def search_knowledge_base(query: str) -> dict[str, Any]:
            """Search NovaMart policy documentation.

            Args:
                query: A natural-language question about NovaMart policy.

            Returns:
                The most relevant policy sections, each with its source document id.
            """
            results = search_index.search(query)
            return {
                "results": [
                    {
                        "doc_id": r.chunk.doc_id,
                        "section": r.chunk.heading,
                        "source": r.chunk.doc_title,
                        "text": r.chunk.text,
                    }
                    for r in results
                ]
            }

        def get_order_status(order_number: str) -> dict[str, Any]:
            """Look up a customer order in the order system by its NM-XXXXX number.

            Args:
                order_number: The order number, format NM-XXXXX.

            Returns:
                The order's current status and details, or a not_found error.
            """
            return get_order(order_number)

        self._agent = Agent(
            model=AGENT_MODEL,
            name="novamart_assistant",
            description="Internal support assistant for NovaMart store employees.",
            instruction=SYSTEM_INSTRUCTION,
            tools=[search_knowledge_base, get_order_status],
            # A policy assistant should be reproducible, not creative: the same
            # question deserves the same answer on every shift.
            generate_content_config=types.GenerateContentConfig(temperature=0),
        )
        self._runner = Runner(
            app_name="novamart-assistant",
            agent=self._agent,
            session_service=InMemorySessionService(),
            auto_create_session=True,
        )

    async def ask(self, session_id: str, message: str) -> AgentReply:
        started = time.monotonic()
        content = types.Content(role="user", parts=[types.Part(text=message)])
        answer_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []

        async for event in self._runner.run_async(
            user_id="store-employee",
            session_id=session_id,
            new_message=content,
        ):
            for call in event.get_function_calls():
                tool_calls.append({"name": call.name, "args": dict(call.args or {})})
            if event.is_final_response() and event.content:
                for part in event.content.parts or []:
                    if part.text:
                        answer_parts.append(part.text)

        answer = "\n".join(answer_parts).strip()
        citations = _extract_citations(answer)
        refused = _is_refusal(answer, citations, tool_calls)
        if refused:
            log_gap(session_id, message)
        return AgentReply(
            answer=answer,
            citations=citations,
            tool_calls=tool_calls,
            refused=refused,
            latency_ms=int((time.monotonic() - started) * 1000),
        )


_CITATION_PATTERN = re.compile(r"\[([a-z][a-z0-9-]+(?:\s*,\s*[a-z][a-z0-9-]+)*)\]")


def _extract_citations(answer: str) -> list[str]:
    """Collect cited doc ids in order. The instruction asks for one id per bracket,
    but models sometimes emit [doc-a, doc-b]; both forms must parse, because the
    refusal heuristic treats an uncited answer as ungrounded."""
    seen: list[str] = []
    for match in _CITATION_PATTERN.findall(answer):
        for doc_id in re.split(r"\s*,\s*", match):
            if doc_id not in seen:
                seen.append(doc_id)
    return seen


def _is_refusal(answer: str, citations: list[str], tool_calls: list[dict[str, Any]]) -> bool:
    """A reply counts as a refusal if it says so, or if it grounds itself in nothing.

    The marker phrase is mandated by the system instruction. The structural check
    catches the quieter failure: an answer with no citation and no successful order
    lookup has no grounding, and the caller deserves to know.
    """
    if REFUSAL_MARKER.lower() in answer.lower():
        return True
    ordered = any(call["name"] == "get_order_status" for call in tool_calls)
    return not citations and not ordered


def new_session_id() -> str:
    return f"session-{uuid.uuid4().hex[:12]}"
