# Scientific contract decision register — Phase 3

**Status:** proposal for Rachit's scientific review. Nothing in this register records owner approval. The two v0.2 review JSONs remain `approval_status: proposed`; the data-gap case is a separate explicit unavailability record because the current type enum cannot represent it honestly.

## Decision register

### 1. Measured AC power, raw reference power, and expected target power

- **Current source definition:** V2 aligns inverter 1 and inverter 2 by exact UTC timestamp. `target_power_w` is inverter 1 measured AC grid-injected Pg. `reference_power_w` is inverter 2's separately measured raw Pg. The selected weather-assisted expected target power is a frozen healthy-period regression, not raw reference Pg. See `DATA_PROVENANCE.md`, `EXPERIMENT_PROTOCOL_V2.md`, `EXPERIMENT_REPORT_V2.md`, and `results/frozen_parameters_v2.json`.
- **Proposed definition:** expose three distinct W-valued fields: `measured_power` = target inverter measured AC Pg; `raw_reference_power` = comparison inverter measured AC Pg; `expected_power` = frozen calibrated healthy estimate for target inverter AC Pg conditional on recorded predictors. Residual polarity is expected minus measured. The expected series must never be described as a second measurement.
- **Justification:** the inverters are nonidentical and the paper has conflicting nameplate-capacity statements. Conflating expected target power with the raw comparison system would erase calibration and imply an observed counterfactual.
- **Required tests:** field-level tests for source/channel identity; expected-model recomputation on valid shared records; reject swapped target/reference values; assert that energy calculations use expected and target measured series, never raw reference as the target measurement.
- **Exporter/frontend/backend effect:** V3 exports all three separately. After approval, backend schema needs explicit channel and model semantics; frontend labels must say “measured target,” “raw comparison,” and “model-expected target.”
- **Status:** OWNER APPROVAL REQUIRED.

### 2. Signed and positive-only energy deviation

- **Current source definition:** V2 integrates trapezoids on consecutive original target records, actual elapsed UTC seconds, eligible endpoints, `0 < dt <= 18 s`, and both endpoints within the labelled event. Signed deviation is expected minus measured. Positive-only clips each endpoint residual at zero before the trapezoid; zero-crossing location is approximate. Historical `shading_01` values are 0.3970489774 kWh signed and 0.3971261454 kWh positive-only.
- **Proposed definition:** `signed_generation_deviation_kwh` is the signed time integral of (healthy expected target AC power − measured target AC power) over one declared population. Negative means measured exceeded expected. `positive_only_generation_deviation_kwh` applies `max(residual, 0)` at observed endpoints before integration. Neither is named loss, recovered electricity, savings, or causal effect.
- **Justification:** signed values preserve direction and positive-only values discard overproduction. Neither estimates recoverable energy without an identified counterfactual and intervention outcome.
- **Required tests:** sign reversal; negative signed value accepted; positive-only value nonnegative; energy identity reconciles with observed/expected integration within floating tolerance; gaps and zero-labelled pauses are never bridged; endpoint clipping is explicit.
- **Exporter/frontend/backend effect:** maintain separate metric ids and display names. The draft already separates the fields but needs stricter metric-scope and definition constraints and an explicit “not recoverable energy” rendering rule.
- **Status:** OWNER APPROVAL REQUIRED.

### 3. Energy integration population, valid duration, and coverage denominators

- **Current source definition:** event valid seconds are the sum of elapsed intervals that pass timestamp, source-row adjacency, feature/model eligibility, and label-boundary checks. The labelled denominator is elapsed source support between labelled target records, integrated under the same no-gap rule with eligibility disabled. Event wall span is the full recorded label duration. Healthy example support has 3,595 valid seconds; `shading_01` has 10,549 valid seconds / 10,734 observed labelled seconds = 98.2765%.
- **Proposed definition:** every energy metric records the same explicit `valid_seconds`; event metrics additionally record `observed_labelled_seconds`; and all interval metrics record `wall_span_seconds`. Coverage is `valid_seconds / observed_labelled_seconds` for labelled events; wall-span coverage is separately `valid_seconds / wall_span_seconds`. Healthy examples set labelled support to null, not to a fabricated label duration. Rates use their own explicit numerator and denominator, never the energy coverage object.
- **Justification:** source availability, model eligibility, label support, and event duration are different denominators. A single ambiguous “coverage” invites false comparison.
- **Required tests:** nonnegative finite seconds; valid seconds cannot exceed its relevant support; denominator identity is recorded; ratio equals numerator/denominator; no missing duration coerced to zero; interval populations align across observed, expected, and signed metrics.
- **Exporter/frontend/backend effect:** V3 records the three durations. v0.2 needs distinct labelled-support and wall-span coverage semantics or an explicit coverage object with denominator kind; frontend must present the denominator label next to any percentage.
- **Status:** OWNER APPROVAL REQUIRED.

