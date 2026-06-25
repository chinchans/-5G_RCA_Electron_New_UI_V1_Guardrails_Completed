"""Map character offsets in extracted document text to line, paragraph, and page."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class LocationContext:
    """Index for resolving global character offsets to human-readable locations."""

    text: str
    page_spans: List[Tuple[int, int, int]] = field(default_factory=list)
    paragraph_spans: List[Tuple[int, int, int]] = field(default_factory=list)

    def offset_to_line(self, offset: int) -> int:
        if not self.text:
            return 1
        clamped = max(0, min(offset, len(self.text)))
        return self.text[:clamped].count("\n") + 1

    def offset_to_paragraph(self, offset: int) -> int:
        if self.paragraph_spans:
            for start, end, para_num in self.paragraph_spans:
                if start <= offset < end:
                    return para_num
            if self.paragraph_spans and offset >= self.paragraph_spans[-1][0]:
                return self.paragraph_spans[-1][2]
            return 1

        para_starts = _blank_line_paragraph_starts(self.text)
        para = 1
        for start in para_starts:
            if start <= offset:
                para = para_starts.index(start) + 1
        return para

    def offset_to_page(self, offset: int) -> Optional[int]:
        if not self.page_spans:
            return None
        for start, end, page_num in self.page_spans:
            if start <= offset < end:
                return page_num
        if offset >= self.page_spans[-1][0]:
            return self.page_spans[-1][2]
        return self.page_spans[0][2]

    def snippet_at(self, offset: int, radius: int = 60) -> str:
        if not self.text:
            return ""
        start = max(0, offset - radius)
        end = min(len(self.text), offset + radius)
        snippet = self.text[start:end].replace("\n", " ").strip()
        if len(snippet) > 160:
            snippet = snippet[:157] + "..."
        return snippet


def _blank_line_paragraph_starts(text: str) -> List[int]:
    starts = [0]
    for match in re.finditer(r"\n\s*\n", text):
        starts.append(match.end())
    return starts


def build_finding(
    *,
    layer: str,
    pattern: str,
    matched_text: str,
    char_offset: int,
    location: Optional[LocationContext],
    score: Optional[float] = None,
    reason: str = "",
) -> dict:
    line = location.offset_to_line(char_offset) if location else None
    paragraph = location.offset_to_paragraph(char_offset) if location else None
    page = location.offset_to_page(char_offset) if location else None
    snippet = location.snippet_at(char_offset) if location else matched_text[:120]

    finding = {
        "layer": layer,
        "pattern": pattern,
        "matched_text": (matched_text or "")[:200],
        "line": line,
        "paragraph": paragraph,
        "page": page,
        "char_offset": char_offset,
        "snippet": snippet,
    }
    if score is not None:
        finding["score"] = round(score, 4)
    if reason:
        finding["reason"] = reason
    return finding
