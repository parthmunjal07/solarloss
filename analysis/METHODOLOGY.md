# Scientific methodology and limitations

## Estimand and interpretation

The primary estimand is the measured inverter-1 AC power deviation from a healthy-period expected-power reference during the dataset's documented shading labels. A positive value means expected power exceeds observed target power. Both signed deviation and positive-only shortfall are integrated and reported. Positive-only shortfall is a descriptive production difference for the sampled interval; it is not a counterfactual repair yield, causal repair attribution, or verified commercial energy recovery.

## Data preparation

1. Download the exact Zenodo record files and verify published file sizes and MD5 digests.
2. Audit raw rows in chunks. Parse source timestamps with their explicit offset and convert to UTC.
3. Exclude duplicate timestamps and malformed-time rows from modeling, but report their counts. Pair inverter streams only on exact one-to-one timestamps; do not interpolate unmatched electrical records.
4. Form nonoverlapping five-minute bins for model fitting and held-out error summaries. Retain raw paired timestamps for episode grouping and elapsed-time energy integration.
5. Define daylight model bins as those with mean reference AC power at least 100 W. This is a predeclared data-support filter, not a fault threshold.
6. Keep every bin containing any nonzero `Fault` value out of model fitting. Unknown labels and missing labels are not considered healthy.

## Chronological experimental design

Sort observed local calendar days and split entire days chronologically into 60% training, 20% validation, and 20% held-out evaluation. No randomly shuffled rows or overlapping windows are used. Train and validation fitting and selection use only healthy, daytime bins. Validation chooses between predeclared candidates. The final 20% is untouched for held-out healthy scores, placebo behaviour, and any documented experimental episodes that fall within it. An episode that begins before the held-out window is excluded in full, rather than clipped into a partial episode.

This boundary is based on chronology, not on observed experimental labels. If the held-out period contains too few independent experimental episodes, the pipeline reports that limitation and does not move the boundary after inspecting labels.

For descriptive effect estimation, the frozen model is also applied to documented shading episodes that begin after the training period, including episodes in the validation calendar window. Their labels are never predictors and are not used for healthy-period model selection or threshold setting. Such validation-window episode estimates are explicitly exploratory because the model's selection used healthy observations from the same calendar window. The primary `supported_change` rule uses only episodes in the final held-out test window. If that window has no shading episodes, the pipeline reports the post-training estimates separately and returns `insufficient_evidence` for held-out shading performance; it does not move the test boundary.

## Baselines and candidate models

- **Capacity-normalized ratio:** target prediction = reference power multiplied by target/reference nameplate capacity ratio. Because the paper's prose and module table disagree, both documented capacity ratios are evaluated in the audit, with the Table 1 arithmetic ratio used as the primary simple baseline.
- **Calibrated linear:** ordinary least squares predicting target AC power from reference AC power. Fit on healthy training bins only.
- **Robust linear:** Huber regression with epsilon 1.35 and alpha 0.0001, included only when there are at least 500 healthy training bins.
- **Weather-assisted linear:** only considered when GTI, DTI, and ambient-temperature summaries each cover at least 80% of nominal 1 Hz measurements within a bin, and usable weather features exist for at least 90% of healthy validation bins. Field means use non-null field-specific counts. The metadata image names the diffuse measurement DHI; the CSV header uses DTI, which is the actual field parsed. Module temperature is excluded because the target module may be affected by shading. The weather data are streamed and binned rather than loaded as a 1.5 GB table in memory.

Huber is considered appropriate only when at least 500 healthy training bins exist and more than 1% of healthy training OLS residuals exceed four robust MAD scales. Selection starts from the fixed Table 1 capacity-ratio baseline and proceeds in order through calibrated linear, Huber, and weather-assisted linear. Each more complex candidate replaces the current simpler selection only if its healthy-validation MAE is at least 5% lower on common validation bins. The held-out test set never selects models or thresholds. Every candidate is evaluated on the same held-out healthy bins available to it. Day-cluster bootstrap intervals for held-out error scores resample whole local calendar days; adjacent days may remain serially dependent.

