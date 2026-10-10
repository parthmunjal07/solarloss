# Phase 3: scientific v2 integration review

**Status:** backend v0.2 support is local and experimental. The scientific v0.2 contract is still proposed. Production API review serving remains v0.1 only.

## What the repository reports

The figures below were checked against `analysis/EXPERIMENT_REPORT_V2.md`, `analysis/EXECUTIVE_SUMMARY_V2.md`, `analysis/results/shading_evaluation_v2.json`, and `analysis/results/example_cases_v2.json` at main commit `e350c84`.

- The selected five-minute detector retrospectively detected 23 of 23 documented episodes, on 23 intervention days. This is one installation and does not establish fleet accuracy or a prospective guarantee.
- It produced 153 healthy alert runs over 1,794.5067 supported hours: 0.08526 runs per healthy hour. The frozen gate is at most 0.05 per hour, so E2 is `LIMIT`. The model's healthy calibration error is not detector accuracy.
- For `shading_01`, expected-minus-measured signed deviation is 0.39704898 kWh. Positive-only deviation is 0.39712615 kWh. There are 10,549 valid elapsed seconds over 10,734 seconds of observed labelled support, or 98.28% coverage. Neither deviation is recovered energy or a true counterfactual-loss estimate.
- Only 10 of 23 events have adequate matched placebo support; 13 are explicitly unavailable for that comparison. The `shading_01` empirical model-error band uses 10 blocks across 7 days and is not a counterfactual-loss confidence interval.
- Electrical signals provide operating context, not independent diagnosis. The proposed technician checks in `analysis/INVESTIGATION_GUIDANCE_PROPOSAL.md` are not approved diagnostic rules.
- The experiment-level research verdict is `LIMIT`; E1 feasibility is `GO`, E2 detector performance is `LIMIT`, E3 energy-effect estimation is `LIMIT`, E4 electrical context is `LIMIT`, and universal diagnosis is `REJECT`.

## Draft contract review

The research-owned source `analysis/contracts/review.schema.v0.2.0.proposed.json` has not been edited. A byte-identical copy is packaged at `artifacts/schema/review.schema.v0.2.0.proposed.json`, identified as proposed and non-serving in the Lambda manifest.

The draft makes several important semantics explicit: signed deviation may be negative; positive-only deviation is nonnegative and cannot establish abnormality; unavailable metrics use null plus a reason; estimated metrics use a finite value and no reason; and uncertainty types distinguish empirical model-error bands from day-bootstrap intervals. It also carries separate measured, raw reference, and expected series, coverage fields, electrical evidence, and candidate checks.

The following areas remain underspecified in the draft and must be resolved by the scientific owner before approval:

- `approval_status=owner_approved` has no required approver identity, date, or approval record. A field value alone is not an approval workflow.
- Most electrical-evidence and candidate-check fields are required but lack explicit JSON types. Provenance objects and downsampling counts also lack detailed field schemas.
- Checksum members require `file`, `md5`, and `sha256` names but do not define their value types or digest formats.
- A ratio carries numerator and denominator units but does not encode or validate that they describe the same population as the metric.
- The contract needs an agreed rule for empty or partial electrical observations, unavailable candidate prompts, and which event-specific metrics are required for each experiment type.
- Metric definitions, expected/observed energy scope, coverage denominators, uncertainty bounds and limitations, and provenance completeness still need owner review.

The backend's additional checks enforce only mechanical interpretations of existing fields. The local v0.2 path currently requires `approval_status=proposed`; it rejects an `owner_approved` claim because this repository has no recorded science-owner approval. It also rejects owner-approved candidate status while the overall artifact is proposed. These checks do not introduce scientific thresholds, recompute research outputs, decide whether a cause is likely, or elevate a candidate check to a diagnosis.

## Local experimental path

The production API calls the v0.1 loader and rejects v0.2 artifacts. The existing `/api/v1` routes, CORS behavior, storage, and download path are unchanged. Proposed v0.2 validation and HTML rendering require an explicit local opt-in:

```powershell
python -m backend.validate_artifact 'data/exports/review_<experiment_id>.json' `
  --experimental-v2 `
  --report-output "$env:TEMP/solarloss-v2-preview.html"
```

This mode validates the proposed schema, structural semantics, and identities, then writes an escaped local HTML preview. It does not call an API, read or write S3, create an artifact, or activate a fixture. The tests use invented values labeled `SYNTHETIC` only.

## Approval and AWS handoff

Before a science exporter can target v0.2, Rachit, as science owner, must approve the metric definitions and status meanings, resolve the open draft questions above, and publish the approved versioned contract. The backend's explicit approval gate and the contract version must then be updated to match that approval. The science worker can then export an event-specific review with original raw-derived energy, complete provenance, and the identity convention `experiment.identifier=<id>`, `review_id=review_<id>`, filename `review_<id>.json`. Run the approved-version local validator and report, review the output with Rachit, and only then plan API/storage changes through backend and infrastructure review.

This checkout contains no `infra/` or `web/` files, no AWS CLI, and no AWS credential/profile environment variables. There are no repository infrastructure settings or live AWS identity to coordinate from this workspace. No AWS resource, CORS policy, endpoint, upload, or production artifact was changed. Before deployment, the infrastructure owner must supply the approved account/region, bucket and prefixes, IAM policy, API Gateway configuration, explicit frontend origins, Lambda runtime/architecture and package configuration, and CI/deployment path. The current Lambda manifest and v0.1 routes remain the production boundary.
