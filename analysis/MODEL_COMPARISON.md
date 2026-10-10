# Model comparison and evaluation results

Produced at 2026-10-09T18:59:14Z from checksum-verified Zenodo record bytes. Analysis version 0.1.0.

## Data and split

- Exact inverter timestamp intersection: **1,990,478 / 1,990,478** rows (100.0%); no duplicates or unmatched timestamps.
- Chronological observed-local-day split: train 2021-10-01–2022-06-12 (181 days), validation 2022-06-13–2022-08-31 (60 days), held-out 2022-09-01–2022-10-31 (61 days).
- Healthy daylight bins: train 17,746; validation 6,149; held-out 7,139.
- Observed electrical median interval: 6.0 s; publication cadence is 5 s. Maximum interval is 2,848,806 s, so the mean interval is not a representative cadence.
- Weather overlap: {"all_feature_coverage": 0.9712046711739397, "all_model_weather_features_present_bins": 31603, "electrical_daylight_bins": 32540, "method": "Weather rows streamed into five-minute bins; a bin and each model feature require at least 80% of the documented 1 Hz nominal cadence. Field means use each field's non-null samples. The model uses actual CSV fields GTI, DTI, and ambient temperature only. The record's metadata image calls the diffuse field DHI; the CSV header is DTI.", "weather_bin_coverage": 0.9712046711739397, "weather_covered_bins_at_80pct_of_nominal_1hz": 31603, "weather_end_utc": "2022-10-31T19:55:00+00:00", "weather_start_utc": "2021-10-28T12:35:00+00:00"}

## Candidate scores

MAE and bias are in W; nMAE divides MAE by mean observed target AC power. Validation scores select models; held-out scores are reported after model selection.

| Candidate | Validation healthy | Held-out healthy | Held-out day-block 95% MAE interval |
|---|---:|---:|---:|
| calibrated_linear | n=6149, MAE=14.975 W, nMAE=0.0182, bias=-0.917 W | n=7139, MAE=12.556 W, nMAE=0.0155, bias=-3.342 W | [12.141, 12.984] W |
| huber_reference | n=6149, MAE=14.723 W, nMAE=0.0179, bias=0.387 W | n=7139, MAE=12.095 W, nMAE=0.0149, bias=-2.096 W | [11.685, 12.534] W |
| weather_assisted_linear **(selected)** | n=6149, MAE=14.017 W, nMAE=0.0170, bias=-3.687 W | n=7139, MAE=11.510 W, nMAE=0.0142, bias=-5.161 W | [11.114, 11.932] W |
| capacity_table_arithmetic | n=6149, MAE=62.939 W, nMAE=0.0764, bias=54.010 W | n=7139, MAE=56.710 W, nMAE=0.0699, bias=50.094 W | [54.190, 58.944] W |
| capacity_paper_prose | n=6149, MAE=23.517 W, nMAE=0.0285, bias=8.508 W | n=7139, MAE=18.213 W, nMAE=0.0224, bias=5.451 W | [17.468, 18.965] W |

### Progressive validation comparisons

Each candidate was compared with the current simpler model on identical common validation bins. The 5% improvement gate was fixed before held-out evaluation.

| Candidate | Compared with | Common bins | MAE improvement | Gate passed |
|---|---|---:|---:|---|
| calibrated_linear | capacity_table_arithmetic | 6,149 | 76.21% | True |
| huber_reference | calibrated_linear | 6,149 | 1.68% | False |
| weather_assisted_linear | calibrated_linear | 6,149 | 6.39% | True |

Selected model: **weather_assisted_linear**.

- Features: reference_power_w, GTI, DTI, TA.
- Training rows: 16,819; preprocessing: Five-minute healthy daylight means; rows with any selected feature missing are excluded; no scaling or imputation.
- Parameters: {}.
- Intercept: 20.000667 W; coefficients: {"DTI": -0.0416843313753731, "GTI": 0.040923397528831944, "TA": 0.3755271961347922, "reference_power_w": 0.9072514887188557}.
- Training dependencies: numpy, pandas, scipy, scikit-learn; exact versions are pinned in requirements.txt.

Held-out day-block intervals resample whole local calendar days (2,000 replicates per candidate). Adjacent days may be serially dependent; intervals are exploratory and do not establish universal superiority. Selection did not use held-out scores.

