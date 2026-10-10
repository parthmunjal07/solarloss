# Detector error analysis — Phase 3

**Status:** retrospective exploratory analysis. The V2 protected outcomes were already inspected. This analysis does not alter the V2 protocol, frozen model, or historical results and is not confirmatory evidence.

## Question and source scope

The V2 weather-assisted OLS had lower later-period pooled MAE than reference-only OLS, yet more false-alarm runs: 153/1,794.5067 supported hours (0.08526/hour) versus 80/1,800.6033 hours (0.04443/hour). The frozen operational limit is at most 0.05 runs per supported zero-labelled hour.

The new diagnostics use the committed five-minute table, the committed V2 evaluation JSON, and frozen V2 model inputs. They do not reread the approximately 1.99 million original raw measurement rows. The input and reconstruction checks are recorded in results/detector_diagnostics_v3/detector_diagnostics_v3.json. The two populations below are deliberately kept separate:

1. Prediction-error comparison: 24,320 later-period rows scored where every candidate prediction is available.
2. Detector comparison: 22,015 identical eligible zero-labelled windows, 1,794.5067 supported hours, after intersecting quality, reference-domain, expected-power, and weather-coverage rules across all four candidates.

This follows the [Sandia/PVPMC model-validation procedure](https://pvpmc.sandia.gov/model-validation/model-validation-procedure/): report basic error, inspect residual distributions and conditions, then compare with a baseline. PVPMC also emphasizes consistent timestamps and scrubbed environmental and measured data ([validation overview](https://pvpmc.sandia.gov/model-validation/)).

## Direct comparison

### Prediction error on 24,320 common later-period rows

| Candidate | MAE (W) | RMSE (W) | Mean signed residual (W) | 95th percentile residual (W) | 99th percentile residual (W) | Positive residual share |
|---|---:|---:|---:|---:|---:|---:|
| Reference OLS | 13.574 | 24.449 | +3.770 | 28.252 | 62.467 | 58.40% |
| Huber | 13.700 | 24.585 | +4.322 | 28.631 | 62.019 | 60.95% |
| Weather OLS | 13.034 | 24.022 | +5.425 | 28.690 | 69.361 | 63.06% |
| Weather Ridge, alpha 1 | 13.230 | 24.155 | +5.239 | 29.696 | 68.822 | 59.90% |

Weather OLS reduces pooled MAE by 0.540 W (3.98%) relative to reference OLS, but its residual mean is 1.655 W more positive and its 99th percentile is 6.894 W higher. MAE is symmetric in residual sign and does not describe the positive tail that the one-sided underproduction detector thresholds.

### Alert outcomes on the strict shared detector population

The following thresholds were calibrated separately from the same 1,312 zero-labelled calibration windows using the same rule, then applied with two consecutive five-minute threshold exceedances. Counts and rates use the same 22,015 later zero-labelled windows and 1,794.5067 supported hours.

| Candidate | Threshold (W) | Healthy alert runs | Runs/hour | Alert windows above threshold | Episodes detected |
|---|---:|---:|---:|---:|---:|
| Reference OLS | 34.803 | 78 | 0.04347 | 239 | 23/23 |
| Huber | 34.962 | 80 | 0.04458 | 240 | 23/23 |
| Weather OLS | 30.484 | 153 | 0.08526 | 380 | 23/23 |
| Weather Ridge, alpha 1 | 30.807 | 175 | 0.09752 | 423 | 23/23 |

The weather OLS threshold is 4.320 W below the reference OLS threshold. The new recalibrated reference OLS point estimate is below 0.05/hour; its original V2 day-bootstrap 95% interval is 0.03495–0.05444/hour and crosses the budget. The new strict common-set rates do not have bootstrap intervals. These facts support a reference OLS prospective test, not promotion to a winning detector.

The comparison code uses the committed weather OLS aggregate stream for that candidate and reconstructs the other candidates from committed five-minute input means. Candidate eligibility and threshold support are common. These implementation details and the small difference from original frozen V2 thresholds are recorded in the JSON. This analysis must not replace the original V2 outcome.

## When errors occur

The excess alerts concentrate in the upper positive tail and in several time periods, not in a uniformly worse average fit.

- By month, weather OLS has later-period mean residuals of +12.21 W in April, +10.55 W in May, +9.69 W in June, and +7.57 W in July. Its corresponding alert rates are 0.0612, 0.1995, 0.1455, and 0.1933 runs/hour. The reference OLS rates are lower in those months (0.0283, 0.1197, 0.0926, and 0.1400), but still elevated in May–July. The recurring months implicate a time-varying model or operating condition, not uniquely a weather feature.
- By local hour, the weather OLS mean residual reaches +20.61 W at 07:00 and remains +14.96 W at 08:00, versus +11.93 W and +8.47 W for reference OLS. For 06:00, weather is +7.44 W while reference OLS is −3.64 W. This pattern can increase early-day one-sided exceedances.
- By GTI fifths, weather OLS mean residual is +8.36 W and +9.40 W in the second and third irradiance strata, and +3.58 W in the highest stratum. Reference OLS is +8.56 W and +9.74 W in those middle strata, but −2.00 W in the highest. Weather does not uniformly reduce bias by irradiance condition.
- In the lowest ambient-temperature fifth (16.17–24.57 °C), weather OLS bias is +13.38 W versus +7.98 W for reference OLS. These are descriptive strata from the same retrospective record; they are not independent experiments.
- Reference-power fifths show positive bias for both models in the middle operating range. At the top reference-power fifth, reference OLS is −3.04 W and weather OLS +1.71 W.

The monthly, hour, GTI, ambient-temperature, and reference-power tables and their plots are in results/detector_diagnostics_v3/. Diagnostic figures are descriptive; the bins are not hypothesis tests.

## Weather-feature stability and measurement limits

The weather model's training period contains 2,958 eligible bins. Training GTI and raw reference power have Pearson correlation 0.99596. In the four-predictor design, variance inflation factors are approximately 127.85 for reference power and 128.32 for GTI, compared with 1.07 for DTI and 1.57 for ambient temperature. Weather-only VIFs look modest because the weather-only calculation omits reference power, the highly correlated predictor.

Weather OLS coefficients also shift across two descriptive halves of training days: the GTI coefficient changes from 0.07397 to 0.03603 W per GTI unit, while ambient-temperature coefficient changes from −0.374 to −0.496 W/°C. This is evidence of coefficient sensitivity and redundancy, not proof that the features are physically invalid. Ridge alpha 1 reduces coefficient instability in principle but the tested Ridge candidate does not satisfy the alert budget here.

Data checks report exact timestamp pairing for the source electrical channels, a median pairing difference of 6 seconds, and a maximum source gap of 2,848,806 seconds. Weather begins later than electrical data, and the frozen training/weather-eligible coverage is smaller than reference-only coverage. The strict common detector comparison prevents weather missingness from creating a favorable or unfavorable denominator by itself. It does not cure sensor calibration problems, representativeness of site weather, reference-inverter changes, curtailment, clipping, outages, or unlogged maintenance. A monthly target/reference median ratio range of 1.455% is only a co-stability screen; neither inverter has independent row-level fault truth.

## What explains the alert difference?

**Supported arithmetic:** the weather candidate uses a lower calibrated threshold, has a larger positive later residual mean and heavier 99th-percentile positive tail, exceeds its threshold in more eligible windows (380 versus 239), and forms more two-window alarm runs (153 versus 78). These facts explain why the detector alarms more often despite a lower pooled MAE.

**Not established:** this data does not identify whether the residual pattern is caused by irradiance-sensor calibration or placement, reference-inverter drift or mismatch, clipping, curtailment, temperature response, cloud-edge gradients, inverter availability, or an actual target-system change. These remain competing hypotheses. No one mechanism should be shown as a diagnosis.

## Energy-deviation uncertainty audit

The V2 event-energy method integrates actual elapsed time across consecutive original target records. It requires source-row adjacency, valid model and measurement support, both endpoints inside the label, and no interval longer than 18 seconds. Positive-only deviation clips negative endpoint residuals before integration; signed deviation preserves direction. Event wall span, observed labelled support, and valid integration seconds remain different denominators.

The matched-placebo method selects contiguous calibration blocks of comparable duration within 20% tolerance in comparison-inverter Pg and GTI, without overlap, requiring at least five blocks on at least three calibration days. It uses calibration-only data. Ten of 23 episodes met that adequacy gate: shading_01, shading_02, shading_04, shading_08, shading_09, shading_19, shading_20, shading_21, shading_22, and shading_23. The other thirteen did not meet the gate; their placebo result is unavailable, not zero. Event durations range from 6,175 to 40,159 seconds. Across labelled episodes, V2 reports minimum and median observed coverage of 82.52% and 95.59%.

For shading_01, measured energy is 2.381649 kWh, expected energy 2.778698 kWh, signed deviation +0.397049 kWh, and positive-only deviation +0.397126 kWh. The empirical placebo signed-energy 2.5th percentile, median, and 97.5th percentile are 0.002243, 0.019188, and 0.026907 kWh. Subtracting those same-design placebo percentiles from the event value yields +0.394806, +0.377861, and +0.370142 kWh. Thus the event-minus-placebo result moves by 0.024664 kWh across this percentile choice. The exported [0.370142, 0.394806] kWh span is a non-simultaneous empirical model-error band, not a confidence interval for unshaded counterfactual generation or causal loss.

The matching blocks are not guaranteed independent: repeated days at one installation share weather, instruments, and system state; nearby days may be serially dependent. Day-block bootstrap intervals in V2 describe uncertainty for the stated resampled statistic under that design, not missing counterfactual measurements. The V2 files do not preserve the full set of matched candidate blocks needed to rerun several alternative Pg/GTI tolerances and matching rules in this Phase 3 checkout. Consequently, no alternative-match sensitivity is claimed. A future energy analysis should preserve matched block IDs and scores, predeclare tolerance grids and block exclusion rules, report coverage and matched-day counts for each event/design, and show the full distribution alongside signed and positive-only values.

**Conclusion:** event deviation is a reproducible measured-versus-modelled comparison with empirical model-error context for ten events. It is not exact counterfactual energy loss, recovered electricity, savings, or proof of physical cause. The project-level E3 verdict remains LIMIT.

## Outputs and reproducibility

Run the diagnostics from the repository root with the V2 runtime requirements and matplotlib installed:

    python analysis/tools/run_detector_diagnostics_v3.py

The JSON records input hashes, source availability, population reconstruction checks, fitting periods, thresholds, results, event latency, and the exploratory-only status. Tables and plots are materialized beside it in results/detector_diagnostics_v3/. The committed raw data were not available for a new complete raw-row rerun.
