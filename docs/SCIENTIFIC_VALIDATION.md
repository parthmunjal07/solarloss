# Scientific validation and claim limits

This page summarizes the committed v2 retrospective study. It is not a certification of a deployed detector. The detailed protocol, result tables, and provenance are in [`analysis/EXPERIMENT_PROTOCOL_V2.md`](../analysis/EXPERIMENT_PROTOCOL_V2.md), [`analysis/EXPERIMENT_REPORT_V2.md`](../analysis/EXPERIMENT_REPORT_V2.md), [`analysis/EXECUTIVE_SUMMARY_V2.md`](../analysis/EXECUTIVE_SUMMARY_V2.md), and [`analysis/DATA_PROVENANCE.md`](../analysis/DATA_PROVENANCE.md).

## Dataset and comparison design

The study uses the pinned version 2 of the [La Réunion residential PV dataset](https://zenodo.org/records/7291380), attributed to Graillet et al., [*Data in Brief* 46 (2023), 108723](https://doi.org/10.1016/j.dib.2022.108723). The system and intervention context are described by Lebreton et al., [*Entropy* 24(9) (2022), 1311](https://doi.org/10.3390/e24091311). Dataset license and file-level checksums are recorded in [`DATA_PROVENANCE.md`](../analysis/DATA_PROVENANCE.md); the source data is licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

One inverter line is the target with documented shading interventions. A second, nonidentical line supplies a comparison signal; healthy-period calibration maps it to expected target output. The two lines are not independent replicates, and the comparison line is not a direct measurement of the target's unshaded output. The model also uses GTI, DTI, and ambient temperature. Training uses pre-event healthy periods; intervention labels are excluded from prediction and reserved for retrospective evaluation.

The selected model is `weather_assisted_linear`, implemented with scikit-learn `LinearRegression` on five-minute means. Its features are reference power, GTI, DTI, and ambient temperature. Thresholds and evaluation windows were frozen in the committed protocol before protected episode scoring. The experiment is offline; there is no live inference or deployed model service.

## Reported results

- The selected five-minute detector retrospectively flagged **23 of 23 documented physical shading episodes**, on 23 intervention days, at this one installation. Simple baselines also flagged all 23. This is not a fleet accuracy estimate, prospective sensitivity, or a general 100% detection claim.
- The selected detector produced **153 healthy alert runs over 1,794.5067 supported healthy hours**, or **0.08526 runs per healthy hour**. The frozen limit is **0.05 per hour**, so the detector's research verdict is **LIMIT**. The day-bootstrap interval is exploratory and does not remove temporal-dependence concerns.
- For `shading_01`, the signed expected-minus-measured modelled deviation is **0.39704898 kWh**; the positive-only integral is **0.39712615 kWh**. Supported labelled observations cover **10,549 of 10,734 seconds (98.28%)**. These values are estimates relative to a modelled expected stream, not recovered electricity or verified causal loss.
- The `shading_01` empirical model-error band is approximately **0.37014–0.39481 kWh**, based on 10 blocks across 7 days. It is not a counterfactual-loss confidence interval. Only 10 of 23 episodes have adequate matched-placebo support.
- Voltage and current comparisons provide operating context only. They do not diagnose shading, an inverter fault, or a grid fault. The technician investigation guidance remains proposed and unapproved.

These reported figures are sourced from [`shading_evaluation_v2.json`](../analysis/results/shading_evaluation_v2.json), [`example_cases_v2.json`](../analysis/results/example_cases_v2.json), [`demo_measured_series_v2.csv`](../analysis/results/demo_measured_series_v2.csv), and the reports linked above. The offline verifier recomputes selected arithmetic from committed outputs; it does not rerun the original dataset download or experiment.

## What the study does not establish

SolarLoss cannot currently claim:

- general fault-detection accuracy, prospective operating performance, or transfer to other sites;
- verified shading loss, recoverable energy, financial savings, or repaired production;
- an independently validated diagnosis from voltage/current observations or technician guidance;
- long-term degradation, panel ageing, soiling diagnosis, or a root cause for a production difference;
- that an anomaly in one stream is a physical fault rather than reference behaviour, weather, operating state, curtailment, or measurement error.

The healthy false-alarm rate exceeds its predeclared target. All 23 documented events are on the same installation and are not independent replications. There are limited matched placebos, nonidentical inverter lines, temporal dependence, and no independently observed unshaded target output. These limits are retained in the research report and must accompany any presentation of the result.

## Review decisions and schema status

An event-level review decision describes the supplied artifact. A research-level GO/LIMIT/REJECT verdict describes an experiment criterion. They answer different questions and must not be merged.

The current review-serving schema is v0.1.0 and its scientific semantics are provisional. Schema v0.2.0 remains a proposal. Do not serve it or label it owner-approved until Rachit approves its metric definitions and the open questions documented in the [science/backend integration review](phase-3-scientific-v2-integration.md). No new artifact or scientific result is created by this documentation pass.
