"""Run the evaluation suite against the live agent.

    make eval

Each case gets a fresh session (except explicit follow-ups, which share one).
Deterministic checks run first; the LLM judge grades correctness and grounding
for cases that carry an expected behavior. Results go to eval/report.md and the
exit code reflects whether every case passed, so the suite can gate CI later.
"""

import asyncio
import os
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from app.agent import AgentReply, AgentService, new_session_id
from app.config import AGENT_MODEL, JUDGE_MODEL
from app.search import load_search_index
from eval.judge import judge_answer

CASES_PATH = Path(__file__).parent / "cases.yaml"
REPORT_PATH = Path(__file__).parent / "report.md"

# Cases run sequentially with a spacing delay so the suite stays polite to rate
# limits. Paid-tier keys tolerate the 2s default; free-tier keys allow roughly
# 10 requests per minute and need EVAL_CASE_SPACING_S=12 or higher, since an
# agent turn can spend several requests on tool round trips.
CASE_SPACING_S = float(os.environ.get("EVAL_CASE_SPACING_S", "2"))


@dataclass
class CaseResult:
    case_id: str
    bucket: str
    passed: bool
    failures: list[str] = field(default_factory=list)
    judge: dict | None = None
    latency_ms: int = 0
    tool_calls: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    refused: bool = False
    answer: str = ""


def _check_deterministic(case: dict, reply: AgentReply) -> list[str]:
    expect = case.get("expect", {})
    failures: list[str] = []
    for doc_id in expect.get("citations_include", []):
        if doc_id not in reply.citations:
            failures.append(f"missing citation [{doc_id}]")
    if "tool_call" in expect:
        wanted = expect["tool_call"]
        matched = any(
            call["name"] == wanted["name"]
            and wanted.get("arg_contains", "").lower() in str(call["args"]).lower()
            for call in reply.tool_calls
        )
        if not matched:
            failures.append(f"expected tool call {wanted}")
    for fragment in expect.get("answer_contains", []):
        if fragment.lower() not in reply.answer.lower():
            failures.append(f"answer missing '{fragment}'")
    if "refused" in expect and reply.refused != expect["refused"]:
        failures.append(f"refused={reply.refused}, expected {expect['refused']}")
    return failures


async def _run_case(service: AgentService, case: dict) -> CaseResult:
    session_id = new_session_id()
    reply = await service.ask(session_id, case["question"])
    if "followup" in case:
        await asyncio.sleep(CASE_SPACING_S)
        reply = await service.ask(session_id, case["followup"])

    failures = _check_deterministic(case, reply)
    expect = case.get("expect", {})
    judge_verdict: dict | None = None
    if "behavior" in expect and not reply.refused:
        relevant = set(expect.get("citations_include", [])) | set(reply.citations)
        judge_verdict = judge_answer(
            question=case["question"],
            answer=reply.answer,
            behavior=expect["behavior"],
            relevant_doc_ids=relevant,
        )
        if not judge_verdict["correct"]:
            failures.append(f"judge: incorrect ({judge_verdict['notes']})")
        if not judge_verdict["grounded"]:
            failures.append(f"judge: ungrounded ({judge_verdict['notes']})")

    return CaseResult(
        case_id=case["id"],
        bucket=case["bucket"],
        passed=not failures,
        failures=failures,
        judge=judge_verdict,
        latency_ms=reply.latency_ms,
        tool_calls=[c["name"] for c in reply.tool_calls],
        citations=reply.citations,
        refused=reply.refused,
        answer=reply.answer,
    )


def _write_report(results: list[CaseResult], duration_s: float) -> None:
    buckets: dict[str, list[CaseResult]] = {}
    for result in results:
        buckets.setdefault(result.bucket, []).append(result)

    lines: list[str] = [
        "# Evaluation report",
        "",
        f"Agent model: `{AGENT_MODEL}`, judge model: `{JUDGE_MODEL}`.",
        f"{len(results)} cases in {duration_s:.0f}s (sequential, rate-limit spaced).",
        "",
        "## Summary",
        "",
        "| Bucket | Passed | Cases |",
        "|---|---|---|",
    ]
    for bucket, bucket_results in buckets.items():
        passed = sum(r.passed for r in bucket_results)
        lines.append(f"| {bucket} | {passed}/{len(bucket_results)} | "
                     f"{', '.join(r.case_id for r in bucket_results)} |")
    latencies = [r.latency_ms for r in results]
    lines += [
        "",
        f"Total: {sum(r.passed for r in results)}/{len(results)} passed. "
        f"Latency p50 {statistics.median(latencies):.0f} ms, "
        f"max {max(latencies)} ms.",
        "",
        "## Cases",
        "",
        "| Case | Bucket | Result | Tools | Citations | Latency |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        status = "pass" if r.passed else "FAIL: " + "; ".join(r.failures)
        lines.append(
            f"| {r.case_id} | {r.bucket} | {status} | {', '.join(r.tool_calls) or '-'} | "
            f"{', '.join(r.citations) or '-'} | {r.latency_ms} ms |"
        )
    lines += ["", "## Transcripts", ""]
    for r in results:
        lines += [f"### {r.case_id}", "", r.answer.strip(), ""]
        if r.judge:
            lines.append(f"Judge: correct={r.judge['correct']}, grounded={r.judge['grounded']}. "
                         f"{r.judge['notes']}")
            lines.append("")

    REPORT_PATH.write_text("\n".join(lines))


async def main() -> int:
    cases: list[dict[str, Any]] = yaml.safe_load(CASES_PATH.read_text())
    service = AgentService(load_search_index())
    results: list[CaseResult] = []
    started = time.monotonic()
    for i, case in enumerate(cases):
        if i:
            await asyncio.sleep(CASE_SPACING_S)
        result = await _run_case(service, case)
        marker = "ok " if result.passed else "FAIL"
        print(f"[{marker}] {result.case_id} ({result.latency_ms} ms)"
              + (f" -> {'; '.join(result.failures)}" if result.failures else ""))
        results.append(result)

    duration = time.monotonic() - started
    _write_report(results, duration)
    passed = sum(r.passed for r in results)
    print(f"\n{passed}/{len(results)} passed -> {REPORT_PATH}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
