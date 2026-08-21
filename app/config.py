"""Central configuration, read once from the environment."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

# Model IDs are pinned: ADK's default model is a preview and judge scores are only
# comparable across runs if the judge never changes underneath them.
AGENT_MODEL = os.environ.get("AGENT_MODEL", "gemini-3.7-flash")
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "gemini-3.6-flash")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "gemini-embedding-001")
EMBEDDING_DIMENSIONS = int(os.environ.get("EMBEDDING_DIMENSIONS", "768"))

CORPUS_DIR = REPO_ROOT / "corpus"
INDEX_DIR = REPO_ROOT / "data" / "index"
