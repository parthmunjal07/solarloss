# Experiments E1–E4 — final retrospective report

## E1: Can an entirely pre-shading fit/selection/calibration design run?

Dataset: checksum-verified pinned La Réunion files; 1,990,478 exact electrical pairs. First physical event2022-02-08T07:11:02UTC. Method: observed whole RET days split60/20/20 before the entire first event day; conservative elapsed coverage screens; zero-known labels only; no future fitting. Baseline: original v1 train through June 12 and held-out September 1–October 31 had zero shading events. Actual revised populations:

| Population | Local dates (RET) | Valid bins | Days | Weather bins |
|---|---|---:|---:|---:|
| train | 2021-10-01 to 2021-12-11 | 3796 | 37 | 2958 |
| selection | 2021-12-12 to 2022-01-25 | 1327 | 13 | 1322 |
| calibration | 2022-01-26 to 2022-02-07 | 1441 | 13 | 1441 |

All 23 physical episodes remain protected; later healthy samples are separate stability evidence. The feasibility gate passes500 training bins and100selection/calibration bins over10 days each. **GO for retrospective feasibility.** Failure modes: substantial missing calendar spans and weather beginningOctober28 reduce usable training; the 33-day gap cannot be repaired by interpolation. Limitations: prior dataset knowledge informed boundaries; neither prospective untouched evaluation nor reference truth is claimed. Support: frozen protocol, feasibility_v2.json, frozen_parameters_v2.json, source/exact-alignment and separation tests.

## E2: Can the residual detector separate documented shading and zero-labelled operation?

Population:23 physical groups on23 days plus 22,015 usable later zero-labelled5 min windows across 235 days. Method: weather-selected coefficients; signed99th healthy-calibration quantile=30.484 W; two consecutive eligible windows; frozen predictor-domain and gap screens; confirmation at window end. Labels enter evaluation after prediction, not detector inputs. All models have separately early-calibrated thresholds; no protected reselection.

Actual outcome:23/23 recall; adequately covered denominator=23; no misses. Latency minimum/median/maximum=58/297/4082 s. Two-window persistence denotes two fixed statistics; onset windows may partially overlap an event, so latency can be shorter than10 minutes. Healthy false alarms=153/1794.507h=0.08526/h. Baseline OLS23/23 with0.04443/h. Calibration-period primary alarms=3/107.495 h; later rate rises. The selected estimator's later healthy MAE=13.034 W,nMAE=1.608%,bias=+5.425 W. Model calibration is not detector accuracy.

Window confusion (different units):TP1196,FN167,FP380,TN21633; 2 mixed-support boundary alerts excluded. Precision=75.89% only in this eligible labelled window population. No episode precision denominator is manufactured.

| Code | Physical groups | Detected | Missed |
|---|---:|---:|---:|
| 1 | 2 | 2 | 0 |
| 2.1 | 1 | 1 | 0 |
| 2.2 | 1 | 1 | 0 |
| 2.3 | 1 | 1 | 0 |
| 3.1 | 3 | 3 | 0 |
| 3.2 | 4 | 4 | 0 |
| 4 | 11 | 11 | 0 |

Predeclared1 min and15 min sensitivity results:{'1': {'detected': 23, 'episodes': 23}, '5': {'detected': 23, 'episodes': 23}, '15': {'detected': 23, 'episodes': 23}}; their healthy rates are separately reported in JSON. 15 min reduces alert-run rate but cannot be selected as a protected winner. 60 s grouping yields25 groups,300/900s23. Events share the same aging installation; adjacent days/procedures are not verified independent. The day-bootstrap recall diagnostic [1,1] is degenerate and cannot establish a population lower bound. Healthy rate95% day-bootstrap interval=[0.07187926961388573, 0.09978005359354448]; temporal dependence may understate uncertainty. **LIMIT**, because0.08526/h exceeds the frozen0.05/h gate. Failure modes: positive residual drift, season/reference behaviour, mixed onset windows, short/intermittent effects, feature/domain/gap exclusions and unknown true no-fault operation. Support: shading_evaluation_v2.json, monthly_stability_v2.csv, event CSV, baseline comparison, calibration-only threshold and label-independence tests.

## E3: Can meaningful episode deviation and uncertainty be estimated?

