from atopile.cli.autolayout import _choose_candidate, _placement_ai_review
from atopile.server.domains.autolayout.models import AutolayoutCandidate


def test_choose_candidate_uses_explicit_candidate_id():
    candidates = [
        AutolayoutCandidate(candidate_id="a", score=0.1),
        AutolayoutCandidate(candidate_id="b", score=0.9),
    ]
    selected = _choose_candidate(candidates, candidate_id="a")
    assert selected.candidate_id == "a"


def test_choose_candidate_defaults_to_best_score():
    candidates = [
        AutolayoutCandidate(candidate_id="a", score=0.1),
        AutolayoutCandidate(candidate_id="b", score=0.9),
        AutolayoutCandidate(candidate_id="c", score=None),
    ]
    selected = _choose_candidate(candidates)
    assert selected.candidate_id == "b"


def test_ai_review_rejects_error_anomaly():
    candidate = AutolayoutCandidate(
        candidate_id="c1",
        score=0.99,
        metadata={
            "placementAnomalies": [
                {"severity": "ERROR", "message": "placement issue"},
            ]
        },
    )
    approved, reason, severity_counts = _placement_ai_review(candidate, min_score=0.5)
    assert approved is False
    assert "ERROR anomalies" in reason
    assert severity_counts["ERROR"] == 1


def test_ai_review_rejects_low_score():
    candidate = AutolayoutCandidate(
        candidate_id="c1",
        score=0.3,
        metadata={},
    )
    approved, reason, severity_counts = _placement_ai_review(candidate, min_score=0.5)
    assert approved is False
    assert "below threshold" in reason
    assert severity_counts["ERROR"] == 0
