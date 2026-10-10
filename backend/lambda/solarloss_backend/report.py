import json
from html import escape
from typing import Any

from .errors import InvalidArtifact


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


def render_experimental_v2_report(review: dict[str, Any]) -> str:
    """Render proposed v0.2 content for local review; this is never an API report."""
    experiment = review["experiment"]
    provenance = review["provenance"]
    decision = review["decision"]

    metric_rows = []
    for metric in review["metrics"]:
        metric_id = metric["id"]
        label = {
            "healthy_mae": "Healthy model MAE",
            "healthy_nmae": "Healthy model nMAE",
            "healthy_bias": "Healthy model bias",
            "episode_recall": "Documented episode recall",
            "healthy_alarm_runs_per_hour": "Healthy alert runs per supported hour",
            "signed_generation_deviation": "Signed generation deviation",
            "positive_only_generation_deviation": (
                "Positive-only generation deviation (not recovered energy)"
            ),
            "observed_energy": "Measured energy",
            "expected_energy": "Model-expected energy",
        }[metric_id]
        value = (
            metric["value"]
            if metric["availability"] == "estimated"
            else f"Unavailable — {metric['reason']}"
        )
        metric_rows.append(
            [
                label,
                metric["availability"],
                value,
                metric["unit"],
                metric["population"],
                metric["definition"],
                metric["calculation"],
                metric["coverage"],
                metric.get("ratio"),
                metric.get("uncertainty"),
            ]
        )

    sample_rows = [
        [
            sample["timestamp"],
            sample["measured_power"],
            sample["raw_reference_power"],
            sample["expected_power"],
            "valid" if sample["valid"] else "invalid",
        ]
        for sample in review["series"]["samples"]
    ]
    electrical_rows = [
        [
            item["signal"],
            item["measurement"],
            item["unit"],
            item["quality"],
            item["comparison_population"],
            item["supports"],
            item["does_not_prove"],
            item["alternatives"],
            item["missing_measurements"],
            item["strength"],
        ]
        for item in review["electrical_evidence"]
    ]
    candidate_rows = [
        [
            item["id"],
            item["status"],
            item["observed_fact"],
            (
                "Suppressed because this candidate check is unavailable."
                if item["status"] == "unavailable"
                else item["hypothesis"]
            ),
            item["supporting_evidence"],
            item["opposing_evidence"],
            item["next_information"],
            item["qualification"],
            item["safety_constraint"],
            item["sources"],
        ]
        for item in review["candidate_checks"]
    ]
    checksum_rows = [
        [item["file"], item["md5"], item["sha256"]] for item in provenance["source_checksums"]
    ]
    provenance_rows = [
        ["Protocol SHA256", provenance["protocol_sha256"]],
        ["Model and features", provenance["model"]],
        ["Data splits", provenance["splits"]],
        ["Thresholds and windows", provenance["thresholds"]],
        ["Evaluation population", provenance["evaluation_population"]],
        ["Grouping", provenance["grouping"]],
        ["Label use", provenance["label_use"]],
        ["Exclusions", provenance["exclusions"]],
        ["Retrospective", provenance["retrospective"]],
        ["Code version", provenance["code_version"]],
        ["Decision owner-review record", decision["owner_review"]],
    ]

    approval_status = review["approval_status"]
    candidate_notice = (
        "Candidate checks below are proposed investigation prompts, not diagnoses. "
        "They do not issue repair instructions or infer a cause."
        if approval_status == "proposed"
        else "Candidate checks remain prompts; this experimental report does not turn them into diagnoses."
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
  <meta name="color-scheme" content="light">
  <title>SolarLoss experimental research report {_e(experiment["identifier"])}</title>
  <style>
    :root {{ color-scheme: light; font: 16px/1.5 system-ui, sans-serif; color: #18221d; background: #f5f7f5; }}
    body {{ margin: 0; }} main {{ max-width: 1180px; margin: 0 auto; padding: 2rem 1.25rem 4rem; }}
    header, section, .warning {{ background: #fff; border: 1px solid #dce4dd; border-radius: 12px; padding: 1.25rem; margin: 0 0 1rem; }}
    .warning {{ border: 2px solid #9b5b00; background: #fff8e8; font-weight: 650; }}
    h1, h2 {{ line-height: 1.2; }} h1 {{ margin: 0 0 .4rem; }} h2 {{ font-size: 1.2rem; margin-top: 0; }}
    .muted {{ color: #56635b; }} .decision {{ display: inline-block; border-radius: 999px; padding: .35rem .7rem; background: #edf2ee; font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; }} th, td {{ text-align: left; padding: .55rem .65rem; border-bottom: 1px solid #e4eae5; vertical-align: top; overflow-wrap: anywhere; }}
    th {{ background: #f4f7f4; }} .table-wrap {{ overflow-x: auto; }} code {{ overflow-wrap: anywhere; }}
    @media (max-width: 640px) {{ main {{ padding: 1rem .6rem 2rem; }} header, section, .warning {{ padding: .9rem; }} }}
  </style>
</head>
<body><main>
  <div class="warning"><strong>EXPERIMENTAL — PROPOSED CONTRACT.</strong> This local research report is not served by the production API. The results are retrospective and from one installation. They do not establish a diagnosis, recovered energy, or commercial savings.</div>
  <header>
    <p class="muted">SolarLoss evidence review · schema {_e(review["schema_version"])} · approval status {_e(approval_status)}</p>
    <h1>Experimental review: {_e(experiment["identifier"])}</h1>
    <p>Type: {_e(experiment["type"])}. Window: {_e(experiment["start"])} to {_e(experiment["end"])} UTC. Review id <code>{_e(review["review_id"])}</code>.</p>
    <p class="decision">Producer verdict: {_e(decision["verdict"])}</p>
    <h2>Reasons recorded by the analysis</h2>{_list(decision["reasons"])}
  </header>

  <section><h2>Metrics, availability, and coverage</h2>
    <p>Each value is displayed as supplied. Unavailable metrics remain null with their reason; the report does not convert missing values to zero.</p>
    {_v2_rows(["Metric", "Availability", "Value", "Unit", "Population", "Definition", "Calculation", "Coverage (seconds)", "Ratio numerator / denominator", "Uncertainty type and bounds"], metric_rows)}
  </section>

  <section><h2>Measured and model-expected time series</h2>
    <p>Measured experimental power, raw reference power, and model-expected power are separate series. A null cell means unavailable.</p>
    <p>Timestamp basis: {_e(review["series"]["timestamp_basis"])}. Power unit: {_e(review["series"]["power_unit"])}. Downsampling record: {_e(_v2_cell(review["series"]["downsampling"]))}</p>
    {_v2_rows(["Timestamp", "Measured experimental power", "Raw reference power", "Model-expected power", "Validity"], sample_rows)}
  </section>

  <section><h2>Electrical evidence — contextual observations</h2>
    <p>These measurements provide context only. They are not independent diagnoses or validated fault classifications.</p>
    {_v2_rows(["Signal", "Measurement", "Unit", "Quality", "Comparison population", "Supports", "Does not prove", "Alternatives", "Missing measurements", "Evidence strength"], electrical_rows)}
  </section>

  <section><h2>Technician candidate checks</h2>
    <p>{_e(candidate_notice)}</p>
    {_v2_rows(["Check", "Status", "Observed fact", "Candidate hypothesis", "Supporting evidence", "Opposing evidence", "Next information", "Qualification", "Safety constraint", "References"], candidate_rows)}
  </section>

  <section><h2>Research provenance</h2>
    {_v2_rows(["Item", "Recorded value"], provenance_rows)}
    <h3>Source checksums</h3>{_v2_rows(["File", "MD5", "SHA256"], checksum_rows)}
  </section>

  <section><h2>Research limitations</h2>{_list(review["limitations"])}</section>
</main></body></html>"""


def render_review_report(review: dict[str, Any], *, allow_experimental_v2: bool = False) -> str:
    """Render v0.1 by default; render proposed v0.2 only on explicit local opt-in."""
    if review.get("schema_version") == "0.2.0":
        if not allow_experimental_v2:
            raise InvalidArtifact(
                "Proposed v0.2 reports require explicit experimental rendering and are not served by the API"
            )
        return render_experimental_v2_report(review)
    if review.get("schema_version") != "0.1.0":
        raise InvalidArtifact(
            f"Unsupported review schema version: {review.get('schema_version')!r}"
        )
    return _render_v1_review_report(review)
