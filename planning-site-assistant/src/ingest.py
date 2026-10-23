"""Ingest planning documents into citable chunks.

Each chunk keeps its source document and section so answers can cite
[file + section] — citation granularity is a design requirement, not a detail.
PDF support is optional (PyMuPDF); .md/.txt work with the stdlib alone.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Chunk:
    chunk_id: str
    doc: str          # file name, used in citations
    section: str      # heading the chunk came from
    text: str

    def citation(self) -> str:
        return f"{self.doc} · {self.section}"


def _split_markdown(text: str) -> list[tuple[str, str]]:
    """Split by headings; returns (section, body) pairs."""
    parts: list[tuple[str, str]] = []
    section, buf = "前言", []
    for line in text.splitlines():
        m = re.match(r"^#{1,3}\s+(.*)", line)
        if m:
            if buf:
                parts.append((section, "\n".join(buf).strip()))
            section, buf = m.group(1).strip(), []
        else:
            buf.append(line)
    if buf:
        parts.append((section, "\n".join(buf).strip()))
    return [(s, b) for s, b in parts if b]


def _paragraphs(body: str, max_chars: int = 600) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    out: list[str] = []
    for p in paras:
        while len(p) > max_chars:  # hard-split long paragraphs at sentence ends
            cut = max(p.rfind("。", 0, max_chars), p.rfind(". ", 0, max_chars))
            cut = cut + 1 if cut > 100 else max_chars
            out.append(p[:cut].strip())
            p = p[cut:].strip()
        if p:
            out.append(p)
    return out


def load_pdf(path: Path) -> list[tuple[str, str]]:
    try:
        import fitz  # PyMuPDF, optional dependency
    except ImportError:
        return []
    doc = fitz.open(path)
    return [(f"第 {i + 1} 页", page.get_text()) for i, page in enumerate(doc)]


def ingest_dir(docs_dir: str | Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(Path(docs_dir).iterdir()):
        if path.suffix.lower() in {".md", ".txt"}:
            sections = _split_markdown(path.read_text(encoding="utf-8"))
        elif path.suffix.lower() == ".pdf":
            sections = load_pdf(path)
        else:
            continue
        n = 0
        for section, body in sections:
            for para in _paragraphs(body):
                n += 1
                chunks.append(Chunk(f"{path.stem}-{n:03d}", path.name, section, para))
    return chunks


if __name__ == "__main__":
    import json, sys
    cs = ingest_dir(sys.argv[1] if len(sys.argv) > 1 else "data/docs")
    print(json.dumps([asdict(c) for c in cs], ensure_ascii=False, indent=1)[:2000])
    print(f"\n{len(cs)} chunks from {len({c.doc for c in cs})} documents")