### 4. Detection alerts versus retrospective intervention labels

- **Current source definition:** V2 alert confirmation is the end of the second consecutive eligible threshold-exceeding five-minute window; a missing or ineligible window resets persistence. Alert time is not backdated. `Fault` labels are used for known-zero restrictions, grouping, and retrospective evaluation only, never as detector input. `shading_01` label boundary begins at 07:11:02 UTC; primary five-minute confirmation is 07:20:00 UTC.
- **Proposed definition:** represent source intervention start/end and detector confirmation as different UTC fields, each with its own provenance and resolution. Alerts are algorithm outputs; labels are source annotations of experimental intervention. Grouped episodes use the frozen 300-second label gap rule, not alert-run boundaries.
- **Justification:** a detector timestamp cannot replace a physical intervention boundary or establish cause. Backdating hides latency.
- **Required tests:** label bounds differ from confirmation when data say so; no confirmation outside event can count as a hit; label column is absent from predictor input; threshold persistence resets at gaps; timestamps are strict UTC.
- **Exporter/frontend/backend effect:** V3 preserves both under event context. Proposed v0.2 currently lacks explicit, typed label interval and detector-confirmation fields; backend must add them after approval, and frontend must render label bands and alert markers separately.
- **Status:** OWNER APPROVAL REQUIRED.

### 5. Unavailable, not applicable, and not estimated

- **Current source definition:** V2 uses JSON `null` and a reason when the source interval lacks enough supported measurement; no interpolation is permitted. The outage example has a 2,848,806-second gap and no energy estimate.
- **Proposed definition:** use `availability=estimated` only for a finite calculated value, `unavailable` for an in-scope metric that cannot be calculated, and add `not_applicable` for a metric that is outside the case's scientific scope. In every state, a reason is mandatory except an estimated metric, whose reason is null. Never replace null with 0 or a narrative guessed value.
- **Justification:** zero is a measured numerical result; unavailable means not determined. Not-applicable distinguishes the two from each other.
- **Required tests:** unavailable and not-applicable values must be null; reasons nonempty; estimated values finite and reason null; renderers retain the reason and never display null as zero.
- **Exporter/frontend/backend effect:** V3 keeps the gap sidecar unavailable and does not force it into a shading/healthy enum. v0.2 has only estimated/unavailable and should add not-applicable plus an insufficient-data/data-gap case type. Frontend should say “not available for this interval” and state why.
- **Status:** OWNER APPROVAL REQUIRED.

### 6. Empirical model-error bands versus confidence intervals

- **Current source definition:** `shading_01` placebo evidence is based on ten calibration-only matched blocks across seven local days. The range 0.370142–0.394806 kWh is event signed deviation minus selected placebo signed-energy quantiles. It is non-simultaneous and is explicitly not a true-counterfactual confidence interval.
- **Proposed definition:** keep uncertainty type and estimand in the field: empirical matched-placebo model-error band, day-block bootstrap interval for the stated statistic, or not estimated. Include method, level when applicable, group count/unit, population, and limitations. Never label a placebo-derived range a confidence interval for causal loss.
- **Justification:** resampling blocks quantifies variation under the chosen model and matching design, not missing target-inverter counterfactuals.
- **Required tests:** paired finite ordered bounds; interval unit equals metric unit; `not_estimated` requires null bounds; empirical band cannot contain a `confidence_level` claim unless separately justified; renderer displays the type and limitations.
- **Exporter/frontend/backend effect:** V3 labels the `shading_01` band as `empirical_model_error_band`; v0.2 needs uncertainty kind/estimand/level rules and stronger cross-field validation.
- **Status:** OWNER APPROVAL REQUIRED.

### 7. Healthy/model evaluation populations

- **Current source definition:** healthy in V2 means known source `Fault=0`, quality-passing, supported daylight operation. It does not rule out an unrecorded fault. Training, selection, calibration, later stability, and matched placebos are different whole-day populations. The `2022-01-26` example is inside detector calibration.
- **Proposed definition:** every metric names its exact source label rule, time span, quality/model eligibility, denominator count/unit, and whether it was used for fitting, selection, threshold calibration, or protected scoring. Use “zero-labelled” where ground-truth health was not independently established. Never call a calibration interval an independent holdout.
- **Justification:** selection, calibration and later scores answer different questions; “healthy” can overstate label certainty.
- **Required tests:** period boundaries disjoint as frozen; counts and duration reconcile; metric population cannot refer to one split while using another; case-level example states calibration participation.
- **Exporter/frontend/backend effect:** V3 states the healthy example's calibration membership and zero-label caveat. Schema and frontend need structured population/split references rather than free-form strings alone.
- **Status:** OWNER APPROVAL REQUIRED.

