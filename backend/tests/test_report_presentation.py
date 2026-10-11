"""Presentation and security checks against the genuine, unchanged release."""

import copy
import json
import re
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path
from xml.etree import ElementTree

import pytest
from solarloss_backend.errors import InvalidArtifact
from solarloss_backend.report import render_review_report
from solarloss_backend.report_chart import MAX_CHART_POINTS, MAX_CHART_SAMPLES, render_power_chart
from solarloss_backend.schema import load_versioned_review

ROOT = Path(__file__).resolve().parents[2]
APPROVED = ROOT / "artifacts/releases/v0.2.0/shading_01/approved/review_shading_01.json"
SCHEMA_SHA = "51001cac97423b454afac7b98ee733306666fe52e3ba22f5cb422ce987c461bd"


@pytest.fixture
def review():
    return load_versioned_review(APPROVED.read_bytes(), approved_v02_schema_sha256=SCHEMA_SHA)


def svg_paths(chart):
    root = ElementTree.fromstring(chart[: chart.index("</svg>") + 6])
    return {
        p.attrib["data-channel"]: p.attrib["d"] for p in root.iter() if "data-channel" in p.attrib
    }


def test_executive_hierarchy_and_recoverable_complete_appendix(review):
    before = copy.deepcopy(review)
    html = render_review_report(review, allow_approved_v2=True)
    assert review == before
    assert html.index('id="executive-summary"') < html.index('id="evidence"')
    assert html.index('id="evidence"') < html.index('id="investigation"')
    assert html.index('id="investigation"') < html.index('id="confidence"')
    assert html.index('id="confidence"') < html.index('id="technical-appendix"')
    assert "2.382" in html and "2.779" in html and "+0.397" in html
    assert "10,549 / 10,734" in html
    assert "28 unavailable expected-power samples" in html
    assert "Research validation" in html and "Event-level decision" in html
    appendix = html[html.index("Original measurement table — all retained records") :]
    assert appendix.count("<tr>") == len(review["series"]["samples"]) + 1
    for sample in review["series"]["samples"]:
        assert sample["timestamp"] in appendix
        for channel in ("measured_power", "expected_power", "raw_reference_power"):
            assert (
                str(sample[channel]) in appendix
                if sample[channel] is not None
                else "Unavailable" in appendix
            )
    for metric in review["metrics"]:
        assert str(metric["value"]) in html
        assert metric["definition"] in unescape(html)
        assert metric["population"] in unescape(html)
    for checksum in review["provenance"]["source_checksums"]:
        assert checksum["sha256"] in html and checksum["md5"] in html
    assert review["decision"]["event_review"]["reason"] in unescape(html)
    assert review["decision"]["owner_review"]["scope"] in unescape(html)
    assert re.search(r"\.appendix-record\s*\{\s*display:\s*none !important", html)
    assert "@page" in html and re.search(r"break-after:\s*avoid", html)


def test_chart_bounds_reduction_and_genuine_expected_gaps(review):
    paths = svg_paths(render_power_chart(review))
    expected_runs = sum(
        s["valid"]
        and s["expected_power"] is not None
        and (
            i == 0
            or not review["series"]["samples"][i - 1]["valid"]
            or review["series"]["samples"][i - 1]["expected_power"] is None
        )
        for i, s in enumerate(review["series"]["samples"])
    )
    assert paths["expected_power"].count("M") == expected_runs
    assert paths["measured_power"].count("M") == 1
    for path in paths.values():
        points = re.findall(r"[ML]([\d.]+),([\d.]+)", path)
        assert len(points) <= MAX_CHART_POINTS
        assert all(64 <= float(x) <= 836 and 44 <= float(y) <= 260 for x, y in points)


def test_source_declared_gap_between_rows_breaks_every_channel(review):
    review["series"]["samples"] = [review["series"]["samples"][0], review["series"]["samples"][-1]]
    review["provenance"]["exclusions"] = [
        {"start": "2022-02-08T08:00:00Z", "end": "2022-02-08T08:01:00Z", "reason": "Test-only gap"}
    ]
    assert all(p.count("M") == 2 for p in svg_paths(render_power_chart(review)).values())


@pytest.mark.parametrize(
    "power", [float("nan"), float("inf"), -float("inf"), 1e13, True, '1" onload="alert(1)']
)
def test_chart_rejects_unbounded_or_non_numeric_coordinates(review, power):
    review["series"]["samples"][0]["measured_power"] = power
    with pytest.raises(InvalidArtifact, match="finite and bounded"):
        render_power_chart(review)


def test_chart_rejects_chronology_and_unsafe_timestamp(review):
    samples = review["series"]["samples"]
    samples[1]["timestamp"] = samples[0]["timestamp"]
    with pytest.raises(InvalidArtifact, match="chronological"):
        render_power_chart(review)
    samples[0]["timestamp"] = '<svg onload="alert(1)">'
    with pytest.raises(InvalidArtifact, match="timestamp"):
        render_power_chart(review)


def test_excessive_samples_or_gap_edges_refuse_misleading_svg(review):
    samples = review["series"]["samples"]
    review["series"]["samples"] = [samples[0]] * (MAX_CHART_SAMPLES + 1)
    assert "Chart unavailable" in render_power_chart(review)
    start = datetime(2022, 2, 8, tzinfo=timezone.utc)
    review["series"]["samples"] = [
        {
            **samples[0],
            "timestamp": (start + timedelta(seconds=i)).isoformat(),
            "valid": i % 2 == 0,
            "expected_power": 500 if i % 2 == 0 else None,
        }
        for i in range(3000)
    ]
    assert "Chart unavailable" in render_power_chart(review)


def test_all_untrusted_text_is_escaped_and_no_active_dependencies(review):
    injection = '<script>alert("x")</script><svg onload="alert(1)">'
    review["candidate_checks"][0]["observed_fact"] = injection
    review["candidate_checks"][0]["sources"] = [injection]
    review["provenance"]["model"]["name"] = injection
    html = render_review_report(review, allow_approved_v2=True)
    assert injection not in html
    assert "&lt;script&gt;" in html and "&lt;svg onload=" in html
    assert "<script" not in html and "<link" not in html and "<img" not in html
    assert (
        "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'" in html
    )
    assert not re.search(r"<(?:svg|path)[^>]+\bon\w+=", html)
    assert "empirical" in html and "not a confidence interval for true counterfactual loss" in html


def test_healthy_source_remains_proposed_and_does_not_gain_shading_annotations():
    source = ROOT / "analysis/results/reviews_v3/review_healthy_20220126_0300.json"
    raw = source.read_bytes()
    review = load_versioned_review(raw, allow_experimental_v2=True)
    html = render_review_report(review, allow_experimental_v2=True)
    assert "EXPERIMENTAL — PROPOSED CONTRACT" in html
    assert "Zero labels do not certify fault-free operation" in html
    assert "Source-labelled intervention" not in html
    assert source.read_bytes() == raw
    assert json.loads(raw)["decision"]["owner_review"] is None
