"""LLM judge for graded qualities the deterministic checks cannot reach.

The judge sees the question, the assistant's answer, the case's expected
behavior, and the full text of the policy documents the answer cited or should
have cited. It grades two things: is the guidance correct, and is every policy
claim supported by the documents. The judge model is pinned and separate from
the agent model so scores stay comparable across runs.
"""

import json

from google.genai import types

from app.config import JUDGE_MODEL
from app.genai_client import call_with_backoff, get_client
from app.kb import load_chunks

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "correct": {"type": "boolean"},
        "grounded": {"type": "boolean"},
        "notes": {"type": "string"},
    },
    "required": ["correct", "grounded", "notes"],
}

JUDGE_INSTRUCTION = """
You grade an internal support assistant for NovaMart store employees. You receive a
question, the assistant's answer, a description of the expected behavior, and the
authoritative policy excerpts.

Return JSON:
- correct: the answer's substantive guidance matches the expected behavior and the
  policy excerpts. Minor wording differences are fine; wrong windows, fees, amounts,
  thresholds, or promises the policy does not make are not.
- grounded: every policy claim in the answer is supported by the excerpts. An answer
  that declines to answer is grounded by definition. An answer that states policy not
  present in the excerpts is not grounded, even if it happens to be plausible.
- notes: one sentence on the main reason for your verdict.
""".strip()


def _documents_text(doc_ids: set[str]) -> str:
    sections: list[str] = []
    for chunk in load_chunks():
        if chunk.doc_id in doc_ids:
            sections.append(f"[{chunk.doc_id}] {chunk.heading}\n{chunk.text}")
    return "\n\n".join(sections)


def judge_answer(
    question: str,
    answer: str,
    behavior: str,
    relevant_doc_ids: set[str],
) -> dict:
    documents = _documents_text(relevant_doc_ids) or "(no policy documents apply)"
    prompt = (
        f"QUESTION:\n{question}\n\n"
        f"ASSISTANT ANSWER:\n{answer}\n\n"
        f"EXPECTED BEHAVIOR:\n{behavior}\n\n"
        f"POLICY EXCERPTS:\n{documents}"
    )
    client = get_client()
    response = call_with_backoff(
        lambda: client.models.generate_content(
            model=JUDGE_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=JUDGE_INSTRUCTION,
                temperature=0,
                response_mime_type="application/json",
                response_schema=JUDGE_SCHEMA,
            ),
        )
    )
    return json.loads(response.text)
