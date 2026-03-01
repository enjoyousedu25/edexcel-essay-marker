from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple

@dataclass(frozen=True)
class LevelBand:
    level: int
    mark_min: int
    mark_max: int
    descriptors: List[str]

@dataclass(frozen=True)
class RubricAspect:
    code: str
    title: str
    max_mark: int
    levels: List[LevelBand]

def default_rubric() -> List[RubricAspect]:
    """Default rubric based on the user's provided AO4/AO5 tables (Questions 6 & 7)."""

    ao4 = RubricAspect(
        code="AO4",
        title="Communicate effectively and imaginatively, adapting form, tone and register for purpose and audience.",
        max_mark=27,
        levels=[
            LevelBand(0, 0, 0, ["No rewardable material."]),
            LevelBand(1, 1, 5, [
                "Communication is at a basic level, and limited in clarity.",
                "Little awareness is shown of the purpose of the writing and the intended reader.",
                "Little awareness of form, tone and register.",
            ]),
            LevelBand(2, 6, 11, [
                "Communicates in a broadly appropriate way.",
                "Shows some grasp of purpose and expectations/requirements of the intended reader.",
                "Straightforward use of form, tone and register.",
            ]),
            LevelBand(3, 12, 17, [
                "Communicates clearly.",
                "Shows a clear sense of purpose and understanding of the expectations/requirements of the intended reader.",
                "Appropriate use of form, tone and register.",
            ]),
            LevelBand(4, 18, 22, [
                "Communicates successfully.",
                "A secure realisation of purpose and expectations/requirements of the intended reader.",
                "Effective use of form, tone and register.",
            ]),
            LevelBand(5, 23, 27, [
                "Communication is perceptive and subtle.",
                "Task is sharply focused on purpose and expectations/requirements of the intended reader.",
                "Sophisticated use of form, tone and register.",
            ]),
        ],
    )

    ao5 = RubricAspect(
        code="AO5",
        title="Write clearly, using a range of vocabulary and sentence structures, with paragraphing and accurate spelling, grammar and punctuation.",
        max_mark=18,
        levels=[
            LevelBand(0, 0, 0, ["No rewardable material."]),
            LevelBand(1, 1, 3, [
                "Expresses information and ideas, with limited use of structural and grammatical features.",
                "Uses basic vocabulary, often misspelt.",
                "Uses punctuation with basic control; often repetitive sentence structures.",
            ]),
            LevelBand(2, 4, 7, [
                "Expresses and orders information and ideas; uses paragraphs and a range of structural and grammatical features.",
                "Uses some correctly spelt vocabulary (e.g., regular patterns such as prefixes/suffixes/double consonants).",
                "Uses punctuation with some control; a range of sentence structures including coordination and subordination.",
            ]),
            LevelBand(3, 8, 11, [
                "Develops and connects appropriate information and ideas; paragraphing/structure make meaning clear.",
                "Uses varied vocabulary and spells words containing irregular patterns correctly.",
                "Uses accurate and varied punctuation, adapting sentence structures as appropriate.",
            ]),
            LevelBand(4, 12, 15, [
                "Manages information and ideas with structural and grammatical features used cohesively and deliberately across the text.",
                "Uses wide, selective vocabulary with only occasional spelling errors.",
                "Positions a range of punctuation for clarity, managing sentence structures for deliberate effect.",
            ]),
            LevelBand(5, 16, 18, [
                "Manipulates complex ideas, using a range of structural and grammatical features to support coherence and cohesion.",
                "Uses extensive vocabulary strategically; rare spelling errors do not detract from meaning.",
                "Punctuates accurately to aid emphasis and precision; uses a range of sentence structures accurately and selectively to achieve effects.",
            ]),
        ],
    )

    return [ao4, ao5]

def aspect_by_code(rubric: List[RubricAspect]) -> Dict[str, RubricAspect]:
    return {a.code: a for a in rubric}

def clamp_mark(mark: int, aspect: RubricAspect) -> int:
    return max(0, min(aspect.max_mark, int(mark)))

def level_for_mark(mark: int, aspect: RubricAspect) -> int:
    m = clamp_mark(mark, aspect)
    for band in aspect.levels:
        if band.mark_min <= m <= band.mark_max:
            return band.level
    # fallback
    return 0
