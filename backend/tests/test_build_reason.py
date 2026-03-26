"""
Unit tests for _build_reason() in services/dynamic_roadmap_service.py.

All tests are pure-Python — no database, no SQLAlchemy session required.
SkillProfile objects are replaced by lightweight MagicMock instances.
"""
import pytest
from unittest.mock import MagicMock

from services.dynamic_roadmap_service import (
    _build_reason,
    STATE_COMPLETED,
    STATE_SKIPPABLE,
    STATE_FAST_TRACKED,
    STATE_UNLOCKED,
    STATE_LOCKED,
)

# ---------------------------------------------------------------------------
# Constants shared across all tests
# ---------------------------------------------------------------------------
SKIP_T = 0.75
FAST_T = 0.50
COURSE_ID = "python:variables"


# ---------------------------------------------------------------------------
# Helper — create a minimal SkillProfile mock
# ---------------------------------------------------------------------------
def make_profile(
    confidence: float = 0.0,
    github_confidence: float = 0.0,
    resume_confidence: float = 0.0,
) -> MagicMock:
    p = MagicMock()
    p.confidence = confidence
    p.github_confidence = github_confidence
    p.resume_confidence = resume_confidence
    return p


# ---------------------------------------------------------------------------
# Convenience wrapper — keeps call sites concise
# ---------------------------------------------------------------------------
def build(
    status: str,
    course_id: str = COURSE_ID,
    profile=None,
    prereq_ids: set | None = None,
    satisfied_ids: set | None = None,
    completed_event_ids: set | None = None,
    skipped_event_ids: set | None = None,
    quiz_passed_ids: set | None = None,
    quiz_scores: dict | None = None,
    skip_threshold: float = SKIP_T,
    fast_track_threshold: float = FAST_T,
    is_force_unlocked: bool = False,
) -> str:
    return _build_reason(
        status=status,
        course_id=course_id,
        profile=profile,
        prereq_ids=prereq_ids or set(),
        satisfied_ids=satisfied_ids or set(),
        completed_event_ids=completed_event_ids or set(),
        skipped_event_ids=skipped_event_ids or set(),
        quiz_passed_ids=quiz_passed_ids or set(),
        quiz_scores=quiz_scores or {},
        skip_threshold=skip_threshold,
        fast_track_threshold=fast_track_threshold,
        is_force_unlocked=is_force_unlocked,
    )


# ===========================================================================
# STATE_COMPLETED sub-variants
# ===========================================================================


class TestStateCompleted:
    def test_quiz_passed_with_score(self):
        """Quiz passage with a numeric score shows rounded percentage."""
        reason = build(
            status=STATE_COMPLETED,
            quiz_passed_ids={COURSE_ID},
            quiz_scores={COURSE_ID: 0.87},
        )
        assert reason == "Passed quiz (87%)"

    def test_quiz_passed_without_score(self):
        """Quiz passage with score=None omits the percentage."""
        reason = build(
            status=STATE_COMPLETED,
            quiz_passed_ids={COURSE_ID},
            quiz_scores={},  # no score entry
        )
        assert reason == "Passed quiz"

    def test_skipped_with_profile(self):
        """Skip event with a real profile shows the confidence percentage."""
        profile = make_profile(confidence=0.82)
        reason = build(
            status=STATE_COMPLETED,
            skipped_event_ids={COURSE_ID},
            profile=profile,
        )
        assert reason == "Skipped — high confidence (82%)"

    def test_skipped_without_profile(self):
        """Skip event with profile=None uses the generic expertise message."""
        reason = build(
            status=STATE_COMPLETED,
            skipped_event_ids={COURSE_ID},
            profile=None,
        )
        assert reason == "Skipped — prior expertise confirmed"

    def test_completed_via_event_only(self):
        """Plain completion event (no quiz, no skip) returns 'Completed'."""
        reason = build(
            status=STATE_COMPLETED,
            completed_event_ids={COURSE_ID},
        )
        assert reason == "Completed"

    def test_quiz_wins_over_skip(self):
        """When course is in both quiz_passed_ids and skipped_event_ids, quiz takes priority."""
        profile = make_profile(confidence=0.90)
        reason = build(
            status=STATE_COMPLETED,
            quiz_passed_ids={COURSE_ID},
            quiz_scores={COURSE_ID: 0.95},
            skipped_event_ids={COURSE_ID},
            profile=profile,
        )
        assert reason == "Passed quiz (95%)"


# ===========================================================================
# STATE_SKIPPABLE sub-variants
# ===========================================================================