Population:23eligible labelled episodes; observed labelled coverage minimum/median=82.52/95.59%;10 events meet matched-placebo adequacy. Method: frozen raw-pair expected power; actual elapsed trapezoids on consecutive original records, both eligible/labelled,dt<=18 s; no healthy-pause or removed-row bridging. Expected-minus-measured signed energy and endpoint-truncated positive energy are separate. Match predictor-only calibration blocks by duration and20%Pg2/GTI; whole-day resampling for error context. Reject positive-only-above-zero significance.

Demo shading_01: measured2.381649 kWh,expected2.778698 kWh,signed0.397049 kWh,positive-only0.397126 kWh; 10549/10734supported labelled seconds. Baseline matched healthy median false signed energy at event duration=0.019188 kWh; event-minus-placebo median=0.377861 kWh. Empirical error band=[0.37014211825708937, 0.3948064694632774]kWh, based on10 blocks/7 days. These are model-error comparisons, not causal-counterfactual confidence bounds.

All eligible signed deviations sum to33.030132 kWh, strictly descriptive and not independent recoverable loss. Mean event signed energy day-bootstrap range=[0.995212556964498, 1.9607351098588002]kWh; it characterizes observed event variation, not uncertainty of a total commercial loss. Healthy example2022-01-26T03:00:03+00:00–2022-01-26T03:59:58+00:00: signed0.012293 kWh,positive-only0.015578 kWh. A positive healthy shortfall illustrates the truncation problem. Measured missing-data gap2848806 s gets null energy.

**LIMIT.** Large signed demo deviation exceeds matched healthy error, but true unshaded target output is not observed. Failure modes: counterfactual mismatch, reference anomalies, five-minute weather reused at raw cadence, scarce long matched placebos, non-simultaneous error bands, nonrandom interventions and sensor uncertainty. Support: measured demo CSV, episode metrics/JSON, examples, methodology, independently recomputed demo energy and gap/positive-bias tests. No repair, recovered electricity or financial claim is supported.

## E4: Do voltage/current signals add investigation context?

Population: training healthy bins define reference-Pg decile envelopes; protected event bins and later healthy bins provide descriptive comparisons. Method: synchronized target-minus-reference Va/Ia/Vg/Ig/Fg, healthy2.5–97.5% envelopes, predictor-only20%Pg2/GTI and5 C matching. No target electrical predictor in the automatic AC detector; no row-wise significance or universal classifier.

Actual demo observations: Va median target/reference=154.617/175.608 V; matched change=-24.546 V;84.38% outside training envelope. Ia matched change=-0.0550 A, with9.38% outside; Ig matched change=-0.6442 A reflects AC-output change. Vg/Fg observations do not independently establish a grid fault. Per-event and later healthy numbers are in JSON and the matrix; no diagnosis accuracy is claimed.

**LIMIT** for descriptive technician context; **REJECT** universal fault diagnosis. Baseline comparisons condition on production/irradiance and show operating-point departures; incremental held-out diagnostic benefit is not validated. Failure modes: temperature/MPPT/inverter-state confounding, nonidentical arrays, unknown sensor precision, temporal dependence and absent string-level/fault-state truth. Missing IV/string/inverter-status/independent irradiance data prevent narrowing to a unique cause. Support: ELECTRICAL_EVIDENCE_MATRIX.md, electrical observations/chart, training-frozen envelopes and label-independent detector tests.

## E5 and integration

INVESTIGATION_GUIDANCE_PROPOSAL.md provides bounded candidate checks with observations, hypotheses, opposing evidence, missing next information, qualification constraints and primary NREL/IEA/Sandia/OEM-sensor references. Implementability: evidence display after owner review; diagnosis engine and commercial outcomes REJECT. SCHEMA_FEEDBACK_V2.md describes approved future integration steps, explicit unavailable-null semantics and identity correction. Backend/frontend/infra remain unchanged. No production-compatible artifact is fabricated to satisfy v0.1 numeric energy.

Execution/test/reproducibility support: all four source-byte checks, actual row audits, frozen protocol hash, pinned direct dependencies and executed runtime versions;27 automated mechanics/schema tests; independent arithmetic verification; locally executed CPU notebook. Local execution does not imply remote Colab Drive/upload branches were run. Preserve all original v1 notebook/result bytes. REVISION_LOG_V2.md discloses post-result visualization fixes without tuning.
