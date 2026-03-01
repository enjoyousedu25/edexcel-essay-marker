from __future__ import annotations
import os
import json
from typing import Dict, Any, List, Optional, Tuple

from spellchecker import SpellChecker
import textstat

from openai import OpenAI

from .rubric import RubricAspect, default_rubric, clamp_mark, level_for_mark
from .text_utils import split_sentences

def _has_openai() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())

def score_essay(
    essay_text: str,
    task_brief: str = "",
    rubric: Optional[List[RubricAspect]] = None,
) -> Dict[str, Any]:
    rubric = rubric or default_rubric()

    essay_text = (essay_text or "").strip()
    if not essay_text:
        return {
            "mode": "no-text",
            "error": "No text could be extracted. Try a clearer scan, or upload a PDF with selectable text.",
        }

    if _has_openai():
        try:
            return _score_with_openai(essay_text, task_brief, rubric)
        except Exception as e:
            # fall back to basic mode
            basic = _score_basic(essay_text)
            basic["mode"] = "basic-fallback"
            basic["warning"] = f"AI scoring failed; showing basic feedback instead. ({type(e).__name__})"
            return basic

    return _score_basic(essay_text)

def _score_basic(text: str) -> Dict[str, Any]:
    # Very lightweight fallback: readability + spelling suggestions
    spell = SpellChecker()
    words = [w.strip(".,;:!?()[]{}\"'").lower() for w in text.split()]
    words = [w for w in words if w.isalpha() and len(w) > 2]
    miss = list(spell.unknown(words))[:40]
    suggestions = []
    for w in miss[:20]:
        suggestions.append({"word": w, "suggestion": next(iter(spell.candidates(w)), "")})

    return {
        "mode": "basic",
        "readability": {
            "flesch_reading_ease": textstat.flesch_reading_ease(text),
            "flesch_kincaid_grade": textstat.flesch_kincaid_grade(text),
            "gunning_fog": textstat.gunning_fog(text),
            "sentence_count": textstat.sentence_count(text),
            "word_count": textstat.lexicon_count(text, removepunct=True),
        },
        "spelling": {
            "possible_misspellings": suggestions,
            "note": "Basic mode cannot apply the full Edexcel rubric. Add OPENAI_API_KEY for rubric-based marking.",
        },
        "improvements": [
            "Check paragraphing: each new idea should start a new paragraph.",
            "Vary sentence openings and lengths to improve flow and control.",
            "Proofread for punctuation (commas/full stops) and common spelling errors.",
        ],
    }

def _score_with_openai(text: str, task_brief: str, rubric: List[RubricAspect]) -> Dict[str, Any]:
    client = OpenAI()

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    rubric_payload = []
    for a in rubric:
        rubric_payload.append({
            "code": a.code,
            "title": a.title,
            "max_mark": a.max_mark,
            "levels": [
                {
                    "level": b.level,
                    "mark_range": [b.mark_min, b.mark_max],
                    "descriptors": b.descriptors,
                } for b in a.levels
            ],
        })

    system = (
        "You are an experienced Edexcel English language examiner. "
        "Mark the essay strictly against the provided rubric aspects. "
        "Be fair, specific, and practical. Return ONLY valid JSON."
    )

    user = {
        "task_brief": task_brief,
        "rubric": rubric_payload,
        "essay_text": text,
        "essay_sentences": [{"i": i, "s": s} for i, s in enumerate(split_sentences(text, max_sentences=120))],
        "instructions": [
            "For each rubric aspect, choose a level and a mark within the band, and justify briefly using evidence from the essay.",
            "List 8-15 highest-impact mistakes or issues. Each item must include: category (spelling/grammar/punctuation/structure/vocabulary/tone/register), quote_snippet (short), what_is_wrong, and improved_version.",
            "Also provide sentence_feedback for problematic sentences only: sentence_index must match the provided essay_sentences indices; include 1-3 concise issues and an improved_sentence.",
            "Give 5-8 actionable improvement steps, aligned to moving up the next level.",
            "Keep any quoted snippets short (<= 20 words).",
        ],
            "output_schema": {
        "overall_summary": "string",
        "aspect_scores": [
            {
                "code": "string",
                "level": "integer",
                "mark": "integer",
                "justification": "string",
                "strengths": ["string"],
                "targets": ["string"]
            }
        ],
        "mistakes": [
            {
                "category": "string",
                "quote_snippet": "string",
                "what_is_wrong": "string",
                "improved_version": "string"
            }
        ],
        "sentence_feedback": [
            {
                "sentence_index": "integer",
                "issues": ["string"],
                "improved_sentence": "string"
            }
        ],
        "improvement_plan": ["string"],
        "confidence": "string"
    }
}

    # Use JSON mode via response_format if supported by the user's OpenAI plan/models.
    # If not supported, the strict JSON instruction usually still works.
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user)},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )

    raw = resp.choices[0].message.content
    data = json.loads(raw)

    # Clamp marks + recompute levels safely to match rubric bands
    aspect_map = {a.code: a for a in rubric}
    for s in data.get("aspect_scores", []):
        code = s.get("code")
        if code in aspect_map:
            aspect = aspect_map[code]
            s["mark"] = clamp_mark(int(s.get("mark", 0)), aspect)
            s["level"] = level_for_mark(int(s["mark"]), aspect)

    data["mode"] = "ai"
    data["model"] = model
    return data
