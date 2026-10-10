# SolarLoss review API

This Python Lambda serves offline analysis artifacts. It does not ingest inverter data, train models, or generate scientific conclusions. For every review response it loads the private S3 object, validates it against [`artifacts/schema/review.schema.json`](../artifacts/schema/review.schema.json), and returns the validated artifact. The schema is provisional v0.1.0 pending scientific-owner review; see [`artifacts/schema/CONTRACT.md`](../artifacts/schema/CONTRACT.md), the [science handoff](../docs/backend-science-handoff.md), and the [schema-change proposal](../docs/scientific-schema-change-proposal.md).

## API contract

All routes are under `/api/v1` and use API Gateway HTTP API payload format 2.0.

| Method and path | Response |
| --- | --- |
| `GET /api/v1/health` | `200` JSON `{ "status": "ok" }` |
| `GET /api/v1/experiments` | `200` JSON `{ "experiments": [...] }`; each entry is derived from a validated artifact and includes its identifier, type, review id, analysis version, systems, time window, and artifact decision state |
| `GET /api/v1/reviews/{experiment_id}` | `200` JSON containing the validated review artifact unchanged |
| `GET /api/v1/reviews/{experiment_id}/report` | Generates escaped static HTML, stores it in the private reports prefix, then returns `302` to a short lived S3 presigned download URL |

Experiment ids must match `^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$`. Error responses use `{ "error": { "code": "...", "message": "...", "request_id": "..." } }`. Invalid ids return `400`, missing reviews `404`, malformed stored artifacts `500`, and S3 availability failures `503`. No missing artifact is replaced with a sample or demo result.

The object name, `experiment.identifier`, and `review_id` must agree: `artifacts/reviews/review_{experiment_id}.json`, `{experiment_id}`, and `review_{experiment_id}` respectively. Mismatches are rejected with actionable local validator errors; the API does not rename or rewrite science output. Structural checks cover chronology, count ordering, confidence interval ordering, finite numbers, and identifier shape. These checks do not validate the scientific meaning of a metric or decision. In particular, v0.1.0 `energy_deficit` is not by itself a measured shading-loss or recovery result.

The HTML report shows the stored decision and reasons, dataset checksums, experiment and label provenance, all metric values and denominators, baseline comparison, uncertainty and its limitations, quality checks, exclusions, robustness and placebo findings, limitations, and the stored time series. Report text comes from the validated artifact; values and decisions are not recomputed. Download is an attachment from S3. The presigned URL lifetime defaults to 900 seconds.

## Local setup and execution

PowerShell from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements-dev.txt
python -m pytest backend/tests -q
python -m ruff check backend
python -m ruff format --check backend
python -m compileall -q backend
```

To validate an exporter file and exercise the in-process review, listing, and report paths without AWS:

```powershell
python -m backend.validate_artifact 'C:\path\to\review_<experiment_id>.json'
```

Proposed v0.2 artifacts have a separate, explicit offline-only path. It validates the candidate schema and can render a local preview, but does not call or change the production API:

```powershell
python -m backend.validate_artifact 'data/exports/review_<experiment_id>.json' `
  --experimental-v2 `
  --report-output "$env:TEMP/solarloss-v2-preview.html"
```

The original source-backed V3 exports can be checked locally with the same command:

```powershell
python -m backend.validate_artifact analysis/results/reviews_v3/review_shading_01.json `
  --experimental-v2 `
  --report-output "$env:TEMP/solarloss-shading-v3-preview.html"
python -m backend.validate_artifact analysis/results/reviews_v3/review_healthy_20220126_0300.json `
  --experimental-v2 `
  --report-output "$env:TEMP/solarloss-healthy-v3-preview.html"
