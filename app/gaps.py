"""Knowledge-gap log.

Every refusal is recorded here. Declining to answer is only useful if it also
tells the policy team which documentation is missing, so refusals become a work
queue instead of dead ends.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from app.config import REPO_ROOT

GAPS_PATH = REPO_ROOT / "var" / "knowledge_gaps.jsonl"


def log_gap(session_id: str, question: str, path: Path = GAPS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "session_id": session_id,
        "question": question,
    }
    with path.open("a") as handle:
        handle.write(json.dumps(entry) + "\n")


def read_gaps(path: Path = GAPS_PATH) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
