from html import escape
from typing import Any


def _e(value: Any) -> str:
    if value is None:
        value = "Not recorded"
    return escape(str(value), quote=True)


def _list(items: list[str], empty: str = "None recorded.") -> str:
    if not items:
        return f"<p>{_e(empty)}</p>"
    return "<ul>" + "".join(f"<li>{_e(item)}</li>" for item in items) + "</ul>"


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    head = "".join(f"<th scope=\"col\">{_e(item)}</th>" for item in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{_e(value)}</td>" for value in row) + "</tr>"
        for row in rows
    )
    if not body:
        body = f"<tr><td colspan=\"{len(headers)}\">No rows recorded.</td></tr>"
    return f"<div class=\"table-wrap\"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"


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


def render_review_report(review: dict[str, Any]) -> str:
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
        ["Energy deficit", metrics["energy_deficit"]["value"], metrics["energy_deficit"]["unit"], metrics["energy_deficit"]["calculation"]],
        ["Deficit fraction", metrics["deficit_fraction"]["value"], metrics["deficit_fraction"]["unit"], f"numerator {metrics['deficit_fraction']['numerator']['value']} {metrics['deficit_fraction']['numerator']['unit']}; denominator {metrics['deficit_fraction']['denominator']['value']} {metrics['deficit_fraction']['denominator']['unit']}"],
        ["Coverage", metrics["coverage"]["value"], metrics["coverage"]["unit"], f"numerator {metrics['coverage']['numerator']['value']} {metrics['coverage']['numerator']['unit']}; denominator {metrics['coverage']['denominator']['value']} {metrics['coverage']['denominator']['unit']}"],
        ["Calibration error", metrics["calibration_error"]["value"], metrics["calibration_error"]["unit"], f"{metrics['calibration_error']['statistic']}; held-out healthy data; denominator {metrics['calibration_error']['denominator']['value']} {metrics['calibration_error']['denominator']['unit']}"],
        ["Valid intervals", metrics["valid_interval_count"], "intervals", "As recorded in the review artifact"],
        ["Total intervals", metrics["total_interval_count"], "intervals", "As recorded in the review artifact"],
    ]
    baseline = review["baseline_comparison"]
    baseline_rows = [
        [baseline["simple_baseline"]["name"], baseline["simple_baseline"]["value"], baseline["unit"]],
        [baseline["calibrated_reference"]["name"], baseline["calibrated_reference"]["value"], baseline["unit"]],
    ]
    if "reported_difference" in baseline:
        baseline_rows.append([
            "Reported difference",
            baseline["reported_difference"]["value"],
            baseline["reported_difference"]["unit"],
        ])

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
        sample_rows.append([
            sample["timestamp"],
            sample["measured_power"],
            sample["raw_reference_power"],
            sample["expected_power"],
            sample.get("expected_lower_bound", ""),
            sample.get("expected_upper_bound", ""),
            "valid" if sample["valid"] else "invalid",
        ])

    quality_rows = [
        [check["name"], check["status"], check.get("result", ""), check["detail"]]
        for check in review["quality_checks"]
    ]
    exclusion_rows = [
        [item["start"], item["end"], item["reason"]]
        for item in review["exclusions"]
    ]

    placebo = review["placebo"]
    robustness = review["robustness"]
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>SolarLoss review {_e(experiment['identifier'])}</title>
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
    <p class="muted">SolarLoss evidence review · schema {_e(review['schema_version'])} · analysis {_e(review['analysis_version'])}</p>
    <h1>Experiment {_e(experiment['identifier'])}</h1>
    <p>Produced at {_e(review['produced_at'])}. Review id <code>{_e(review['review_id'])}</code>.</p>
    <p class="decision">{_e(decision['state'])}</p>
    <h2>Reasons recorded by the analysis</h2>
    {_list(decision['reasons'])}
  </header>

  <section><h2>Dataset provenance</h2>
    <p><strong>{_e(dataset['name'])}</strong> · version {_e(dataset['version'])}</p>
    <p>Source: <code>{_e(dataset['source'])}</code></p>
    <p>Extraction date: {_e(dataset.get('extraction_date', 'Not recorded'))}</p>
    {_table(['Checksum scope', 'Algorithm', 'Digest'], checksum_rows)}
  </section>

  <section><h2>Experiment</h2>
    <p>Type: {_e(experiment['type'])}</p>
    <p>Window: {_e(experiment['time_window']['start'])} to {_e(experiment['time_window']['end'])}</p>
    <p>Experimental system: {_e(experiment['experimental_system']['identifier'])} — {_e(experiment['experimental_system']['description'])}</p>
    <p>Reference system: {_e(experiment['reference_system']['identifier'])} — {_e(experiment['reference_system']['description'])}</p>
    <p>Label: {_e(experiment['label_provenance']['label'])}; source {_e(experiment['label_provenance']['source'])}; method {_e(experiment['label_provenance']['method'])}.</p>
    <p>Label reference: {_e(experiment['label_provenance'].get('reference', 'Not recorded'))}</p>
  </section>

  <section><h2>Metrics and calculation context</h2>
    <p>Power series unit: {_e(review['series']['power_unit'])}. Energy deficit calculation: values are presented as supplied by the analysis artifact.</p>
    {_table(['Metric', 'Value', 'Unit', 'Denominator / calculation context'], metric_rows)}
  </section>

  <section><h2>Baseline comparison</h2>
    <p>Metric: {_e(baseline['metric'])} ({_e(baseline['unit'])}); evaluation population: {_e(baseline['evaluation_population'])}.</p>
    {_table(['Method', 'Value', 'Unit'], baseline_rows)}
    <p>{_e(baseline.get('calculation', 'No comparison calculation detail recorded.'))}</p>
  </section>

  <section><h2>Uncertainty</h2>
    <p>Method: {_e(uncertainty['method'])}</p>
    <p>Independent blocks: {_e(uncertainty['independent_blocks']['count'])} {_e(uncertainty['independent_blocks']['unit'])}; exploratory: {_e(uncertainty['exploratory'])}.</p>
    <p>Interval: {_e(interval_text)}</p>
    <h3>Uncertainty limitations</h3>{_list(uncertainty['limitations'])}
  </section>

  <section><h2>Quality checks</h2>
    {_table(['Check', 'Status', 'Result', 'Detail'], quality_rows)}
    <h3>Excluded intervals</h3>
    {_table(['Start (UTC)', 'End (UTC)', 'Reason'], exclusion_rows)}
  </section>

  <section><h2>Robustness findings</h2>
    <p>Status: {_e(robustness['status'])}</p>{_findings(robustness['findings'])}
  </section>
  <section><h2>Placebo findings</h2>
    <p>Status: {_e(placebo['status'])}</p>{_findings(placebo['findings'])}
  </section>

  <section><h2>Limitations</h2>{_list(review['limitations'])}</section>

  <section><h2>Time series</h2>
    <p>Measured power is from the experimental system. Raw reference power is the uncalibrated reference measurement. Expected power is calibrated output derived from the reference. Values use {_e(review['series']['power_unit'])}; timestamps use {_e(review['series']['timestamp_basis'])}.</p>
    {_table(['Timestamp (UTC)', 'Measured experimental', 'Raw reference', 'Calibrated expected', 'Expected lower bound', 'Expected upper bound', 'Validity'], sample_rows)}
  </section>
</main>
</body>
</html>"""
