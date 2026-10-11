import copy
import hashlib
import json
from pathlib import Path

import pytest
from solarloss_backend.errors import InvalidArtifact
from solarloss_backend.schema import load_versioned_review

from backend.local_release_server import LocalReleaseStore

ROOT = Path(__file__).resolve().parents[2]
RELEASE_DIR = ROOT / "artifacts/releases/v0.2.0/shading_01"
APPROVED = RELEASE_DIR / "approved/review_shading_01.json"
CANDIDATE = RELEASE_DIR / "candidate/review_shading_01.json"
SOURCE = ROOT / "analysis/results/reviews_v3/review_shading_01.json"
SCHEMA_SHA = "51001cac97423b454afac7b98ee733306666fe52e3ba22f5cb422ce987c461bd"


def test_release_preserves_every_historical_scientific_field():
    manifest = json.loads((RELEASE_DIR / "release-manifest.json").read_bytes())
    raw = APPROVED.read_bytes()
    release = load_versioned_review(raw, approved_v02_schema_sha256=SCHEMA_SHA)
    candidate = json.loads(CANDIDATE.read_bytes())
    assert candidate == json.loads(SOURCE.read_bytes())
    assert hashlib.sha256(CANDIDATE.read_bytes()).hexdigest() == manifest["candidate"]["sha256"]
    assert hashlib.sha256(raw).hexdigest() == manifest["promotion"]["approved_artifact_sha256"]
    assert release["approval_status"] == "owner_approved"
    assert release["decision"]["owner_review"] == manifest["artifact_owner_approval"]["record"]
    restored = copy.deepcopy(release)
    restored["approval_status"] = candidate["approval_status"]
    restored["decision"]["owner_review"] = candidate["decision"]["owner_review"]
    assert restored == candidate


def test_real_approval_does_not_bypass_default_production_gate():
    with pytest.raises(InvalidArtifact, match="not enabled for production"):
        load_versioned_review(APPROVED.read_bytes())
    with pytest.raises(InvalidArtifact, match="not enabled for production"):
        LocalReleaseStore(CANDIDATE, SCHEMA_SHA)
    with pytest.raises(InvalidArtifact, match="does not match"):
        LocalReleaseStore(APPROVED, "0" * 64)
    store = LocalReleaseStore(APPROVED, SCHEMA_SHA)
    assert store.get_review_bytes("shading_01") == APPROVED.read_bytes()