### 8. Research GO/LIMIT/REJECT versus individual review state

- **Current source definition:** V2 project gates apply to an experiment/capability. Selected detector E2 is LIMIT because 0.08526 healthy alert runs/hour exceeds the frozen <=0.05/hour gate. E3 effect magnitude remains LIMIT. These are not event-level decisions.
- **Proposed definition:** retain `decision.verdict` only for the named experiment/capability gate and make its scope/version explicit. Event-level state is a separate tri-state field (`supported_change`, `inconclusive`, `insufficient_evidence`) with an explicit unavailable state before the gates are approved. Do not infer it from research verdict.
- **Justification:** one event can carry a measurable change while the detector/research capability remains LIMIT; the inverse is also possible.
- **Required tests:** schema rejects enum conflation; event state cannot be derived from `decision.verdict`; missing event evidence serializes as unavailable with reason; each decision cites its rule version and population.
- **Exporter/frontend/backend effect:** V3 keeps the research verdict LIMIT and adds an explicitly unavailable event review object as provisional extension data. Current v0.2 preview ignores that extension; after approval, backend must validate/render both levels and frontend must keep them visually separate.
- **Status:** OWNER APPROVAL REQUIRED.

### 9. Eligibility gates for event-level states

- **Current source definition:** V2 reports measured/modelled differences but does not validate an unshaded target counterfactual or field-cause classification. Its source intervention label describes experimental setup; only 10/23 events have adequate matched-placebo evidence.
- **Proposed definition:** `supported_change` requires all of: valid calibrated model/reference for the interval; declared coverage floor; signed residual beyond an approved calibrated healthy-error rule; detector evidence when the product claim is detection; adequate comparison population; explicit missing-control and uncertainty review; and alternative operating explanations assessed. It supports a measured-versus-modelled change only. A physical cause requires independent cause-specific evidence. `inconclusive` denotes usable but conflicting/underpowered evidence. `insufficient_evidence` denotes a failed validity, support, or comparison gate. If counterfactual and error assumptions are unresolved, event state is unavailable.
- **Justification:** labels can define retrospective episodes without measuring unshaded output or proving a production loss.
- **Required tests:** gate-by-gate fixtures, failure-reason preservation, no state assignment solely from `Fault`, threshold provenance, independent cause evidence required for cause language.
- **Exporter/frontend/backend effect:** V3 assigns no event state to `shading_01`; backend/front end must support unavailable state and show gates/reasons without auto-asserting cause.
- **Status:** OWNER APPROVAL REQUIRED.

### 10. Provenance, hashes, model version, training, and preprocessing

- **Current source definition:** immutable Zenodo record 7291380 v2 raw files have committed MD5/SHA256 and byte-size checks; the V2 protocol and evaluation source each have SHA256. The V2 run records model coefficients, whole-day splits, predictor-domain rule, thresholds, labels, and preprocessing. Raw source bytes are not in Git.
- **Proposed definition:** every artifact includes source file name, SHA256 and MD5 formats, byte count, source role/scope, verification state, immutable record/version/DOI, analysis input hashes, protocol hash, model/code version, coefficient units/features, split dates and counts, preprocessing, threshold/window, grouping, label use, exclusions, and the distinction between “verified in the committed V2 run” and “rehash performed by this export run.”
- **Justification:** an embedded historical hash does not prove that unavailable raw bytes were rechecked at export time; model identity must remain separable from export-code identity.
- **Required tests:** lowercase digest regex and exact length; hash-source roles and unique file names; source manifest reconciliation; protocol/model code hashes equal frozen result; exporter hash is separately identified; exported numbers reconcile to committed result JSONs.
- **Exporter/frontend/backend effect:** V3 carries raw hashes with their original V2 verification scope plus rehashed committed output hashes. v0.2 source checksum members currently lack types, digest patterns, scope and verification semantics; frontend should expose provenance without presenting it as a new raw-data download check.
- **Status:** OWNER APPROVAL REQUIRED.

### 11. Sample series, downsampling, validity, and gap markers

- **Current source definition:** `demo_measured_series_v2.csv` contains original aligned electrical samples at observed cadence; expected values use five-minute weather means. The separate healthy display series comes from twelve committed five-minute bin means. Energy metrics are calculated on original supported intervals, not the display samples.
- **Proposed definition:** record source cadence, output cadence, timestamp convention (original observation time or bin midpoint), aggregation rule, source/retained counts, gap/exclusion markers, and a typed validity reason. `valid=true` means the measured, reference, and expected values all pass the metric's declared eligibility; measured values may still be shown when a model estimate is unavailable.
- **Justification:** display series can be a lossy projection and must not look like the energy integration source. A single boolean cannot communicate which channel failed.
- **Required tests:** UTC sorted unique timestamps; gap markers retained; no line bridge across gaps; every validity flag agrees with fields and exclusions; energy calculations remain invariant to preview downsampling.
- **Exporter/frontend/backend effect:** V3 retains all shading label records and marks expected-value eligibility; healthy sample timestamps are documented bin midpoints. v0.2 requires typed downsampling and per-channel validity semantics; preview currently calls its table a time series without enough temporal-support detail.
- **Status:** OWNER APPROVAL REQUIRED.

