from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from .contracts import DetailLevel, RecommendationScale


@dataclass(frozen=True)
class StageProfile:
    instruction: str
    allowed_scales: tuple[RecommendationScale, ...]
    max_immediate_insertion_words: int


@dataclass(frozen=True)
class DetailProfile:
    target_pages: int
    priority_area_range: tuple[int, int]


STAGE_PROFILES: Mapping[str, StageProfile] = MappingProxyType(
    {
    "early_drafting": StageProfile(
        "Challenge strategic framing where needed, but keep any immediate edit suitable "
        "for a short concept document. Carry larger changes as preparation priorities.",
        (RecommendationScale.PREPARATION_PRIORITY, RecommendationScale.TARGETED_EDIT),
        80,
    ),
    "concept_review": StageProfile(
        "Recommend material but bounded changes to strategic choices and architecture.",
        (RecommendationScale.SUBSTANTIVE_REVISION, RecommendationScale.TARGETED_EDIT),
        180,
    ),
    "decision_review": StageProfile(
        "Recommend specific revisions to objectives, results, risks, and delivery choices.",
        (RecommendationScale.SUBSTANTIVE_REVISION, RecommendationScale.TARGETED_EDIT),
        140,
    ),
    "roc_oc": StageProfile(
        "Focus on discrete management decisions and implementability refinements.",
        (RecommendationScale.TARGETED_EDIT,),
        100,
    ),
    "finalization": StageProfile(
        "Limit advice to precise clarification, correction, consistency, and indicator edits.",
        (RecommendationScale.FINE_TUNING,),
        60,
    ),
    "response_to_comments": StageProfile(
        "Link each action to the issue being resolved and propose concise response language.",
        (RecommendationScale.COMMENT_RESPONSE,),
        100,
    ),
    }
)

DETAIL_PROFILES: Mapping[DetailLevel, DetailProfile] = MappingProxyType(
    {
        DetailLevel.BRIEF: DetailProfile(1, (2, 3)),
        DetailLevel.STANDARD: DetailProfile(2, (3, 5)),
        DetailLevel.IN_DEPTH: DetailProfile(3, (4, 7)),
    }
)