class TestStateSkippable:
    def test_github_dominant(self):
        """GitHub confidence alone meets skip_threshold — resume does not."""
        profile = make_profile(
            confidence=0.80,
            github_confidence=SKIP_T,
            resume_confidence=0.30,
        )
        reason = build(status=STATE_SKIPPABLE, profile=profile)
        assert reason == "Skip available — GitHub shows strong experience"

    def test_resume_dominant(self):
        """Resume confidence alone meets skip_threshold — GitHub does not."""
        profile = make_profile(
            confidence=0.80,
            github_confidence=0.20,
            resume_confidence=SKIP_T,
        )
        reason = build(status=STATE_SKIPPABLE, profile=profile)
        assert reason == "Skip available — resume mentions this skill"

    def test_both_sources_meet_threshold(self):
        """Both GitHub and resume confidence meet skip_threshold."""
        profile = make_profile(
            confidence=0.90,
            github_confidence=SKIP_T,
            resume_confidence=SKIP_T,
        )
        reason = build(status=STATE_SKIPPABLE, profile=profile)
        assert reason == "Skip available — GitHub + resume signal"

    def test_neither_source_meets_threshold(self):
        """Composite confidence is high but individual sources are below skip_threshold."""
        profile = make_profile(
            confidence=0.80,
            github_confidence=0.50,
            resume_confidence=0.50,
        )
        reason = build(status=STATE_SKIPPABLE, profile=profile)
        assert reason == "Skip available — high confidence (80%)"

    def test_profile_is_none_fallback(self):
        """profile=None causes all confidences to be treated as 0.0."""
        reason = build(status=STATE_SKIPPABLE, profile=None)
        assert reason == "Skip available — high confidence (0%)"


# ===========================================================================
# STATE_FAST_TRACKED sub-variants
# ===========================================================================


class TestStateFastTracked:
    def test_github_dominant(self):
        """GitHub confidence alone meets fast_track_threshold."""
        profile = make_profile(
            confidence=0.60,
            github_confidence=FAST_T,
            resume_confidence=0.10,
        )
        reason = build(status=STATE_FAST_TRACKED, profile=profile)
        assert reason == "Fast-track — GitHub shows some experience"

    def test_resume_dominant(self):
        """Resume confidence alone meets fast_track_threshold."""
        profile = make_profile(
            confidence=0.60,
            github_confidence=0.10,
            resume_confidence=FAST_T,
        )
        reason = build(status=STATE_FAST_TRACKED, profile=profile)
        assert reason == "Fast-track — resume mentions this skill"

    def test_both_sources_meet_threshold(self):
        """Both GitHub and resume meet fast_track_threshold."""
        profile = make_profile(
            confidence=0.65,
            github_confidence=FAST_T,
            resume_confidence=FAST_T,
        )
        reason = build(status=STATE_FAST_TRACKED, profile=profile)
        assert reason == "Fast-track — GitHub + resume signal"

    def test_neither_source_meets_threshold(self):
        """Composite confidence triggers fast-track but individual sources are below threshold."""
        profile = make_profile(
            confidence=0.55,
            github_confidence=0.30,
            resume_confidence=0.30,
        )
        reason = build(status=STATE_FAST_TRACKED, profile=profile)
        assert reason == "Fast-track — high confidence (55%)"


# ===========================================================================
# STATE_UNLOCKED sub-variants
# ===========================================================================


class TestStateUnlocked:
    def test_force_unlocked(self):
        """is_force_unlocked=True returns the entry-point message regardless of prereqs."""
        reason = build(
            status=STATE_UNLOCKED,
            prereq_ids={"python:basics"},
            satisfied_ids={"python:basics"},
            is_force_unlocked=True,
        )
        assert reason == "Entry point — start here"

    def test_no_prerequisites(self):
        """Empty prereq set means no prerequisites — course is immediately ready."""
        reason = build(
            status=STATE_UNLOCKED,
            prereq_ids=set(),
        )
        assert reason == "No prerequisites — ready to start"

    def test_single_prerequisite_singular(self):
        """Exactly 1 prerequisite uses the singular noun form."""
        reason = build(
            status=STATE_UNLOCKED,
            prereq_ids={"python:basics"},
            satisfied_ids={"python:basics"},
        )
        assert reason == "Unlocked — all 1 prerequisite complete"

    def test_multiple_prerequisites_plural(self):
        """Three prerequisites use the plural noun form."""
        prereqs = {"python:basics", "python:loops", "python:functions"}
        reason = build(
            status=STATE_UNLOCKED,
            prereq_ids=prereqs,
            satisfied_ids=prereqs,
        )
        assert reason == "Unlocked — all 3 prerequisites complete"


# ===========================================================================
# STATE_LOCKED sub-variants
# ===========================================================================


class TestStateLocked:
    def test_single_unsatisfied_singular(self):
        """One unsatisfied prerequisite uses the singular noun form."""
        reason = build(
            status=STATE_LOCKED,
            prereq_ids={"python:basics"},
            satisfied_ids=set(),
        )
        assert reason == "Locked — 1 prerequisite remaining"

    def test_multiple_unsatisfied_plural(self):
        """Three unsatisfied prerequisites use the plural noun form."""
        reason = build(
            status=STATE_LOCKED,
            prereq_ids={"a", "b", "c"},
            satisfied_ids=set(),
        )
        assert reason == "Locked — 3 prerequisites remaining"

    def test_mixed_satisfied_counts_only_unsatisfied(self):
        """Only the unsatisfied prerequisites are counted in the locked message."""
        # 4 total prereqs, 1 already satisfied → 3 remaining
        reason = build(
            status=STATE_LOCKED,
            prereq_ids={"a", "b", "c", "d"},
            satisfied_ids={"a"},
        )
        assert reason == "Locked — 3 prerequisites remaining"