## Experimental shading estimate

- **No experimental shading shortfall is estimable** in the post-training evaluation window. Estimate fields remain null; no value is imputed.
- Final held-out shading episodes: 0; signed energy=None; positive-only energy=None; uncertainty interval=None.
- Grouped episodes excluded from post-training estimation: 23. Grouping joins nonzero labels separated by at most 300 seconds; zero-label pauses are not integrated.

| Episode start (UTC) | End (UTC) | Labels | Labeled samples | Exclusion |
|---|---|---|---:|---|
| 2022-02-08T07:11:02+00:00 | 2022-02-08T10:09:56+00:00 | 2.1 | 2148 | Episode begins before the frozen model's post-training evaluation window; excluded from the primary post-training estimate. |
| 2022-02-09T06:58:01+00:00 | 2022-02-09T10:22:55+00:00 | 2.2 | 2460 | Episode begins before the frozen model's post-training evaluation window; excluded from the primary post-training estimate. |
| 2022-02-11T07:05:04+00:00 | 2022-02-11T11:38:55+00:00 | 2.3 | 3287 | Episode begins before the frozen model's post-training evaluation window; excluded from the primary post-training estimate. |
| 2022-02-14T07:30:03+00:00 | 2022-02-14T11:41:55+00:00 | 1 | 3018 | Episode begins before the frozen model's post-training evaluation window; excluded from the primary post-training estimate. |
| 2022-02-15T06:50:04+00:00 | 2022-02-15T11:34:56+00:00 | 1 | 3300 | Episode begins before the frozen model's post-training evaluation window; excluded from the primary post-training estimate. |
| 2022-02-17T05:20:01+00:00 | 2022-02-17T13:34:49+00:00 | 4 | 5936 | Episode begins before the frozen model's post-training evaluation window; excluded from the primary post-training estimate. |
| 2022-02-18T02:24:28+00:00 | 2022-02-18T11:49:56+00:00 | 4 | 6785 | Episode begins before the frozen model's post-training evaluation window; excluded from the primary post-training estimate. |
| 2022-02-24T06:35:00+00:00 | 2022-02-24T09:44:55+00:00 | 3.2 | 2280 | Episode begins before the frozen model's post-training evaluation window; excluded from the primary post-training estimate. |
| 2022-03-01T05:58:01+00:00 | 2022-03-01T07:40:56+00:00 | 3.2 | 1236 | Episode begins before the frozen model's post-training evaluation window; excluded from the primary post-training estimate. |
| 2022-03-09T04:49:02+00:00 | 2022-03-09T13:45:14+00:00 | 4 | 6426 | Episode begins before the frozen model's post-training evaluation window; excluded from the primary post-training estimate. |
| 2022-03-10T05:24:07+00:00 | 2022-03-10T14:15:49+00:00 | 4 | 6372 | Episode begins before the frozen model's post-training evaluation window; excluded from the primary post-training estimate. |
| 2022-03-11T02:35:48+00:00 | 2022-03-11T12:04:55+00:00 | 4 | 6819 | Episode begins before the frozen model's post-training evaluation window; excluded from the primary post-training estimate. |
| 2022-03-15T04:53:03+00:00 | 2022-03-15T14:20:18+00:00 | 4 | 5424 | Episode begins before the frozen model's post-training evaluation window; excluded from the primary post-training estimate. |
| 2022-03-16T02:56:58+00:00 | 2022-03-16T14:03:58+00:00 | 4 | 5704 | Episode begins before the frozen model's post-training evaluation window; excluded from the primary post-training estimate. |
| 2022-03-17T02:40:32+00:00 | 2022-03-17T13:49:51+00:00 | 4 | 6311 | Episode begins before the frozen model's post-training evaluation window; excluded from the primary post-training estimate. |
| 2022-03-18T02:32:43+00:00 | 2022-03-18T11:49:56+00:00 | 4 | 5549 | Episode begins before the frozen model's post-training evaluation window; excluded from the primary post-training estimate. |
| 2022-03-25T06:18:01+00:00 | 2022-03-25T11:42:58+00:00 | 4 | 3245 | Episode begins before the frozen model's post-training evaluation window; excluded from the primary post-training estimate. |
| 2022-04-19T06:27:04+00:00 | 2022-04-19T10:59:58+00:00 | 4 | 2726 | Episode begins before the frozen model's post-training evaluation window; excluded from the primary post-training estimate. |
| 2022-04-25T07:22:04+00:00 | 2022-04-25T09:27:58+00:00 | 3.2 | 1258 | Episode begins before the frozen model's post-training evaluation window; excluded from the primary post-training estimate. |
| 2022-04-27T05:20:05+00:00 | 2022-04-27T07:51:59+00:00 | 3.2 | 1518 | Episode begins before the frozen model's post-training evaluation window; excluded from the primary post-training estimate. |
| 2022-05-10T05:45:06+00:00 | 2022-05-10T07:43:54+00:00 | 3.1 | 891 | Episode begins before the frozen model's post-training evaluation window; excluded from the primary post-training estimate. |
| 2022-05-16T05:46:03+00:00 | 2022-05-16T07:49:55+00:00 | 3.1 | 928 | Episode begins before the frozen model's post-training evaluation window; excluded from the primary post-training estimate. |
| 2022-05-19T05:43:00+00:00 | 2022-05-19T07:42:52+00:00 | 3.1 | 898 | Episode begins before the frozen model's post-training evaluation window; excluded from the primary post-training estimate. |

