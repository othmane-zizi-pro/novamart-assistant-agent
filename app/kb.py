"""Load the policy corpus and split it into retrievable chunks.

Each markdown document carries YAML frontmatter (id, title). Chunking is
heading-aware: one chunk per H2 section, so a chunk is always a coherent policy
rule rather than an arbitrary token window. At this corpus size that yields
chunks well under embedding limits; a max-word guard splits the rare long
section on paragraph boundaries.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from app.config import CORPUS_DIR

MAX_CHUNK_WORDS = 400


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    doc_title: str
    heading: str
    text: str

    def embedding_text(self) -> str:
        return f"{self.doc_title} / {self.heading}\n{self.text}"


def _slug(heading: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", heading.lower()).strip("-")


def _split_frontmatter(raw: str) -> tuple[dict, str]:
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, flags=re.DOTALL)
    if not match:
        raise ValueError("document is missing frontmatter")
    return yaml.safe_load(match.group(1)), match.group(2)


def _split_sections(body: str) -> list[tuple[str, str]]:
    """Return (heading, text) pairs, one per H2 section."""
    title_match = re.match(r"^\s*# (.+)$", body.strip().split("\n", 1)[0])
    doc_heading = title_match.group(1) if title_match else "Overview"
    sections: list[tuple[str, str]] = []
    current_heading = doc_heading
    current_lines: list[str] = []
    for line in body.strip().split("\n"):
        if line.startswith("# "):
            continue
        if line.startswith("## "):
            if current_lines and "".join(current_lines).strip():
                sections.append((current_heading, "\n".join(current_lines).strip()))
            current_heading = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines and "".join(current_lines).strip():
        sections.append((current_heading, "\n".join(current_lines).strip()))
    return sections


def _split_long_section(heading: str, text: str) -> list[tuple[str, str]]:
    if len(text.split()) <= MAX_CHUNK_WORDS:
        return [(heading, text)]
    parts: list[tuple[str, str]] = []
    buffer: list[str] = []
    for paragraph in text.split("\n\n"):
        candidate = "\n\n".join([*buffer, paragraph])
        if buffer and len(candidate.split()) > MAX_CHUNK_WORDS:
            parts.append((f"{heading} (part {len(parts) + 1})", "\n\n".join(buffer)))
            buffer = [paragraph]
        else:
            buffer.append(paragraph)
    if buffer:
        suffix = f" (part {len(parts) + 1})" if parts else ""
        parts.append((f"{heading}{suffix}", "\n\n".join(buffer)))
    return parts


def load_chunks(corpus_dir: Path = CORPUS_DIR) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(corpus_dir.glob("*.md")):
        meta, body = _split_frontmatter(path.read_text())
        doc_id, doc_title = meta["id"], meta["title"]
        for heading, text in _split_sections(body):
            for sub_heading, sub_text in _split_long_section(heading, text):
                chunks.append(
                    Chunk(
                        chunk_id=f"{doc_id}#{_slug(sub_heading)}",
                        doc_id=doc_id,
                        doc_title=doc_title,
                        heading=sub_heading,
                        text=sub_text,
                    )
                )
    return chunks