### 12. Technician evidence and candidate-check approval

- **Current source definition:** `ELECTRICAL_EVIDENCE_MATRIX.md` and `INVESTIGATION_GUIDANCE_PROPOSAL.md` define bounded observations and proposed checks. Va is operating-point context; Ia is class-dependent; Ig is coupled to Pg; Vg/Fg do not have validated grid-fault truth. No diagnostic rule or candidate is owner-approved.
- **Proposed definition:** each prompt keeps an observed trigger with unit/time/quality, candidate hypothesis, support and counterevidence, next information, source reference, qualification/safety boundary, strength, and approval record. Proposed guidance never asserts root cause or repair. Only the source experimental intervention label may be described as a documented label.
- **Justification:** technician usefulness depends on evidence context and bounded action; sensor telemetry alone does not validate physical cause.
- **Required tests:** all fields typed and nonempty where required; status defaults proposed; owner_approved requires named approver, date/time, decision reference and approved text version; unsafe/unqualified action directions rejected; Ig cannot be described as independent Pg confirmation.
- **Exporter/frontend/backend effect:** V3 includes proposed inverter-record, data/reference, and safe shading-context checks only for `shading_01`. The proposed schema has no typed approval record; backend and frontend must render provenance and safety context without a classifier badge.
- **Status:** OWNER APPROVAL REQUIRED.

### 13. Schema mechanics, metric constraints, and identity

- **Current source definition:** draft identity pattern allows valid ids but schema alone does not make `review_id == 'review_' + experiment.identifier` or filename equal that id. `source_checksums` fields are required but untyped; metrics are not unique in JSON Schema; ratio fields do not enforce metric/population alignment; downsampling counts and sample fields lack complete types; electrical and candidate item fields have required names but mostly no JSON types; nested objects are permissive.
- **Proposed definition:** strengthen JSON Schema types/formats and closed-object policy where appropriate. Require lowercase MD5 (32 hex) and SHA256 (64 hex), unique metric ids, source scope and verification, finite values, paired ordered bounds, numerator/denominator population linkage, nonnegative observed/expected energy, UTC timestamps, unique chronological samples, count ordering, electrical/candidate field types, and explicit unknown/additional-field versioning. Enforce filename/experiment/review identity and approval workflow in application invariants because JSON Schema cannot compare arbitrary fields robustly.
- **Justification:** a field name or required key is not a semantic definition; proposed validation currently permits malformed objects that pass the JSON Schema alone.
- **Required tests:** schema negative fixtures for each malformed type/format, backend cross-field invariants, identity mismatch, unknown-field/version behavior, NaN/Infinity rejection, and preview/report source preservation.
- **Exporter/frontend/backend effect:** V3 has exporter-side exact reconciliation and custom validation; backend's experimental path passes current structural checks. Approval requires a new versioned schema and backend dispatch/invariants, then frontend types/rendering.
- **Status:** READY FOR APPROVAL (mechanical requirements are specified; owner must approve the scientific field meanings above first).

### 14. Approval and candidate status records

- **Current source definition:** proposed schema allows `approval_status=owner_approved` without an approver/date/reference record. Backend experimental invariants currently reject any such claim because no science-owner approval record exists. Candidate `status=owner_approved` is also forbidden while overall status is proposed.
- **Proposed definition:** `approval_status` remains `proposed` until a signed/traceable owner record identifies Rachit (or successor), decision date/time, exact schema/protocol hash, scope, and decision. Candidate check approval must point to its own approved version and record. A string alone never establishes approval.
- **Justification:** authorization requires evidence and exact scope; approval cannot be inferred from generated data.
- **Required tests:** missing, malformed, mismatched-version, or ownerless approval records fail; proposed artifacts cannot contain any approved item; signed-off artifact hash matches the approved source.
- **Exporter/frontend/backend effect:** exporter has no path to set owner approval. Backend approval gate remains intact; frontend must show “proposed” until there is an approval record.
- **Status:** OWNER APPROVAL REQUIRED.

## Signoff boundary

Only Rachit can decide the scientific semantics and approval states. This artifact set does not record a decision. The backend's local experimental validator checks structure and limited mechanical invariants; it cannot approve these definitions. Production v0.1 serving remains unchanged.
