"""
CleanTrack AI — AI Service Unit Tests
Tests the pure-function components (no network calls).
"""
import pytest

from ai_service.urgency_scorer import compute_urgency
from ai_service.volume_estimator import estimate_volume
from ai_service.dispatch_recommender import recommend_dispatch


class TestUrgencyScorer:
    def test_hazardous_always_high(self):
        score = compute_urgency("hazardous", 0.001)
        assert score >= 75

    def test_higher_volume_increases_score(self):
        low = compute_urgency("plastic", 0.01)
        high = compute_urgency("plastic", 5.0)
        assert high > low

    def test_score_within_bounds(self):
        for wtype in ["plastic", "glass", "metal", "cardboard", "organic", "hazardous", "unknown"]:
            score = compute_urgency(wtype, 0.5, recurrence_count=10)
            assert 0 <= score <= 100, f"Score out of range for {wtype}: {score}"

    def test_recurrence_increases_score(self):
        single = compute_urgency("organic", 0.3, recurrence_count=1)
        repeated = compute_urgency("organic", 0.3, recurrence_count=20)
        assert repeated > single


class TestVolumeEstimator:
    def test_returns_positive_volume(self):
        bbox = {"x": 0.1, "y": 0.1, "width": 0.3, "height": 0.4, "confidence": 0.8}
        vol = estimate_volume("plastic", bbox)
        assert vol > 0

    def test_no_bbox_returns_minimal(self):
        vol = estimate_volume("paper", None)
        assert vol >= 0.001

    def test_larger_bbox_larger_volume(self):
        small = estimate_volume("mixed", {"x": 0, "y": 0, "width": 0.1, "height": 0.1, "confidence": 0.9})
        large = estimate_volume("mixed", {"x": 0, "y": 0, "width": 0.8, "height": 0.8, "confidence": 0.9})
        assert large > small

    def test_volume_clamped_to_max(self):
        # Huge bbox shouldn't exceed 50 m³
        vol = estimate_volume("mixed", {"x": 0, "y": 0, "width": 1.0, "height": 1.0, "confidence": 1.0})
        assert vol <= 50.0


class TestDispatchRecommender:
    def test_hazardous_always_hazmat(self):
        vehicle, team = recommend_dispatch("hazardous", 0.001)
        assert vehicle == "hazmat_unit"
        assert team == 2

    def test_small_plastic_compact_van(self):
        vehicle, team = recommend_dispatch("plastic", 0.1)
        assert vehicle == "compact_van"

    def test_large_metal_bulk_loader(self):
        vehicle, team = recommend_dispatch("metal", 15.0)
        assert vehicle == "bulk_loader"
        assert team == 4

    def test_team_size_positive(self):
        for wtype in ["plastic", "glass", "organic", "hazardous", "mixed"]:
            _, team = recommend_dispatch(wtype, 0.5)
            assert team >= 1
