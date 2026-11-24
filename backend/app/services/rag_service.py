"""Local retrieval index over backend/data/rag_policies/.

Reads PDF, Markdown and text files, splits them into overlapping chunks and
indexes them with TF-IDF (scikit-learn). The index is rebuilt automatically
when a file in the folder is added or changed, so the weekly watcher only has
to drop new documents into the folder.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from backend.app.config import RAG_DIR, RAG_INDEX_FILE

log = logging.getLogger("career_forge.rag")

CHUNK_WORDS = 180
OVERLAP_WORDS = 40
SUPPORTED = {".pdf", ".md", ".txt"}


@dataclass
class Chunk:
    text: str
    source: str


def read_document(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    return path.read_text(encoding="utf-8", errors="ignore")


def chunk_text(text: str, size: int = CHUNK_WORDS, overlap: int = OVERLAP_WORDS) -> list[str]:
    words = re.sub(r"\s+", " ", text).split(" ")
    words = [w for w in words if w]
    chunks, step = [], max(size - overlap, 1)
    for start in range(0, len(words), step):
        piece = words[start:start + size]
        if len(piece) >= 15:
            chunks.append(" ".join(piece))
        if start + size >= len(words):
            break
    return chunks


def _fingerprint(directory: Path) -> list[tuple[str, int, int]]:
    files = sorted(p for p in directory.glob("*") if p.suffix.lower() in SUPPORTED and p.is_file())
    return [(p.name, p.stat().st_size, int(p.stat().st_mtime)) for p in files]


class RagService:
    def __init__(self, directory: Path = RAG_DIR, index_file: Path = RAG_INDEX_FILE):
        self.directory = directory
        self.index_file = index_file
        self._chunks: list[Chunk] = []
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None
        self._fingerprint: list = []

    def build(self) -> int:
        """(Re)build the index from every supported file. Returns chunk count."""
        chunks: list[Chunk] = []
        self.directory.mkdir(parents=True, exist_ok=True)
        for path in sorted(self.directory.glob("*")):
            if path.suffix.lower() not in SUPPORTED or not path.is_file():
                continue
            try:
                text = read_document(path)
            except Exception as exc:  # corrupt or encrypted PDF
                log.warning("Skipping %s: %s", path.name, type(exc).__name__)
                continue
            chunks += [Chunk(t, path.name) for t in chunk_text(text)]
        self._chunks = chunks
        self._fingerprint = _fingerprint(self.directory)
        if chunks:
            self._vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
            self._matrix = self._vectorizer.fit_transform([c.text for c in chunks])
        else:
            self._vectorizer, self._matrix = None, None
        try:
            self.index_file.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump({"chunks": chunks, "vectorizer": self._vectorizer, "matrix": self._matrix,
                         "fingerprint": self._fingerprint}, self.index_file)
        except OSError as exc:
            log.warning("Could not persist RAG index: %s", exc)
        return len(chunks)

    def _ensure_fresh(self) -> None:
        current = _fingerprint(self.directory) if self.directory.exists() else []
        if self._fingerprint == current and (self._chunks or not current):
            return
        if self.index_file.exists() and not self._chunks:
            try:
                cached = joblib.load(self.index_file)
                if cached["fingerprint"] == current:
                    self._chunks, self._vectorizer = cached["chunks"], cached["vectorizer"]
                    self._matrix, self._fingerprint = cached["matrix"], cached["fingerprint"]
                    return
            except Exception:  # stale or incompatible cache
                pass
        self.build()

    def search(self, query: str, k: int = 4, min_score: float = 0.05) -> list[dict]:
        self._ensure_fresh()
        if not self._chunks or self._vectorizer is None or not query.strip():
            return []
        scores = linear_kernel(self._vectorizer.transform([query]), self._matrix).ravel()
        best = scores.argsort()[::-1][:k]
        return [{"text": self._chunks[i].text, "source": self._chunks[i].source, "score": round(float(scores[i]), 3)}
                for i in best if scores[i] >= min_score]

    def stats(self) -> dict:
        self._ensure_fresh()
        return {"documents": len({c.source for c in self._chunks}), "chunks": len(self._chunks)}


rag_service = RagService()
