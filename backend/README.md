# SolarLoss review API

This Python Lambda serves offline analysis artifacts. It does not ingest inverter data, train models, or generate scientific conclusions. For every review response it loads the private S3 object, validates it against [`artifacts/schema/review.schema.json`](../artifacts/schema/review.schema.json), and returns the validated artifact. The schema is provisional v0.1.0 pending scientific-owner review; see [`artifacts/schema/CONTRACT.md`](../artifacts/schema/CONTRACT.md).

## API contract

All routes are under `/api/v1` and use API Gateway HTTP API payload format 2.0.

| Method and path | Response |
| --- | --- |
| `GET /api/v1/health` | `200` JSON `{ "status": "ok" }` |
| `GET /api/v1/experiments` | `200` JSON `{ "experiments": [...] }`; each entry is derived from a validated artifact and includes its identifier, type, review id, analysis version, systems, time window, and artifact decision state |
| `GET /api/v1/reviews/{experiment_id}` | `200` JSON containing the validated review artifact unchanged |
| `GET /api/v1/reviews/{experiment_id}/report` | Generates escaped static HTML, stores it in the private reports prefix, then returns `302` to a short lived S3 presigned download URL |

Experiment ids must match `^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$`. Error responses use `{ "error": { "code": "...", "message": "...", "request_id": "..." } }`. Invalid ids return `400`, missing reviews `404`, malformed stored artifacts `500`, and S3 availability failures `503`. No missing artifact is replaced with a sample or demo result.

The HTML report shows the stored decision and reasons, dataset checksums, experiment and label provenance, all metric values and denominators, baseline comparison, uncertainty and its limitations, quality checks, exclusions, robustness and placebo findings, limitations, and the stored time series. Report text comes from the validated artifact; values and decisions are not recomputed. Download is an attachment from S3. The presigned URL lifetime defaults to 900 seconds.

## Local setup and execution

PowerShell from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements-dev.txt
python -m pytest backend/tests -q
```

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

- Python Lambda runtime (Python 3.12 is the target), API Gateway HTTP API payload format 2.0, and a deployment package containing `handler.py`, `solarloss_backend/`, the schema at `artifacts/schema/review.schema.json`, `jsonschema`, and `boto3`.
- Private S3 bucket with public access blocked, bucket versioning enabled, and default server-side encryption. Review objects follow `artifacts/reviews/review_{experiment_id}.json`; report objects are written beneath `artifacts/reports/{experiment_id}/`.
- Lambda environment: `REVIEW_BUCKET` (required), optional `REVIEW_PREFIX`, `REPORT_PREFIX`, `REPORT_URL_TTL_SECONDS` (60 to 604800), and `ALLOWED_ORIGINS` (explicit origins only). `REVIEW_SCHEMA_PATH` can override the schema location.
- Lambda execution role: `s3:ListBucket` restricted to the review prefix; `s3:GetObject` on the review prefix; `s3:PutObject` and `s3:GetObject` on the report prefix (the latter permits signing report downloads); and CloudWatch Logs permissions. No AWS keys belong in environment variables or Git.
- Configure API Gateway CORS with the same explicit origins as `ALLOWED_ORIGINS`. The handler also validates preflight origins. Set short CloudWatch log retention and an S3 lifecycle rule to expire generated reports after the download window.
- Keep analysis/model dependencies, including `pvlib`, out of the Lambda package. The offline analysis writes precomputed artifacts; this Lambda only validates and presents them.

No AWS infrastructure is created by this backend branch. Coordinate bucket, IAM, API Gateway, log group, packaging, and frontend hosting with the infrastructure owner before deployment.

## Scientific handoff

Before freezing the v0.1 contract, the science owner should check the raw reference versus calibrated expected-output distinction, interval alignment and units, whether values are per-sample or interval totals, exact deficit/coverage/calibration denominators, held-out healthy population naming, uncertainty block semantics, exclusions, and placebo/robustness representation. Update the schema, contract, tests, and analysis producer together through review. Test fixtures are confined to `backend/tests/` and explicitly marked synthetic; they are not publishable review artifacts.