## Error, effect, and uncertainty

- Held-out healthy MAE is in W. nMAE is MAE divided by the mean observed target AC power in W. Calibration bias is the mean prediction-minus-observation residual in W.
- The detection floor is the 95th percentile of positive mean residuals across nonoverlapping healthy validation one-hour blocks with at least six daylight five-minute bins. It is frozen before held-out labels are evaluated.
- Shading labels are grouped into one intervention episode when consecutive nonzero-label samples are no more than 300 seconds apart. Zero-label pauses remain unshaded and are not integrated as shading. Episode grouping and sensitivity can be inspected in the generated results.
- For each episode, integrate adjacent fault-labelled exact pairs with the trapezoidal rule using the observed elapsed seconds. Do not interpolate over gaps. Integration intervals longer than three observed median sample intervals are excluded. Signed net deviation and positive-only shortfall use the same valid intervals.
- Estimate uncertainty for experimental effects by resampling whole separated episodes (5,000 bootstrap replicates, fixed seed). Never treat 5-second rows as independent. With fewer than two episodes, no interval is produced; with fewer than ten, any interval is marked exploratory. Between-episode independence remains an assumption, so the interval is not a population guarantee. Held-out healthy error-score uncertainty is separately summarized with a whole-local-day bootstrap.
- Placebo false-shortfall behaviour is measured on held-out healthy nonoverlapping one-hour blocks using the validation-frozen detection floor. It is descriptive because hours may still be serially dependent.
- Missingness sensitivity simulates deletion of six consecutive observed 5-minute held-out healthy bins only when timestamps are exactly 300 seconds apart. With fixed random seeds, it rescores both the capacity-ratio baseline and frozen selected model without refitting. These are explicitly synthetic sensitivity experiments and do not replace measured missingness audit results.

## Reference stability and fallback

Screen healthy daylight capacity-normalized target/reference ratios by calendar month. A relative range of monthly medians greater than 15%, or fewer than two represented months, flags the comparison as unstable/insufficient. This screen is not proof that inverter 2 is healthy. If the reference fails this screen, the weather-assisted model can be used only if its aligned coverage and held-out calibration pass the same evaluation. Otherwise the fallback is a descriptive capacity ratio and the decision is `insufficient_evidence`; the pipeline does not force a reference-based alarm.

## Decision rules (version 0.1.0)

- **`insufficient_evidence`**: fewer than 10 held-out healthy days; selected-model held-out feature coverage below 80%; test nMAE above 20%; absolute held-out bias above 10% of mean target power; no sufficiently covered shading episode in the final test window; or unstable reference without a valid weather fallback.
- **`supported_change`**: all evidence-quality checks pass; at least three independent episodes in the final held-out test window have valid intervals; the episode-cluster 95% interval lower bound exceeds zero; and mean episode positive-only shortfall exceeds the frozen validation detection floor.
- **`inconclusive`**: data and calibration are adequate, but the episode count, uncertainty interval, or detection-floor criterion does not support `supported_change`.

Every decision includes reasons, exclusions, the rule version, limitations, and data-quality findings. These rules distinguish a measured deviation from a physical diagnosis.

## Weather overlap

The meteorological file is optional for execution but is streamed when available. Weather values are summarized in the same nonoverlapping five-minute bins. A weather model is suppressed unless at least 90% of validation healthy bins have both adequate weather-bin coverage and all three selected predictors. The report gives the resulting coverage and exact data interval. Weather coverage or availability is not assumed from the publication cadence alone.

## Scope limits

This is a single La Réunion experimental rooftop installation with nonidentical inverter/module lines. The results do not establish Indian-site performance, commercial fleet accuracy, plant-wide degradation, root cause, intervention recovery, or maintenance benefit. Small numbers of separated experiments and temporal dependence limit inferential strength. All thresholds are explicit and are not selected after inspecting held-out experimental labels.