# ===========================================================================
# Edge cases
# ===========================================================================


class TestEdgeCases:
    def test_unknown_status_returns_empty_string(self):
        """Any status string not matching a known constant returns ''."""
        reason = build(status="unknown_state")
        assert reason == ""

    def test_unknown_status_gibberish(self):
        """Garbage status also returns ''."""
        reason = build(status="foobar")
        assert reason == ""


# ===========================================================================
# Parametrized length guard — all reasons must be <= 60 characters
# ===========================================================================

_LENGTH_CASES = [
    # (test_id, kwargs)
    (
        "completed_quiz_with_score",
        dict(
            status=STATE_COMPLETED,
            quiz_passed_ids={COURSE_ID},
            quiz_scores={COURSE_ID: 0.87},
        ),
    ),
    (
        "completed_quiz_no_score",
        dict(
            status=STATE_COMPLETED,
            quiz_passed_ids={COURSE_ID},
            quiz_scores={},
        ),
    ),
    (
        "completed_skipped_with_profile",
        dict(
            status=STATE_COMPLETED,
            skipped_event_ids={COURSE_ID},
            profile=make_profile(confidence=0.82),
        ),
    ),
    (
        "completed_skipped_no_profile",
        dict(
            status=STATE_COMPLETED,
            skipped_event_ids={COURSE_ID},
            profile=None,
        ),
    ),
    (
        "completed_event_only",
        dict(
            status=STATE_COMPLETED,
            completed_event_ids={COURSE_ID},
        ),
    ),
    (
        "skippable_github_dominant",
        dict(
            status=STATE_SKIPPABLE,
            profile=make_profile(
                confidence=0.80,
                github_confidence=SKIP_T,
                resume_confidence=0.20,
            ),
        ),
    ),
    (
        "skippable_resume_dominant",
        dict(
            status=STATE_SKIPPABLE,
            profile=make_profile(
                confidence=0.80,
                github_confidence=0.20,
                resume_confidence=SKIP_T,
            ),
        ),
    ),
    (
        "skippable_both_sources",
        dict(
            status=STATE_SKIPPABLE,
            profile=make_profile(
                confidence=0.90,
                github_confidence=SKIP_T,
                resume_confidence=SKIP_T,
            ),
        ),
    ),
    (
        "skippable_fallback_confidence",
        dict(
            status=STATE_SKIPPABLE,
            profile=make_profile(confidence=0.80, github_confidence=0.50, resume_confidence=0.50),
        ),
    ),
    (
        "skippable_no_profile",
        dict(status=STATE_SKIPPABLE, profile=None),
    ),
    (
        "fast_tracked_github_dominant",
        dict(
            status=STATE_FAST_TRACKED,
            profile=make_profile(
                confidence=0.60,
                github_confidence=FAST_T,
                resume_confidence=0.10,
            ),
        ),
    ),
    (
        "fast_tracked_resume_dominant",
        dict(
            status=STATE_FAST_TRACKED,
            profile=make_profile(
                confidence=0.60,
                github_confidence=0.10,
                resume_confidence=FAST_T,
            ),
        ),
    ),
    (
        "fast_tracked_both_sources",
        dict(
            status=STATE_FAST_TRACKED,
            profile=make_profile(
                confidence=0.65,
                github_confidence=FAST_T,
                resume_confidence=FAST_T,
            ),
        ),
    ),
    (
        "fast_tracked_fallback_confidence",
        dict(
            status=STATE_FAST_TRACKED,
            profile=make_profile(confidence=0.55, github_confidence=0.30, resume_confidence=0.30),
        ),
    ),
    (
        "unlocked_force",
        dict(
            status=STATE_UNLOCKED,
            is_force_unlocked=True,
        ),
    ),
    (
        "unlocked_no_prereqs",
        dict(status=STATE_UNLOCKED, prereq_ids=set()),
    ),
    (
        "unlocked_single_prereq",
        dict(
            status=STATE_UNLOCKED,
            prereq_ids={"python:basics"},
            satisfied_ids={"python:basics"},
        ),
    ),
    (
        "unlocked_many_prereqs",
        dict(
            status=STATE_UNLOCKED,
            prereq_ids={"a", "b", "c"},
            satisfied_ids={"a", "b", "c"},
        ),
    ),
    (
        "locked_single",
        dict(
            status=STATE_LOCKED,
            prereq_ids={"python:basics"},
            satisfied_ids=set(),
        ),
    ),
    (
        "locked_many",
        dict(
            status=STATE_LOCKED,
            prereq_ids={"a", "b", "c"},
            satisfied_ids=set(),
        ),
    ),
]


@pytest.mark.parametrize("test_id,kwargs", _LENGTH_CASES, ids=[c[0] for c in _LENGTH_CASES])
def test_reason_length_at_most_60_chars(test_id: str, kwargs: dict):
    """Every reason string produced by _build_reason must be at most 60 characters."""
    reason = build(**kwargs)
    assert len(reason) <= 60, (
        f"[{test_id}] reason is {len(reason)} chars (> 60): {reason!r}"
    )