No held-out shading comparison means the decision remains **insufficient_evidence**. Earlier experimental intervals are not used to move the chronological test boundary.

## Healthy-period checks

- Held-out selected-model calibration: n=7139, MAE=11.510 W, nMAE=0.0142, bias=-5.161 W; selected-model coverage=100.0%; validity=True.
- Reference stability: stable_by_predeclared_screen; monthly normalized ratio relative range=0.0113 (predeclared limit 15%). This is not proof that inverter 2 is healthy.
- Held-out healthy placebo: {"false_shortfall_blocks": 7, "false_shortfall_rate": 0.011647254575707155, "limitations": "Placebo blocks are serially dependent and are not independent Bernoulli trials; the rate is descriptive and uses a threshold fixed on healthy validation blocks.", "mean_signed_residual_w": -5.113757618433256, "population": "held-out healthy nonoverlapping 1-hour blocks; at least six complete 5-minute daylight bins", "status": "evaluated", "threshold_w": 12.815414272240444, "valid_placebo_blocks": 601}.
- Missingness sensitivity (synthetic): {"findings": [{"capacity_baseline_change_from_complete_mae_w": -0.19636396865645622, "complete_capacity_baseline_mae_w": 56.70966181677241, "complete_selected_model_mae_w": 11.509810302242265, "mean_capacity_baseline_mae_w": 56.513297848115954, "mean_retained_coverage": 0.8995937806415464, "mean_selected_model_mae_w": 11.555546882331319, "repeats": 20, "selected_model_change_from_complete_mae_w": 0.0457365800890539, "synthetic_missing_fraction_requested": 0.1}, {"capacity_baseline_change_from_complete_mae_w": -0.638275173690559, "complete_capacity_baseline_mae_w": 56.70966181677241, "complete_selected_model_mae_w": 11.509810302242265, "mean_capacity_baseline_mae_w": 56.07138664308185, "mean_retained_coverage": 0.7496007844235887, "mean_selected_model_mae_w": 11.611635216547564, "repeats": 20, "selected_model_change_from_complete_mae_w": 0.10182491430529872, "synthetic_missing_fraction_requested": 0.25}], "method": "Deterministic-seed simulation deleting six consecutive observed 5-minute held-out healthy bins only where timestamps are exactly 300 seconds apart; the capacity-normalized baseline and frozen selected model are rescored on identical retained bins without refitting.", "note": "This sensitivity experiment is synthetic and does not represent the measured missingness process.", "status": "evaluated", "synthetic": true}.

## Decision

State: **insufficient_evidence** (solarloss-decision-rules-0.1.0).

- No evaluable post-training labelled shading episode is present; 23 grouped episode(s) were excluded before the frozen evaluation window.
- Post-training validation-period episodes, when present, do not establish held-out shading performance.
- Fallback considered: none.

These results describe a La Réunion experimental installation. They do not establish physical cause, repair attribution, commercial recovery, Indian-site performance, or general model accuracy.
