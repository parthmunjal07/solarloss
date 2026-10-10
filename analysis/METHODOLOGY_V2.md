# Scientific methodology v2

The estimand is expected healthy inverter1 AC power minus measured inverter1 AC power under a frozen model calibrated against nonidentical inverter2 and optional weather. A residual is a modelled comparison, not directly measured counterfactual production. Prior v1 findings remain historical. EXPERIMENT_PROTOCOL_V2.md controls this retrospective evaluation; its SHA256 is stored with the parameters and results. No random splits, test-label predictor use, refit on future healthy observations or protected threshold tuning occurs.

## Processing and quality

Download/reuse the pinned four files after byte-count/MD5 verification; compute streaming SHA256. Audit all CSV rows, nulls, numeric ranges, labels, offsets, actual time intervals and source gaps. Parse explicit +04:00 offsets into UTC; local Indian/Reunion days determine boundaries. Pair inverter timestamps exactly one-to-one, excluding duplicates/malformed times. Unknown Fault values are never healthy; documented decimal categories recover from float32 representations only within 1e-6 of a known code. Regression tests retain unknown labels.

Five-minute modelling means require reference>=100 W, nonnegative finite AC measurements, >=80% supported elapsed seconds and known zero labels. Weather is streamed with count-weighted recombination at chunk boundaries; each feature's non-null count must cover >=80% of 1Hz nominal records. No preprocessing statistic is fitted on protected data. TPV remains descriptive because shading can affect module temperature. Both published capacity ratios are reported; a calibrated relationship is an empirical alternative, not proof either capacity is correct.

Training, selection and detector calibration use separate whole local days before February8. Progressive >=5% common-population healthy-selection MAE improvements select OLS/Huber/weather against fixed ratios. Thresholds use only signed residual means from healthy calibration; 1/5/15-minute statistics each use their own 99th percentile and two-window persistence. The primary remains 5min. Window-end confirmation timestamps prevent backdated alarms. Missing windows reset persistence. Reference support limits come from training predictor percentiles and do not establish reference health. Later healthy monthly ratios and calibration errors describe stability without changing selection.

## Evaluation units

Physical labels are grouped at <=300-second nonzero separation, retaining zero-label pauses. Episode recall denominator includes all documented groups and separately adequately covered groups. Confirmations must occur within episode spans. Latency is elapsed time from first label to automatic confirmation. Alarm runs/evaluated healthy elapsed hours are distinct from window alert fraction and TP/FN/FP/TN. Precision is conditional on the eligible labelled window population; no event precision is constructed from unlike counts. Boundary alerts with mixed supporting labels are unassigned. 60/900-second grouping and 1/15min detection are predeclared sensitivity results, not alternative selected winners.

## Energy and uncertainty

For adjacent original records, integrate r=(expected-observed) using sum[0.5*(r_i+r_j)*(t_j-t_i)]/3,600,000 in kWh. Both endpoints must be eligible and fault-labelled; 0<dt<=18s; original row adjacency must hold. No zero-label pause or removed-record gap is bridged. Signed deviation and positive-only endpoint-truncated deviation use the same intervals. Positive truncation has nonnegative healthy bias; a positive-only interval above zero is rejected as an abnormality test. Linear zero-crossings of a residual are approximated by endpoint truncation and cannot be treated as exact rectified waveforms.

Report actual/expected energy, valid seconds, observed labelled support seconds and wall span separately. Weather-assisted raw predictions use five-minute environmental means, so second-level effect resolution is not independently validated. Matched healthy calibration placebos use only predictor conditions (20% Pg2/GTI), contiguous windows of comparable duration, >=5 blocks and >=3 days. Signed error distributions produce an empirical model-error band, not a confidence interval for causal loss. Bands are not multiplicity-adjusted; no significance claims are made. Day-resampling bootstrap intervals for average event energy/recall and healthy calibration/alarm rates reduce within-day dependence, but serial dependence across days and one site's repeated setup remain.

## Electrical and scientific limits

Training reference-power deciles define Va/Ia/Vg/Ig/Fg target-minus-reference envelopes; post-prediction matched comparisons are descriptive. See electrical matrix for sensor meanings and confounding. No target DC variable feeds the AC detector. There is no intervention/maintenance ground truth, universal fault label set, independent reference-health truth or observed unshaded inverter1 during shading. Therefore counterfactual-magnitude accuracy, cause diagnosis, maintenance recovery, fleet performance and finance remain unproven. E3/E4 are LIMIT even where observations are useful.

## Verification

Tests cover float32 labels, unknowns, exact elapsed integration, gaps/zero pauses/deleted records, signed-versus-positive bias, unavailable energy, predictor independence from labels, persistence/confirmation timestamps, frozen reference support and exporter/schema semantics. All charts derive from reusable CSV/JSON measurements. Execute the notebook and CLI using README_V2.md; execution records disclose local CPU execution and environment-specific Colab branches. Schema v0.2 remains a proposal and no production review artifact is fabricated.
