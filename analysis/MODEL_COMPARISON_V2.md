# Model comparison v2 — actual rerun

Selected **weather_assisted_linear** using pre-event healthy selection only. Weather improved common-selection MAE by 9.07%; Huber improved by only 0.15% and failed the 5% replacement gate. Selected weather training uses 2,958 bins; OLS/Huber use 3,796. No refit with later healthy data.

| Model | Selection n / MAE W | Later common n / MAE W / bias W | Detected episodes | Healthy alarm runs/hour |
|---|---:|---:|---:|---:|
| capacity_table_arithmetic | 1327 / 48.709 | 24320 / 60.584 / 53.198 | 23/23 | 0.10885 |
| capacity_paper_prose | 1327 / 16.564 | 24320 / 21.756 / 8.441 | 23/23 | 0.06331 |
| calibrated_linear | 1327 / 9.077 | 24320 / 13.574 / 3.770 | 23/23 | 0.04443 |
| huber_reference | 1327 / 9.063 | 24320 / 13.700 / 4.322 | 23/23 | 0.04554 |
| weather_assisted_linear | 1322 / 8.261 | 24320 / 13.034 / 5.425 | 23/23 | 0.08526 |

Later common-weather comparison: 24,320 identical healthy bins; weather MAE 13.034 W versus OLS 13.574 W, a 3.98% descriptive improvement. Weather bias is +5.425 W versus OLS +3.770 W. All-candidate MAE and whole-local-day bootstrap diagnostics are in model_comparison_v2.json. No inferential superiority claim is made from overlapping intervals or selecting the smallest protected error.

Regression accuracy did not translate into the best detector. Weather's healthy alarm rate 0.08526/hour exceeds the frozen 0.05/hour gate; OLS has 0.04443/hour. All fixed/calibrated baselines detected all 23 episodes. This experiment supports simple residual screening; it does not establish that ML is necessary for these interventions. E2 remains **LIMIT** for the originally selected primary, and neither OLS nor the 15-minute sensitivity is promoted after seeing test outcomes.

Fixed capacity baselines use table arithmetic 2.10/2.04=1.029411765 (primary) and conflicting prose 2.04/2.09=0.976076555 (sensitivity). Neither is represented as an established true capacity ratio. Published capacities and observed behaviour are nonidentical. The calibrated relationship removes substantial offset/scale mismatch but does not make inverter2 an infallible ground truth.

Healthy calibration threshold 30.484 W is the 99th percentile of signed five-minute means; two consecutive eligible windows confirm. Calibration has 3 runs/107.495 h; later healthy has 153 runs/1794.507 h. Monthly stability numbers are in monthly_stability_v2.csv. Adjacent days, season and one common installation limit transfer. No test-derived retuning occurred.
