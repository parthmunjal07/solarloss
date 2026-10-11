import json
from html import escape
from typing import Any

from .errors import InvalidArtifact
from .report_styles import V2_REPORT_CSS


def _e(value: Any) -> str:
    if value is None:
        value = "Not recorded"
    return escape(str(value), quote=True)


def _list(items: list[str], empty: str = "None recorded.") -> str:
    if not items:
        return f"<p>{_e(empty)}</p>"
    return "<ul>" + "".join(f"<li>{_e(item)}</li>" for item in items) + "</ul>"


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    head = "".join(f'<th scope="col">{_e(item)}</th>' for item in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{_e(value)}</td>" for value in row) + "</tr>" for row in rows
    )
    if not body:
        body = f'<tr><td colspan="{len(headers)}">No rows recorded.</td></tr>'
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def _findings(findings: list[dict[str, Any]]) -> str:
    rows = []
    for finding in findings:
        rows.append(
            [
                finding["name"],
                finding["status"],
                finding.get("result", ""),
                finding["detail"],
            ]
        )
    return _table(["Finding", "Status", "Result", "Detail"], rows)


def _render_v1_review_report(review: dict[str, Any]) -> str:
    """Render the validated artifact as static, escaped HTML without deriving findings."""
    experiment = review["experiment"]
    dataset = review["dataset"]
    metrics = review["metrics"]
    uncertainty = review["uncertainty"]
    decision = review["decision"]

    checksum_rows = [
        [checksum["scope"], checksum["algorithm"], checksum["digest"]]
        for checksum in dataset["checksums"]
    ]
    metric_rows = [
        [
            "Energy deficit",
            metrics["energy_deficit"]["value"],
            metrics["energy_deficit"]["unit"],
            metrics["energy_deficit"]["calculation"],
        ],
        [
            "Deficit fraction",
            metrics["deficit_fraction"]["value"],
            metrics["deficit_fraction"]["unit"],
            f"numerator {metrics['deficit_fraction']['numerator']['value']} {metrics['deficit_fraction']['numerator']['unit']}; denominator {metrics['deficit_fraction']['denominator']['value']} {metrics['deficit_fraction']['denominator']['unit']}",
        ],
        [
            "Coverage",
            metrics["coverage"]["value"],
            metrics["coverage"]["unit"],
            f"numerator {metrics['coverage']['numerator']['value']} {metrics['coverage']['numerator']['unit']}; denominator {metrics['coverage']['denominator']['value']} {metrics['coverage']['denominator']['unit']}",
        ],
        [
            "Calibration error",
            metrics["calibration_error"]["value"],
            metrics["calibration_error"]["unit"],
            f"{metrics['calibration_error']['statistic']}; held-out healthy data; denominator {metrics['calibration_error']['denominator']['value']} {metrics['calibration_error']['denominator']['unit']}",
        ],
        [
            "Valid intervals",
            metrics["valid_interval_count"],
            "intervals",
            "As recorded in the review artifact",
        ],
        [
            "Total intervals",
            metrics["total_interval_count"],
            "intervals",
            "As recorded in the review artifact",
        ],
    ]
    baseline = review["baseline_comparison"]
    baseline_rows = [
        [
            baseline["simple_baseline"]["name"],
            baseline["simple_baseline"]["value"],
            baseline["unit"],
        ],
        [
            baseline["calibrated_reference"]["name"],
            baseline["calibrated_reference"]["value"],
            baseline["unit"],
        ],
    ]
    if "reported_difference" in baseline:
        baseline_rows.append(
            [
                "Reported difference",
                baseline["reported_difference"]["value"],
                baseline["reported_difference"]["unit"],
            ]
        )

    interval = uncertainty.get("interval")
    if interval:
        interval_text = (
            f"Level {interval['level']}; lower {interval['lower']} {interval['unit']}; "
            f"upper {interval['upper']} {interval['unit']}"
        )
    else:
        interval_text = uncertainty.get("not_estimated_reason", "No interval recorded.")

    sample_rows = []
    for sample in review["series"]["samples"]:
        sample_rows.append(
            [
                sample["timestamp"],
                sample["measured_power"],
                sample["raw_reference_power"],
                sample["expected_power"],
                sample.get("expected_lower_bound", ""),
                sample.get("expected_upper_bound", ""),
                "valid" if sample["valid"] else "invalid",
            ]
        )

    quality_rows = [
        [check["name"], check["status"], check.get("result", ""), check["detail"]]
        for check in review["quality_checks"]
    ]
    exclusion_rows = [[item["start"], item["end"], item["reason"]] for item in review["exclusions"]]

    placebo = review["placebo"]
    robustness = review["robustness"]
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>SolarLoss review {_e(experiment["identifier"])}</title>
  <style>
    :root {{ color-scheme: light; font: 16px/1.5 system-ui, sans-serif; color: #18221d; background: #f5f7f5; }}
    body {{ margin: 0; }}
    main {{ max-width: 1080px; margin: 0 auto; padding: 2rem 1.25rem 4rem; }}
    header, section {{ background: #fff; border: 1px solid #dce4dd; border-radius: 12px; padding: 1.25rem; margin: 0 0 1rem; }}
    h1, h2 {{ line-height: 1.2; }} h1 {{ margin: 0 0 .4rem; }} h2 {{ font-size: 1.2rem; margin-top: 0; }}
    .muted {{ color: #56635b; }} .decision {{ display: inline-block; border-radius: 999px; padding: .35rem .7rem; background: #edf2ee; font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; }} th, td {{ text-align: left; padding: .55rem .65rem; border-bottom: 1px solid #e4eae5; vertical-align: top; overflow-wrap: anywhere; }}
    th {{ background: #f4f7f4; }} .table-wrap {{ overflow-x: auto; }} code {{ overflow-wrap: anywhere; }}
    @media (max-width: 640px) {{ main {{ padding: 1rem .6rem 2rem; }} header, section {{ padding: .9rem; }} }}
  </style>
</head>
<body>
<main>
  <header>
    <p class="muted">SolarLoss evidence review · schema {_e(review["schema_version"])} · analysis {_e(review["analysis_version"])}</p>
    <h1>Experiment {_e(experiment["identifier"])}</h1>
    <p>Produced at {_e(review["produced_at"])}. Review id <code>{_e(review["review_id"])}</code>.</p>
    <p class="decision">{_e(decision["state"])}</p>
    <h2>Reasons recorded by the analysis</h2>
    {_list(decision["reasons"])}
  </header>

  <section><h2>Dataset provenance</h2>
    <p><strong>{_e(dataset["name"])}</strong> · version {_e(dataset["version"])}</p>
    <p>Source: <code>{_e(dataset["source"])}</code></p>
    <p>Extraction date: {_e(dataset.get("extraction_date", "Not recorded"))}</p>
    {_table(["Checksum scope", "Algorithm", "Digest"], checksum_rows)}
  </section>

  <section><h2>Experiment</h2>
    <p>Type: {_e(experiment["type"])}</p>
    <p>Window: {_e(experiment["time_window"]["start"])} to {_e(experiment["time_window"]["end"])}</p>
    <p>Experimental system: {_e(experiment["experimental_system"]["identifier"])} — {_e(experiment["experimental_system"]["description"])}</p>
    <p>Reference system: {_e(experiment["reference_system"]["identifier"])} — {_e(experiment["reference_system"]["description"])}</p>
    <p>Label: {_e(experiment["label_provenance"]["label"])}; source {_e(experiment["label_provenance"]["source"])}; method {_e(experiment["label_provenance"]["method"])}.</p>
    <p>Label reference: {_e(experiment["label_provenance"].get("reference", "Not recorded"))}</p>
  </section>

  <section><h2>Metrics and calculation context</h2>
    <p>Power series unit: {_e(review["series"]["power_unit"])}. Energy deficit calculation: values are presented as supplied by the analysis artifact.</p>
    {_table(["Metric", "Value", "Unit", "Denominator / calculation context"], metric_rows)}
  </section>

  <section><h2>Baseline comparison</h2>
    <p>Metric: {_e(baseline["metric"])} ({_e(baseline["unit"])}); evaluation population: {_e(baseline["evaluation_population"])}.</p>
    {_table(["Method", "Value", "Unit"], baseline_rows)}
    <p>{_e(baseline.get("calculation", "No comparison calculation detail recorded."))}</p>
  </section>

  <section><h2>Uncertainty</h2>
    <p>Method: {_e(uncertainty["method"])}</p>
    <p>Independent blocks: {_e(uncertainty["independent_blocks"]["count"])} {_e(uncertainty["independent_blocks"]["unit"])}; exploratory: {_e(uncertainty["exploratory"])}.</p>
    <p>Interval: {_e(interval_text)}</p>
    <h3>Uncertainty limitations</h3>{_list(uncertainty["limitations"])}
  </section>

  <section><h2>Quality checks</h2>
    {_table(["Check", "Status", "Result", "Detail"], quality_rows)}
    <h3>Excluded intervals</h3>
    {_table(["Start (UTC)", "End (UTC)", "Reason"], exclusion_rows)}
  </section>

  <section><h2>Robustness findings</h2>
    <p>Status: {_e(robustness["status"])}</p>{_findings(robustness["findings"])}
  </section>
  <section><h2>Placebo findings</h2>
    <p>Status: {_e(placebo["status"])}</p>{_findings(placebo["findings"])}
  </section>

  <section><h2>Limitations</h2>{_list(review["limitations"])}</section>

  <section><h2>Time series</h2>
    <p>Measured power is from the experimental system. Raw reference power is the uncalibrated reference measurement. Expected power is calibrated output derived from the reference. Values use {_e(review["series"]["power_unit"])}; timestamps use {_e(review["series"]["timestamp_basis"])}.</p>
    {_table(["Timestamp (UTC)", "Measured experimental", "Raw reference", "Calibrated expected", "Expected lower bound", "Expected upper bound", "Validity"], sample_rows)}
  </section>
</main>
</body>
</html>"""


def _v2_cell(value: Any) -> str:
    if value is None:
        return "Unavailable"
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return str(value)


def _v2_rows(headers: list[str], rows: list[list[Any]]) -> str:
    return _table(headers, [[_v2_cell(cell) for cell in row] for row in rows])


def _structured(value: Any) -> str:
    """Readable escaped records, retaining full values rather than raw object cells."""
    if isinstance(value, dict):
        return (
            '<dl class="record">'
            + "".join(
                f"<div><dt>{_e(key.replace('_', ' '))}</dt><dd>{_structured(item)}</dd></div>"
                for key, item in value.items()
            )
            + "</dl>"
        )
    if isinstance(value, list):
        if not value:
            return "<span>None recorded.</span>"
        return "<ul>" + "".join(f"<li>{_structured(item)}</li>" for item in value) + "</ul>"
    return _e("Unavailable" if value is None else value)


def _report_details(title: str, body: str, *, appendix: bool = False) -> str:
    return f'<details class="{"appendix-record" if appendix else "evidence-detail"}"><summary>{_e(title)}</summary><div class="detail-body">{body}</div></details>'


def render_experimental_v2_report(review: dict[str, Any], *, owner_approved: bool = False) -> str:
    """Present the validated artifact without deriving scientific findings or totals."""
    from .report_chart import render_power_chart

    experiment = review["experiment"]
    decision = review["decision"]
    context = experiment["event_context"]
    metrics = {m["id"]: m for m in review["metrics"]}
    deviation = metrics.get("signed_generation_deviation")
    coverage = deviation["coverage"] if deviation else {}

    def figure(identifier: str, label: str, signed: bool = False) -> str:
        metric = metrics.get(identifier)
        if metric and metric["availability"] == "estimated":
            value = f"{metric['value']:+.3f}" if signed else f"{metric['value']:.3f}"
            text = f"{value} <small>{_e(metric['unit'])}</small>"
        else:
            text = "Unavailable"
        return f"<div><dt>{_e(label)}</dt><dd>{text}</dd></div>"

    valid, observed = coverage.get("valid_seconds"), coverage.get("observed_labelled_seconds")
    support = (
        f"{valid:,.0f} / {observed:,.0f}"
        if valid is not None and observed is not None
        else "Unavailable"
    )
    event_window = f"{experiment['start']} to {experiment['end']}"
    event_label = context.get("label_description", context.get("note", experiment["type"]))
    observation = (
        "Recorded target generation is compared with a calibrated healthy expectation during the source-documented shading intervention."
        if experiment["type"] == "documented_shading"
        else "Recorded target generation is compared with its calibrated expectation over a zero-labelled comparison interval. Zero labels do not certify fault-free operation."
    )
    if deviation and deviation["availability"] == "estimated":
        observation += f" The full supported interval has a signed model-expected minus measured deviation of {deviation['value']:+.6f} {_e(deviation['unit'])}."
    warning = (
        "Approved for bounded retrospective evidence presentation. Proposed checks remain unapproved."
        if owner_approved
        else "EXPERIMENTAL — PROPOSED CONTRACT. This local research report is not served by the production API."
    )
    titles = {
        "review_inverter_operating_records": "Review inverter operating records",
        "verify_measurement_and_reference_context": "Verify measurements and reference context",
        "request_shading_observation_context": "Request shading observation context",
    }
    checks = []
    for i, check in enumerate(review["candidate_checks"], 1):
        hypothesis = (
            "Suppressed because this candidate check is unavailable."
            if check["status"] == "unavailable"
            else check["hypothesis"]
        )
        detail = {**check, "hypothesis": hypothesis}
        checks.append(
            f'<article class="proposed-check"><div class="check-heading"><span class="section-number">{i:02}</span><h3>{_e(titles.get(check["id"], check["id"].replace("_", " ")))}</h3><span class="tag">{_e("Unavailable" if check["status"] == "unavailable" else "Proposed · Unapproved")}</span></div>'
            f'<dl class="check-record"><div><dt>Observation</dt><dd>{_e(check["observed_fact"])}</dd></div>'
            f"<div><dt>Why inspect this</dt><dd>{_e(hypothesis)}</dd></div>"
            f"<div><dt>Information required</dt><dd>{_list(check['next_information'])}</dd></div>"
            f"<div><dt>Supporting evidence</dt><dd>{_list(check['supporting_evidence'])}</dd></div>"
            f"<div><dt>Opposing evidence / alternatives</dt><dd>{_list(check['opposing_evidence'])}</dd></div>"
            f"<div><dt>Professional constraint</dt><dd>{_e(check['qualification'])} {_e(check['safety_constraint'])}</dd></div></dl>"
            + _report_details(
                "Sources and complete check record", _structured(detail), appendix=True
            )
            + "</article>"
        )
    timing_rows = []
    if experiment["type"] == "documented_shading":
        interval = context["label_interval_utc"]
        timing_rows += [
            ["Source intervention start", interval["start"]],
            ["Source intervention end", interval["end"]],
        ]
        timing_rows += [
            [f"Detector confirmation: {key}", timestamp]
            for key, timestamp in context["detector_confirmations_utc"].items()
        ]
    null_count = sum(s["expected_power"] is None for s in review["series"]["samples"])
    research_metrics = []
    for identifier, label in [
        ("episode_recall", "Retrospective intervention detection"),
        ("healthy_alarm_runs_per_hour", "Selected detector false-alarm rate"),
    ]:
        m = metrics.get(identifier)
        if m:
            ratio = m.get("ratio")
            if m["availability"] != "estimated":
                value = f"Unavailable — {_e(m['reason'])}"
            elif identifier == "episode_recall" and ratio:
                value = (
                    f"{ratio['numerator']:g} / {ratio['denominator']:g} documented interventions"
                )
            else:
                value = f"{m['value']:.5f} {_e(m['unit'])}"

            research_metrics.append(
                f'<article><h3>{label}</h3><p>{value}</p><p class="small">{_e(m["population"])}</p>'
                + (
                    f'<p class="small">{_e(ratio["numerator"])} {_e(ratio["numerator_unit"])} / {_e(ratio["denominator"])} {_e(ratio["denominator_unit"])}</p>'
                    if ratio
                    else ""
                )
                + "</article>"
            )
    uncertainty = deviation.get("uncertainty") if deviation else None
    uncertainty_html = "<p>No model-error band was supplied for this metric.</p>"
    if uncertainty:
        bounds = (
            "Unavailable"
            if uncertainty["lower"] is None or uncertainty["upper"] is None
            else f"{uncertainty['lower']:.6f}–{uncertainty['upper']:.6f} {_e(uncertainty['unit'])}"
        )
        uncertainty_html = f"<h3>Empirical matched-placebo model-error context</h3><p>{bounds} · {_e(uncertainty['group_count'])} groups.</p><p>{_e(uncertainty['method'])}</p>{_list(uncertainty['limitations'])}"
    metric_appendix = []
    labels = {
        "observed_energy": "Measured target AC energy",
        "expected_energy": "Model-expected target AC energy (not raw reference Pg)",
        "signed_generation_deviation": "Signed model-expected minus measured deviation (not causal loss or recovery)",
        "positive_only_generation_deviation": "Positive-only model-expected minus measured deviation (not recoverable energy)",
    }
    for m in review["metrics"]:
        value = (
            _v2_cell(m["value"])
            if m["availability"] == "estimated"
            else f"Unavailable — {m['reason']}"
        )
        metric_appendix.append(
            f'<article class="metric-definition"><h3>{_e(labels.get(m["id"], m["id"].replace("_", " ")))}</h3><p class="exact-value">{_e(value)} {_e(m["unit"])}</p>{_structured(m)}</article>'
        )
    measurement_rows = [
        [
            s["timestamp"],
            s["measured_power"],
            s["raw_reference_power"],
            s["expected_power"],
            "valid" if s["valid"] else "invalid",
        ]
        for s in review["series"]["samples"]
    ]
    appendix = (
        _report_details(
            "Full metric definitions, values and populations",
            "".join(metric_appendix),
            appendix=True,
        )
        + _report_details(
            "Calibration, provenance, checksums and verification scope",
            _structured(review["provenance"]),
            appendix=True,
        )
        + _report_details(
            "Original event context, scientific decision and approval scope",
            f"<p>Research verdict (experiment/capability scope): {_e(decision['verdict'])}</p>"
            + _v2_rows(
                ["Field", "Recorded value"],
                [
                    ["Event review availability", decision["event_review"]["availability"]],
                    ["Event review state", decision["event_review"]["state"]],
                    ["Event review reason", decision["event_review"]["reason"]],
                ],
            )
            + _structured(
                {
                    "schema_version": review["schema_version"],
                    "approval_status": review["approval_status"],
                    "review_id": review["review_id"],
                    "experiment": experiment,
                    "decision": decision,
                }
            ),
            appendix=True,
        )
        + _report_details(
            "Electrical evidence — contextual observations",
            _structured(review["electrical_evidence"]),
            appendix=True,
        )
        + _report_details(
            "Original measurement table — all retained records",
            "<p>Measured target AC power and raw comparison-inverter power are measurements. Model-expected target power is a calibrated estimate. Unavailable cells remain null, never zero.</p>"
            + _structured({k: v for k, v in review["series"].items() if k != "samples"})
            + _v2_rows(
                [
                    "Timestamp (UTC)",
                    "Measured target AC power",
                    "Raw comparison-inverter power",
                    "Model-expected target power",
                    "Sample validity",
                ],
                measurement_rows,
            ),
            appendix=True,
        )
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<meta name="color-scheme" content="light"><title>SolarLoss evidence report · {_e(experiment["identifier"])}</title>
<style>{V2_REPORT_CSS}</style></head><body><main>
<header id="executive-summary"><div class="masthead"><p class="brand">☼ SolarLoss</p><p class="eyebrow">Evidence report · {_e(experiment["identifier"])}</p></div>
<p class="eyebrow">A · Executive summary</p><h1>{_e("Documented shading: evidence & next checks" if experiment["type"] == "documented_shading" else "Recorded generation: evidence & context")}</h1>
<p class="intro">{observation} This comparison does not establish a physical cause or recoverable electricity.</p>
<p class="window"><strong>Analysis window (UTC):</strong> {_e(event_window)}<br><strong>Source:</strong> University of La Réunion · Graillet et al. · pinned Zenodo record 7291380, v2<br><strong>Intervention / context:</strong> {_e(event_label)}</p>
<dl class="figures">{figure("observed_energy", "Measured energy")}{figure("expected_energy", "Model-expected energy")}{figure("signed_generation_deviation", "Signed modelled deviation", True)}<div class="coverage"><dt>Supported coverage</dt><dd>{support}<br><small>observed labelled seconds</small></dd></div></dl>
<p class="small">Full supported event totals, unchanged by chart presentation. Positive signed deviation means expected above measured. Exact values and populations are retained in Part E.</p>
<div class="status-grid"><div><p class="eyebrow">Research validation</p><h3>{_e(decision["verdict"])}</h3><p class="small">Retrospective evidence from one installation. The selected detector's healthy false-alarm rate exceeded its frozen limit.</p></div><div><p class="eyebrow">Event-level decision</p><h3>{_e(decision["event_review"]["availability"].capitalize())}</h3><p class="small">The target line's true unshaded output was not observed; reference, operating-state and sensor alternatives remain unresolved.</p></div></div>
<p class="notice">{_e(warning)}</p></header>
<section id="evidence"><p class="eyebrow">B · Evidence</p><h2>The measured comparison</h2><p>Measured target AC power, calibrated expected target power and raw reference inverter power are separate channels. Expected power is an estimate, not a second measurement.</p>
<div class="legend"><span><i class="line"></i>Measured target</span><span><i class="line expected"></i>Model-expected target</span><span><i class="line reference"></i>Raw reference</span></div>
{render_power_chart(review)}
<p class="small">{null_count:,} unavailable expected-power samples remain gaps. Recorded measured channels remain available where supplied. {("The intervention band comes from source labels; the vertical line marks the primary detector confirmation." if experiment["type"] == "documented_shading" else "No shading intervention is annotated in this zero-labelled comparison.")}</p>
{_table(["Recorded timing", "UTC timestamp"], timing_rows) if timing_rows else ""}
<p class="small">Supported coverage: {support} observed labelled seconds. Wall span: {_e(coverage.get("wall_span_seconds"))} seconds. No generation deviation is assigned to unsupported time.</p></section>
<section id="investigation"><p class="eyebrow">C · Suggested investigation</p><h2>Information to gather next</h2><p>These are proposed investigation prompts, not diagnoses. They do not issue repair instructions or infer a cause. Electrical and array tests require qualified PV personnel and the site's safety plan.</p>{"".join(checks) if checks else "<p>No candidate checks were supplied.</p>"}</section>
<section id="confidence"><p class="eyebrow">D · Scientific confidence & limitations</p><h2>What the evaluation supports</h2><div class="research-metrics">{"".join(research_metrics)}</div>{_list(decision["reasons"])}<div class="model-error">{uncertainty_html}</div><h3>Interpretation boundaries</h3>{_list(review["limitations"])}</section>
<section id="technical-appendix"><p class="eyebrow">E · Technical appendix</p><h2>The complete evidence record</h2><p class="print-note">All {len(measurement_rows):,} retained measurement rows and full scientific values are embedded below. Expand sections in the browser to inspect them. Long appendices are omitted from the default print layout; keep this HTML with the printed summary for the complete audit record.</p>{appendix}</section>
<footer><p class="small">SolarLoss · Evidence review for solar performance. Review {_e(review["review_id"])}. Self-contained HTML; no external assets or scripts required.</p></footer>
</main></body></html>"""


def render_review_report(
    review: dict[str, Any],
    *,
    allow_experimental_v2: bool = False,
    allow_approved_v2: bool = False,
) -> str:
    """Render v0.1 by default; render v0.2 only through an explicit offline or approved gate."""
    if review.get("schema_version") == "0.2.0":
        if not allow_experimental_v2 and not allow_approved_v2:
            raise InvalidArtifact(
                "v0.2 reports require explicit experimental rendering or the approved production schema gate"
            )
        is_approved = review.get("approval_status") == "owner_approved"
        if allow_approved_v2 and not is_approved:
            raise InvalidArtifact(
                "Production v0.2 reports require an owner-approved review artifact"
            )
        return render_experimental_v2_report(review, owner_approved=is_approved)
    if review.get("schema_version") != "0.1.0":
        raise InvalidArtifact(
            f"Unsupported review schema version: {review.get('schema_version')!r}"
        )
    return _render_v1_review_report(review)
