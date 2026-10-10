# Phase 3 exporter and integration handoff

**Source checkout:** `main` at `b978940973ecbae6d516e6d49bc31800e3b7348a`, equal to the supplied current reference and remote `origin/main` at export start. The checkout was clean. No backend, frontend, production schema, infrastructure, historical V1/V2 result, or Git history was modified.

Before final validation, origin/main had advanced to 7ca012f with a scientific-documentation curation commit. The checkout was fast-forwarded to that latest fetched commit before completing this handoff. The curated tree retains the V2 protocol, executive summary, report, core result JSONs, and their Git history; it consolidates or removes several older overview notes. This Phase 3 work adds files only under analysis/.

## Exported cases

The exporter consumes the committed V2 results and produces:

- `results/reviews_v3/review_shading_01.json` — real `shading_01` event, actual measured target Pg, raw reference Pg, calibrated expected target power, UTC label bounds, distinct detector-confirmation times, all 2,148 labelled measured-series rows, actual 10,549/10,734 valid/labelled seconds, signed and positive-only energy, placebo model-error band, bounded electrical observations, and the research verdict `LIMIT`.
- `results/reviews_v3/review_healthy_20220126_0300.json` — a real known-zero-label comparison interval with twelve five-minute display bins and the V2 source-record energy results. It is explicitly described as part of threshold calibration, not an independent test or proven fault-free operation.
- `results/reviews_v3/review_insufficient_data_gap_20211222_20220124.json` — an explicit unavailability case record for the 2,848,806-second source-measurement gap. It is not a v0.2 review artifact because the proposed type enum has no data-gap or insufficient-data type. No energy is filled or estimated.

Identity is consistent for every record: `experiment_identifier`/`experiment.identifier = <experiment_id>`, `review_id = review_<experiment_id>`, and the filename is `review_<experiment_id>.json`. Only the first two files are v0.2 artifacts. Their `approval_status` is `proposed`; no owner approval is represented. Each keeps the research-level `LIMIT` separate from the unavailable event-level review state.

The raw Zenodo file digests are copied from the checksum-verified V2 audit and independent verification record, with verification scope disclosed. Those ~1.8 GB raw files are absent from this checkout and were not rehashed during this export. Committed V2 inputs were rehashed locally and matched to `package_manifest_v2.json`; the protocol and V2 model-code hashes match the frozen run.

## Reproducible commands

From repository root, export or refresh only the new V3 case files:

```powershell
python analysis/tools/export_reviews_v3.py export
```

Run exporter-side schema, identity, checksum-manifest, availability, and source-number reconciliation separately:

```powershell
python analysis/tools/export_reviews_v3.py validate
```

For each actual v0.2 review, run the existing backend's explicit local/offline experimental validator and create its HTML preview separately:

```powershell
python backend/validate_artifact.py analysis/results/reviews_v3/review_shading_01.json `
  --experimental-v2 `
  --report-output analysis/results/reviews_v3/preview_shading_01.html

python backend/validate_artifact.py analysis/results/reviews_v3/review_healthy_20220126_0300.json `
  --experimental-v2 `
  --report-output analysis/results/reviews_v3/preview_healthy_20220126_0300.html
```

Do not pass `review_insufficient_data_gap_20211222_20220124.json` to the v0.2 validator; it intentionally is not a review artifact. The v0.2 backend validator is a local preview path only; it makes no API/S3 request. The production review route still accepts v0.1 only.

Run source-backed Phase 3 detector diagnostics with the repository V2 runtime dependencies (matplotlib is required for plots):

```powershell
python analysis/tools/run_detector_diagnostics_v3.py
```

## Validation performed

- Existing independent V2 output verifier: **PASS**. Protocol and V2 code hashes, calibration-only threshold arithmetic, healthy alarm arithmetic, event count, split separation, independent demo expected power and energy reconciliation, source audit claims, and historical V2 file identity all pass.
- Existing tests before the V3 work: **99 passed**.
- New Phase 3 exporter and detector tests: **7 passed**. They check exact source values, event identity and UTC boundaries, label/confirmation separation, measured/reference/expected series separation, availability semantics, draft-schema validity, ratio arithmetic, byte-for-byte deterministic export, common-population reconstruction, candidate alert rates and generated plots.
- Exporter custom validation: **PASS** for both v0.2 reviews and the explicit unavailability record.
- Backend's opt-in v0.2 schema/invariant validation and HTML preview: **PASS** for both v0.2 reviews. Production API and storage were not exercised.
- All metrics that overlap the V2 examples/result JSONs agree at full stored precision. The event artifact retains measured 2.3816488889 kWh, expected 2.7786978663 kWh, signed deviation 0.3970489774 kWh, positive-only deviation 0.3971261454 kWh, 10,549 valid seconds, 10,734 observed labelled seconds, and the original primary confirmation at 07:20:00 UTC.

## Contract blockers and required integration after approval

Rachit's signoff is required for scientific definitions and event-state gates in `SCIENTIFIC_CONTRACT_DECISIONS_V3.md`, especially signed/positive energy and polarity; duration/coverage denominators; healthy labels versus known fault-free operation; empirical model-error band versus confidence interval; event-level decision eligibility; additional insufficient-data type; and what counts as approved evidence-guided technician language. No field is owner-approved now.

After that decision, the backend owner should publish a new versioned schema and implement dispatch, typed provenance and electrical/candidate records, digest checks, unique metrics and ratio-population checks, event/label/confirmation fields, explicit data-gap and event-decision availability states, owner-approval records, and HTML rendering for those fields. Preserve the v0.1 route and immutable legacy artifacts.

After the backend version exists, the frontend owner should add that version to its accepted adapter/types, render measured target, raw reference, and expected target series separately, show metric population and coverage denominator, distinguish intervention bands from detector confirmations, label placebo bands as model-error ranges, retain reasons for unavailable values, show research verdict apart from event state, and display only bounded proposed technician prompts with qualification/safety/source provenance. `web/` is unchanged in this handoff.

Production serving would then require the usual separately reviewed API/storage/deployment changes and an owner-approved real artifact. This handoff stops at reviewable local evidence; it does not change serving or claim production approval.
