from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from .contracts import CoreQuestion, DetailLevel, RecommendationDestination, RecommendationScale

CORE_QUESTION_LABELS = {
    CoreQuestion.DRIVERS_PRIORITIES: "Drivers and priorities",
    CoreQuestion.ACTIONS_COMMITMENT: "Critical actions and commitment",
    CoreQuestion.PROGRAM_IMPLICATIONS: "Program implications",
    CoreQuestion.IF_THEN_CALIBRATION: "Adapting to changing conditions",
}
CORE_QUESTION_EXPLANATIONS = {
    CoreQuestion.DRIVERS_PRIORITIES: (
        'Does the CPF show how the main FCV drivers and sources of resilience shaped '
        'its priorities?'
    ),
    CoreQuestion.ACTIONS_COMMITMENT: (
        "Which actions matter most, and what evidence supports the authorities' "
        'commitment and capacity to deliver them?'
    ),
    CoreQuestion.PROGRAM_IMPLICATIONS: (
        "What does this mean for the program's priorities, sequencing, geographic focus "
        'and delivery arrangements?'
    ),
    CoreQuestion.IF_THEN_CALIBRATION: (
        'This section assesses whether the CPF explains how engagement would change if '
        'FCV conditions improve or deteriorate, and suggests relevant scenarios where '
        'that link is missing.'
    ),
}
DESTINATION_LABELS = {
    RecommendationDestination.CPF_TEXT: "CPF text or annex",
    RecommendationDestination.RESULTS_FRAMEWORK: "Results framework",
    RecommendationDestination.MEETING_RECORD: "Meeting minutes or decision note",
    RecommendationDestination.ANNUAL_BUSINESS_PLANNING: (
        "Annual business planning or implementation"
    ),
}


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
        "Focus on discrete management decisions, earlier-comment follow-through and "
        "feasible adjustments before finalisation. Route sensitive implementation "
        "responsibilities to the meeting record or annual business planning where appropriate. "
        "Do not routinely reopen program architecture.",
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
        DetailLevel.IN_DEPTH: DetailProfile(3, (3, 5)),
    }
)
