# Phase 4 backend and deployment readiness

**Repository baseline:** `main` at the audited V3 source commit `8b78fb41b5f79a5db1a31fd328b7bd4e660db212`.

**Current Phase 5 update (2026-10-11):** field semantics are approved under `SOLARLOSS-SCI-V02-20261011-SEMANTICS`. Rachit's artifact-specific authorization for the exact `shading_01` candidate was separately confirmed by the user and recorded in [the release approval](phase-5-shading-01-release-approval.md). Its separate approved copy passes strict backend checks and the real local API/frontend/HTML-download journey. Historical V3 exports remain unchanged/proposed. AWS deployment is postponed by the user; cloud actions are out of scope for the current task. Private S3 reads and deployed serving are **NOT VERIFIED**, and the production gate remains unset. See [the release handoff](../artifacts/releases/v0.2.0/shading_01/README.md). The sections below describe the original Phase 4 readiness baseline unless updated explicitly.

## API behavior and release gate

The existing v0.1 routes and response shapes remain unchanged. The default Lambda configuration serves v0.1 only. The in-process candidate loader validates proposed v0.2 artifacts only when the local `--experimental-v2` option is explicit; it never calls S3 or the API.

After a recorded science-owner approval of the exact schema, a deployment may set `APPROVED_REVIEW_SCHEMA_V02_SHA256` to the lowercase SHA256 of the bundled v0.2 schema. Production v0.2 dispatch then additionally requires each stored artifact to carry `approval_status: "owner_approved"` and a matching typed `decision.owner_review` record with schema/protocol hashes, approver, UTC approval time, scope, and decision reference. The variable is currently unset. A proposed artifact, an unsupported version, a mismatched identity, or a schema-hash mismatch is rejected. The present V3 source reviews remain proposed and cannot pass the production gate.

The v0.2 listing uses `research_verdict` and a separate `event_review` object. `LIMIT` is never mapped to an event state. The review endpoint returns the approved versioned artifact unchanged. HTML report generation keeps metric availability, reasons, provenance scopes, intervention bounds, detector confirmations, event review status, and proposed technician-check status visible. No route infers a diagnosis or converts a null to zero.

## Source artifacts and keys

The unchanged V3 source files are offline fixtures and approval candidates:

- `analysis/results/reviews_v3/review_shading_01.json`
- `analysis/results/reviews_v3/review_healthy_20220126_0300.json`
- `analysis/results/reviews_v3/review_insufficient_data_gap_20211222_20220124.json` — separate sidecar, not a review and not an experiment-listing entry.

If Rachit approves the review contract and the source artifacts are approved for storage, their exact private S3 keys are:

- `artifacts/reviews/review_shading_01.json`
- `artifacts/reviews/review_healthy_20220126_0300.json`

Generated HTML reports use `artifacts/reports/{experiment_id}/{sha256-of-html}.html`. The adapter writes them with server-side encryption and returns a presigned attachment URL. The current report URL lifetime defaults to 900 seconds. Keep the review and report bucket private.

## Deployment variables and package

| Variable | Requirement / current default |
| --- | --- |
| `REVIEW_BUCKET` | Required private bucket |
| `REVIEW_PREFIX` | Optional; default `artifacts/reviews/` |
| `REPORT_PREFIX` | Optional; default `artifacts/reports/` |
| `REPORT_URL_TTL_SECONDS` | Optional; default `900`, accepted range `60`–`604800` |
| `ALLOWED_ORIGINS` | Optional comma-separated exact origins; wildcard is rejected |
| `REVIEW_SCHEMA_PATH` | Optional override for the v0.1 schema |
| `APPROVED_REVIEW_SCHEMA_V02_SHA256` | **Unset today.** Set only after recorded Rachit approval of the exact bundled schema and an explicit release decision. Must be lowercase 64-hex SHA256. |
| `AWS_REGION` / standard AWS credential chain | Supplied by the deployment environment; never embed keys in code, package, or browser. |

The Lambda target remains Python 3.12 on x86_64 with API Gateway HTTP API payload v2. The package includes the v0.1 schema and candidate v0.2 schema at `artifacts/schema/review.schema.v0.2.0.proposed.json`; the manifest marks v0.2 serving disabled and identifies its hash activation gate. No analysis, ML, or `pvlib` dependency is added to Lambda.

## Local validation and demo preparation

```powershell
python analysis/tools/export_reviews_v3.py validate
python -m backend.validate_artifact analysis/results/reviews_v3/review_shading_01.json `
  --experimental-v2 `
  --report-output "$env:TEMP/solarloss-shading-v3-preview.html"
python -m backend.validate_artifact analysis/results/reviews_v3/review_healthy_20220126_0300.json `
  --experimental-v2 `
  --report-output "$env:TEMP/solarloss-healthy-v3-preview.html"
```

The original source-backed test uses the committed `shading_01` JSON directly and reconciles the recorded observed, expected, signed, and positive-only energy values. The local Lambda-shaped test exercises `ReviewApplication.handle_event`; proposed V3 files are rejected by the production default, and a synthetic signoff test exercises the future hash-gated route without claiming actual approval. The sidecar remains outside the versioned review schema.

Before an AWS demo, the infrastructure owner must supply the actual API URL, approved account/region, private bucket name, IAM policy, API Gateway/CORS configuration, frontend origin, deployment package location, and deployment workflow. Deployment verification requires a real URL, successful private S3 review read, exact review API response, and report 302 to a private short-lived S3 URL. None was supplied or exercised here.

## Open scientific and display blockers

- Field-definition approval and the specific bounded shading release signoff are now recorded. Other artifacts still need their own signoff; the production gate additionally requires verified deployment configuration and private storage. `LIMIT` alone satisfies no approval gate.
- The 28 invalid shading display samples have null model-expected power but no per-sample availability reason; do not infer one. Rachit should decide whether the next exporter adds channel-specific validity/reason fields.
- Electrical evidence entries are window summaries with no per-measurement UTC timestamp or interval field. Keep them as contextual summaries, not timestamped technician triggers, until Rachit decides a typed temporal-support correction.
- Detector generalisation, event-state eligibility, fault diagnosis, and maintenance recommendations are outside contract-field approval and remain unapproved.

See the [scientific decision sheet](phase-4-scientific-decision-sheet.md) and [frontend handoff](phase-4-frontend-v0.2-handoff.md) for the pending approvals and typed response examples.

## GitHub CI for the pushed Phase 4 commit

For commit `0254befe35ad15988b67889c33aff276f54c949f`, Backend CI and Scientific Unit Checks completed successfully. Frontend CI failed in `tests/proposed-v2.test.ts` while validating the existing adapter fixture against the stricter proposed contract. The fixture lacks required `event_context`, typed checksum and model provenance fields, explicit splits and thresholds, metric `ratio` and `uncertainty` fields, and `decision.event_review`. The frontend production build and browser smoke steps were skipped after the unit-test failure.

No `web/` files were changed because frontend ownership remains with Parth. Before v0.2 frontend integration is complete, Parth needs to update the adapter and its fixture to the field-level handoff while preserving `research_verdict: "LIMIT"` separately from the unavailable event-review state. [Backend CI](https://github.com/parthmunjal07/solarloss/actions/runs/38073307458) and [Scientific Unit Checks](https://github.com/parthmunjal07/solarloss/actions/runs/38073307486) passed; [Frontend CI](https://github.com/parthmunjal07/solarloss/actions/runs/38073307483) failed.
