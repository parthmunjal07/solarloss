# Exploratory detector comparison — Phase 3

**Recommendation:** reference-only OLS is the best next candidate to test prospectively among these four, but no candidate is selected or validated by this retrospective comparison. The V2 weather-assisted detector remains the frozen historical detector and its research verdict remains LIMIT.

## Frozen objectives and exploratory status

The operating objective is at most 0.05 alarm runs per supported zero-labelled hour, while preserving grouped intervention-episode recall, short-event sensitivity, detection latency, eligible coverage, and stability across time and operating strata. These goals are fixed before reading a future independent evaluation. The V2 protected results have already been inspected; therefore every new comparison on these records is exploratory. No threshold, model, cadence, or persistence choice made here is a fresh confirmatory result.

The comparison was run on committed V2 five-minute measurements and summaries. The raw source bytes were absent from this checkout, so this is a reproducible analysis of committed processed evidence, not a fresh run from the original raw files.

## Same-support comparison

All candidates share 1,312 zero-labelled calibration windows for thresholding and the identical strict later population of 22,015 eligible zero-labelled five-minute windows, equivalent to 1,794.5067 supported hours. Each model uses a 99th-percentile calibration residual threshold and two consecutive eligible threshold-exceeding windows. Ridge uses alpha 1.0, fixed without tuning on the inspected later outcomes, and feature scaling fit only on frozen training data.

| Candidate | Calibration threshold (W) | Later alerts | Supported hours | Runs/hour | Point budget result | Grouped shading episodes detected | Median latency |
|---|---:|---:|---:|---:|---|---:|---:|
| Reference OLS | 34.8034 | 78 | 1,794.5067 | 0.04347 | Below 0.05 | 23/23 | 297 s |
| Huber | 34.9624 | 80 | 1,794.5067 | 0.04458 | Below 0.05 | 23/23 | 297 s |
| Weather OLS | 30.4838 | 153 | 1,794.5067 | 0.08526 | Above 0.05 | 23/23 | 297 s |
| Weather Ridge alpha 1 | 30.8069 | 175 | 1,794.5067 | 0.09752 | Above 0.05 | 23/23 | 297 s |

All four candidates detected all 23 retrospectively known, long shading episodes. There were no episodes of 30 minutes or less, so short-event sensitivity is unavailable. Equal recall here does not distinguish candidates. Because the labels, days, and weather regime are from one installation, and because the protected outcomes are known, neither the 23/23 recall nor the point budget result validates future performance.

Separately, on the broader 24,320-row common score population, weather OLS has lower MAE than reference OLS (13.034 versus 13.574 W), but higher mean positive residual and a heavier upper residual tail. Keep prediction MAE distinct from alarm performance; see DETECTOR_ERROR_ANALYSIS_V3.md.

### Candidate disposition

- **Reference-only OLS — advance to prospective comparison.** It has the best common-set alarm point estimate while retaining the observed historical episode detections. Its original V2 day-bootstrap rate interval, 0.03495–0.05444/hour, crosses the 0.05 budget, so even the existing uncertainty does not establish that the budget is met.
- **Huber — retain as a robustness comparator.** Its common-set alert rate is close to reference OLS and below the point budget; no meaningful superiority is established.
- **Weather OLS — retain as a prediction comparator, not detector winner.** It has lowest pooled MAE, but exceeds the alarm budget on the identical detector support. Investigate sensor/reference and temporal residual mechanisms before reconsidering.
- **Weather Ridge alpha 1 — reject this specific exploratory setting for next-candidate status.** Its common-set alert rate is highest. This does not reject Ridge generally or other regularization strengths; no broad hyperparameter search was undertaken.
- **Nonlinear models — do not add yet.** The evidence identifies residual-tail, time, and operating-stratum issues, but no adequately isolated failure showing that a more complex model will fix them. First resolve measurement integrity, baseline drift, operating-state exclusions, and independent labels.
- **Window length and persistence — no new selection.** V2's 15-minute weather sensitivity result had 37 alarm runs / 1,623.928 supported hours (0.02278/hour) and detected all known events, but window-duration alternatives were exposed to the same inspected outcomes. The 1-, 5-, and 15-minute historical comparisons are sensitivity evidence only.

These are GO/LIMIT/REJECT recommendations about what to study next, not production approvals. Overall detector generalization and a new operational winner remain **LIMIT**; universal physical diagnosis remains **REJECT**.

## Evaluation that could genuinely confirm a detector

Use a locked, prospective evaluation on a new installation, or a time period collected after model and protocol lock with no preselection review of its outcomes. A new site is stronger because a later interval at the same installation does not test site transfer.

Before collecting or opening evaluation labels:

1. Publish a protocol version and hashes for model code, preprocessing, features, permitted model family, fit dates, thresholding rule, window duration, persistence, gap resets, eligibility, alert grouping, and all primary estimands.
2. Define the supported-hour denominator and data-quality rules for every candidate. Use identical eligibility where scientifically appropriate; report candidate-specific coverage and exclusions if missing sensors make full intersection impractical.
3. Train and calibrate only on designated earlier clean-operation data. Define “clean” using reviewed maintenance/inverter logs and independent operations records. Avoid using detector-selected alerts to define healthy calibration.
4. Freeze the alarm budget and a primary model before opening the held-out period. For multiple candidates, specify a training/selection set and retain the final site or time block entirely untouched for one final comparison.
5. Collect timestamped interventions and independently adjudicated clean periods, ideally with technician records, photos or inspection evidence, inverter state/curtailment/outage records, string-level information where available, and weather-sensor calibration history. Do not treat an anomaly score or an experimental intervention label alone as physical fault truth.
6. Score supported-hour alarm runs, event-group recall, confidence intervals grouped by day and site, detection latency, coverage, short-event recall with adequate short events, and residual calibration by season, time, irradiance, temperature, and reference-power strata. Include false negative review and unresolved labels.
7. For site transfer, keep all windows from each evaluation installation together. Do not randomly split highly correlated windows across train and test.

For decisions near the 0.05/hour limit, predeclare an uncertainty rule: report a site/day-clustered interval and require the upper bound to meet the product target if the intended claim is “at most 0.05/hour.” The existing V2 OLS interval crossing that line demonstrates why a point estimate alone is not enough.

## External data suitability

[NREL PVDAQ public datasets](https://data.openei.org/submissions/4568) include system metadata, performance time series, and environmental sensors for some systems. Their existence does not guarantee timestamped shading/fault ground truth, target/reference comparability, complete operating-state records, clean-operation labels, sensor calibration history, or compatible measurement cadence. The current PVDAQ v3 API is decommissioned; use the published OEDI data lake and documentation rather than assuming old API examples still work. Review site-specific metadata, licensing, gaps, label semantics, inverter/system changes, and all channels before inclusion. PVDAQ is a discovery source, not a prequalified validation cohort.

The preferred next step is a prospective instrumented installation with stable calibrated measurements, fully timestamped operations and interventions, and independent technician adjudication. If a PVDAQ system satisfies those exact checks, it can be a separately described external validation set. Do not pool a convenient site with SolarLoss until measurement and label semantics have been audited.

## Artifacts

The executed code is src/solarloss_research/detector_diagnostics_v3.py with a command wrapper at tools/run_detector_diagnostics_v3.py. Tests are in tests/test_phase3_v3.py. Results, tables, and plots are in results/detector_diagnostics_v3/. Reproduce with:

    python analysis/tools/run_detector_diagnostics_v3.py

The output status explicitly says exploratory because the protected V2 outcomes were inspected.
