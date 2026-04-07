"""Tests for pure scoring functions in orchestrator and synthesis modules."""
from __future__ import annotations

import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.orchestrator import _reconciled_score, _risk_tier_from_score, _majority_tier, ExpertJudgeOutput
from app.synthesis import _collect_top_risks


def _make_result(
    score: int,
    tier: str,
    confidence: float,
    error: bool = False,
    module_name: str = "Judge_1_AutomatedEvaluator",
) -> ExpertJudgeOutput:
    return ExpertJudgeOutput(
        submission_id="test-001",
        module_name=module_name,
        module_version="v1.0",
        assessment_timestamp=datetime.now(timezone.utc).isoformat(),
        perspective_type="technical_evaluator",
        overall_risk_score=score,
        risk_tier=tier,  # type: ignore[arg-type]
        confidence=confidence,
        key_findings=[],
        reasoning_summary="",
        evidence=[],
        policy_alignment=[],
        detected_risks=[],
        recommended_action="",
        raw_output_reference="",
        error_flag=error,
        error_message="error" if error else "",
    )


def test_risk_tier_boundaries():
    assert _risk_tier_from_score(77) == "High"
    assert _risk_tier_from_score(78) == "Critical"
    assert _risk_tier_from_score(57) == "Medium"
    assert _risk_tier_from_score(58) == "High"
    assert _risk_tier_from_score(34) == "Low"
    assert _risk_tier_from_score(35) == "Medium"


def test_reconciled_score_high_spread_biases_upward():
    results = [
        _make_result(40, "Medium", 0.8),
        _make_result(80, "Critical", 0.8),
        _make_result(50, "High", 0.8),
    ]
    score = _reconciled_score(results)
    assert score > 55, f"Expected score > 55 with high spread, got {score}"


def test_majority_tier_returns_none_on_three_way_split():
    results = [
        _make_result(40, "Low", 0.8),
        _make_result(60, "High", 0.8),
        _make_result(80, "Critical", 0.8),
    ]
    assert _majority_tier(results) is None


def test_majority_tier_returns_common_tier():
    results = [
        _make_result(60, "High", 0.8),
        _make_result(65, "High", 0.8),
        _make_result(80, "Critical", 0.8),
    ]
    assert _majority_tier(results) == "High"


def test_error_flag_downweights_confidence():
    results = [
        _make_result(90, "Critical", 0.9, error=True),
        _make_result(30, "Low", 0.9),
        _make_result(30, "Low", 0.9),
    ]
    score = _reconciled_score(results)
    assert score < 60, f"Error-flagged judge should be downweighted, got score {score}"


def test_reconciled_score_uniform_tiers():
    results = [
        _make_result(50, "Medium", 0.8),
        _make_result(55, "Medium", 0.8),
        _make_result(52, "Medium", 0.8),
    ]
    score = _reconciled_score(results)
    assert 35 <= score <= 57, f"Expected Medium range score, got {score}"