```

Production remains v0.1-only by default. A recorded science-owner approval of the exact v0.2 schema and an explicit release decision are required before setting `APPROVED_REVIEW_SCHEMA_V02_SHA256`. When set, the Lambda requires both that exact schema digest and a matching typed owner-approval record on each v0.2 artifact. This variable is unset in this checkout; proposed V3 artifacts are rejected by production routes. The scientific decision and API readiness state are in the [Phase 4 decision sheet](../docs/phase-4-scientific-decision-sheet.md) and [backend readiness note](../docs/phase-4-backend-readiness.md). Test fixtures are synthetic and must not be used as exported or served review artifacts.

To run the API against actual private review artifacts in an S3 bucket, set an AWS profile or use the normal AWS credential chain. Do not create fixture output for the local server.

```powershell
$env:AWS_PROFILE = "your-aws-profile"
$env:AWS_REGION = "ap-south-1"
$env:REVIEW_BUCKET = "your-private-review-bucket"
$env:REVIEW_PREFIX = "artifacts/reviews/"
$env:REPORT_PREFIX = "artifacts/reports/"
$env:REPORT_URL_TTL_SECONDS = "900"
$env:ALLOWED_ORIGINS = "https://your-hosted-frontend.example"
python -m backend.local_server
```

The local server binds to `127.0.0.1:8000`. Check the health route with `curl.exe http://127.0.0.1:8000/api/v1/health`. It has no demo-data mode. `ALLOWED_ORIGINS` must be an explicit comma-separated list of frontend origins; wildcard CORS is rejected.

## Lambda and AWS requirements

- Python Lambda runtime (Python 3.12, x86_64), API Gateway HTTP API payload format 2.0, and a deployment package containing `handler.py`, `solarloss_backend/`, the schema at `artifacts/schema/review.schema.json`, `jsonschema`, and `boto3`.
- Private S3 bucket with public access blocked, bucket versioning enabled, and default server-side encryption. Review objects follow `artifacts/reviews/review_{experiment_id}.json`; report objects are written beneath `artifacts/reports/{experiment_id}/`.
- Lambda environment: `REVIEW_BUCKET` (required), optional `REVIEW_PREFIX`, `REPORT_PREFIX`, `REPORT_URL_TTL_SECONDS` (60 to 604800), and `ALLOWED_ORIGINS` (explicit origins only). `REVIEW_SCHEMA_PATH` can override the v0.1 schema location. `APPROVED_REVIEW_SCHEMA_V02_SHA256` remains unset unless the v0.2 approval/release gate has been completed.
- Lambda execution role: `s3:ListBucket` restricted to the review prefix; `s3:GetObject` on the review prefix; `s3:PutObject` and `s3:GetObject` on the report prefix (the latter permits signing report downloads); and CloudWatch Logs permissions. No AWS keys belong in environment variables or Git.
- Configure API Gateway CORS with the same explicit origins as `ALLOWED_ORIGINS`. The handler also validates preflight origins. Set short CloudWatch log retention and an S3 lifecycle rule to expire generated reports after the download window.
- Keep analysis/model dependencies, including `pvlib`, out of the Lambda package. The offline analysis writes precomputed artifacts; this Lambda only validates and presents them.

No AWS infrastructure is created by this backend branch. Coordinate bucket, IAM, API Gateway, log group, packaging, and frontend hosting with the infrastructure owner before deployment.

Build and validate the self-contained deployment ZIP from the repository root:

```powershell
python -m backend.build_lambda --output backend/build/solarloss-lambda.zip
python -m backend.validate_lambda_package backend/build/solarloss-lambda.zip
```

The builder resolves the pinned `backend/requirements-lambda.txt` lock into a clean target directory and selects Linux x86_64 Python 3.12 wheels. The package includes that lock and a manifest listing its handler, schema, runtime, dependencies, and environment settings. It intentionally excludes ML/scientific libraries. `.github/workflows/backend.yml` runs lint, formatting, tests, compilation, package build, and package validation on pushes to `main` and pull requests targeting `main`.

## Scientific handoff

Before freezing the v0.1 contract, the science owner should check the raw reference versus calibrated expected-output distinction, interval alignment and units, whether values are per-sample or interval totals, exact deficit/coverage/calibration denominators, held-out healthy population naming, uncertainty block semantics, exclusions, and placebo/robustness representation. The required v0.2 topics are listed in the [proposal](../docs/scientific-schema-change-proposal.md); none are finalized here. Update the schema, contract, tests, and analysis producer together through review. Test fixtures are confined to `backend/tests/` and explicitly marked synthetic; they are not publishable review artifacts.
