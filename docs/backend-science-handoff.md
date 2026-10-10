# Backend and science-worker handoff

This page defines the current producer/backend boundary. Schema version `0.1.0` is provisional; scientific semantics still require owner review. See [`scientific-schema-change-proposal.md`](scientific-schema-change-proposal.md).

## Artifact contract

The science exporter should write its original review JSON as `review_<experiment_id>.json`. The same ID must appear in all three places:

- File name: `review_<experiment_id>.json`
- JSON `experiment.identifier`: `<experiment_id>`
- JSON `review_id`: `review_<experiment_id>`

For new local exports, use the ignored workspace path `data/exports/review_<experiment_id>.json`; have the exporter write there directly. The API reads the S3 object at `artifacts/reviews/review_<experiment_id>.json`. It does not rename or edit scientific artifacts. A mismatch is an exporter integration error; the compatibility command reports the identities that disagree. Keep the historical export intact and coordinate any naming change with the science owner. If an existing export is stored elsewhere, point the validator at that original path rather than moving or renaming it.

## Validate a science export locally

From the repository root, point the command at the original exporter output. No frontend, AWS credentials, or deployed API is needed for this check:

```powershell
$artifact = 'data/exports/review_<experiment_id>.json'
python -m backend.validate_artifact $artifact
```

The command validates the v0.1.0 JSON Schema, structural invariants, and all artifact identities. It then passes that same file through the in-process review API, listing, and HTML report code. It neither writes an artifact nor calls AWS. If the exporter currently produces another filename, the command fails and explains the producer contract; it never silently renames or rewrites the result.

### Proposed v0.2 local review

The v0.2 schema is proposed and is not served by the production API. For a local-only schema check and escaped HTML preview, opt in explicitly:

```powershell
python -m backend.validate_artifact 'data/exports/review_<experiment_id>.json' `
  --experimental-v2 `
  --report-output "$env:TEMP/solarloss-v2-preview.html"
```

This command does not exercise API routes, storage, S3, or downloads. It must not be used to upload v0.2 to the current service. The v2 research results and approval questions are summarized in [`phase-3-scientific-v2-integration.md`](phase-3-scientific-v2-integration.md).

## Upload and exercise a real artifact

Only after the private bucket, IAM role, API URL, and science-owner naming are confirmed, set the configured values and use the exact experiment ID from the JSON:

```powershell
$experimentId = '<experiment.identifier from the artifact>'
$artifact = "data/exports/review_${experimentId}.json"
$env:REVIEW_BUCKET = '<private-review-bucket>'
$env:SOLARLOSS_API_URL = 'https://<api-id>.execute-api.<region>.amazonaws.com'

python -m backend.validate_artifact $artifact
aws s3 cp $artifact "s3://$env:REVIEW_BUCKET/artifacts/reviews/review_${experimentId}.json" --sse AES256

$retrievedJson = Join-Path $env:TEMP "solarloss-review-$experimentId.json"
$reportHtml = Join-Path $env:TEMP "solarloss-report-$experimentId.html"
curl.exe --fail --silent --show-error `
  "$env:SOLARLOSS_API_URL/api/v1/reviews/$experimentId" `
  --output $retrievedJson
curl.exe --fail --silent --show-error --location `
  "$env:SOLARLOSS_API_URL/api/v1/reviews/$experimentId/report" `
  --output $reportHtml
python -m backend.validate_artifact $artifact `
  --retrieved-json $retrievedJson `
  --report-html $reportHtml
```

The last command compares parsed API JSON to the original artifact and checks that the downloaded report contains the source values covered by the report contract. `curl --location` follows the API's 302 to the short-lived S3 presigned URL. These commands verify an integration only after AWS is configured; local compatibility does not imply a deployment.

## Producer and API flow

1. The science worker exports the versioned review JSON without changing historical results.
2. The owner runs `python -m backend.validate_artifact <artifact>` and resolves identity/schema errors in the exporter.
3. The approved artifact is uploaded to the private review prefix under the exact key above.
4. `GET /api/v1/reviews/{experiment_id}` reads and validates that S3 object, then returns its JSON content.
5. `GET /api/v1/reviews/{experiment_id}/report` renders the stored artifact's values and decision, writes the HTML report to the private report prefix, and returns a presigned download redirect.
6. The same compatibility command can compare downloaded API JSON and report HTML with the source file.

## Provisional scientific boundary

The API does not run ML, detect shading, estimate recovery, or replace the producer's decision. The v2 research package reports 23/23 retrospective detections on one installation, but its selected detector exceeds the frozen healthy false-alarm gate and is `LIMIT`. Its energy deviations are not true counterfactual loss or recovered energy; electrical evidence is context only, and technician checks are proposed. These research results do not establish a production-ready detector or approved shading-recovery result. The v0.1 numeric `energy_deficit` field remains insufficient to represent unavailable energy safely. Resolve metric meanings, unavailable values, denominator definitions, model/training provenance, exclusions, downsampling, independent episode counts, and decision provenance through the methodology handoff before changing the production schema or presenting a shading-loss claim.

## Lambda build and configuration

Build a Python 3.12, x86_64 deployment ZIP from the repository root:

```powershell
python -m backend.build_lambda --output backend/build/solarloss-lambda.zip
python -m backend.validate_lambda_package backend/build/solarloss-lambda.zip
```

The builder installs the pinned `backend/requirements-lambda.txt` lock into a clean target directory and packages the Lambda handler, internal modules, schema, dependencies, lock file, and manifest. It targets Linux x86_64 Python 3.12 wheels for Lambda. It excludes the offline scientific stack. Before deployment, coordinate with the infrastructure owner and configure a private versioned S3 bucket, API Gateway HTTP API v2, CORS origins, Lambda IAM access, `REVIEW_BUCKET`, and CloudWatch logging. No AWS deployment is performed by these local commands.
