from __future__ import annotations
import re
import html
from typing import List, Dict, Any, Tuple

_SENT_SPLIT = re.compile(r"""(?<=[.!?])\s+(?=[A-Z0-9\"'\(])""")

def split_sentences(text: str, max_sentences: int = 120) -> List[str]:
    # Normalise whitespace a bit
    clean = re.sub(r"\s+", " ", (text or "").strip())
    if not clean:
        return []
    parts = _SENT_SPLIT.split(clean)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) > max_sentences:
        # keep first N; caller can show note
        return parts[:max_sentences]
    return parts

def build_highlighted_html(sentences: List[str], feedback: List[Dict[str, Any]]) -> str:
    """Return safe HTML with problematic sentences highlighted and anchors."""
    issue_map = {int(f.get("sentence_index")): f for f in (feedback or []) if str(f.get("sentence_index", "")).isdigit()}
    chunks: List[str] = []
    for i, s in enumerate(sentences):
        esc = html.escape(s)
        if i in issue_map:
            chunks.append(f'<span class="sent issue" id="s{i}">{esc}</span>')
        else:
            chunks.append(f'<span class="sent" id="s{i}">{esc}</span>')
    # keep spaces between sentences
    return " ".join(chunks)
