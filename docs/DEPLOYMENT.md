# Deployment guide

**2026-10-11 plan update: AWS deployment is postponed.** This guide is preparation for a separately authorized future phase. Do not execute cloud deployment commands, create/modify/upload/delete AWS resources, incur AWS charges or enable production v0.2 serving during the current local-completion task.

This guide documents the deployment target implemented by the repository. It is a manual checklist, not infrastructure-as-code. No AWS account, resources, DNS names, API URL, bucket, or deployment credentials were available to verify in this pass. Do not treat the commands below as evidence that a service is deployed.

## Target architecture

- Static React build in a private S3 bucket served through CloudFront with Origin Access Control (OAC).
- API Gateway **HTTP API**, payload format **2.0**, integrated with a Python **3.12, x86_64 Lambda ZIP**.
- A separate private S3 bucket (or separately isolated prefixes) holds review JSON and generated HTML reports. Block public access, enable versioning and default encryption.
- The Lambda only validates v0.1 review artifacts, returns their stored values, and generates an escaped HTML download. It does not run the scientific model.
- The browser calls the API origin from `VITE_API_BASE_URL`. Keep API and static site origins separate unless an API CloudFront behavior and its caching/error rules are deliberately configured.

The code path is `backend/lambda/handler.py` → `ReviewApplication` → schema/invariant validation and `S3ReviewStore`. The frontend's Vite production guard excludes the development-only research preview. See [Architecture](ARCHITECTURE.md) for component boundaries.

## Release values to obtain

Before deployment, the infrastructure owner must provide and approve these values. Keep credentials in the AWS credential chain; never put access keys in environment variables or repository files.

| Value                                                                | Use                                                                                                       |
| -------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| AWS account, region, and deployment role                             | Restrict deployment to the intended account and region.                                                   |
| `FRONTEND_BUCKET`, CloudFront distribution ID and domain             | Private static origin and release invalidation.                                                           |
| `REVIEW_BUCKET`                                                      | Private review and generated-report storage.                                                              |
| `REVIEW_PREFIX`                                                      | Defaults to `artifacts/reviews/`.                                                                         |
| `REPORT_PREFIX`                                                      | Defaults to `artifacts/reports/`.                                                                         |
| `REPORT_URL_TTL_SECONDS`                                             | Defaults to `900`; code accepts 60 through 604800 seconds. Use a short download window.                   |
| `ALLOWED_ORIGINS`                                                    | Exact frontend origins, comma-separated, with no wildcard. Configure the same values in API Gateway CORS. |
| HTTP API ID, stage, API origin, Lambda function and `prod` alias     | The API integration must target the Lambda alias ARN.                                                     |
| Log retention, throttles, concurrency limit and monthly budget alert | Set explicit operational and cost bounds before opening traffic.                                          |

Use a profile or an attached deployment role, for example:

```powershell
$env:AWS_PROFILE = "approved-deployment-profile"
$env:AWS_REGION = "ap-south-1"
aws sts get-caller-identity
```

Confirm the returned account with the infrastructure owner before running any deployment command.

## Storage and IAM requirements

For the review/report bucket:

- Block all public access; enable bucket versioning and default server-side encryption.
- Allow the Lambda role `s3:ListBucket` only for the review prefix, `s3:GetObject` only for review objects, and `s3:PutObject` plus `s3:GetObject` only for generated report objects. The latter permission allows the Lambda role to sign report downloads.
- Grant no delete or public ACL permissions to the Lambda role. Keep deployment permissions separate from runtime permissions.
- Add a lifecycle rule to expire generated reports after the report download window. Retain versioned source reviews according to the owner's retention policy.

For the frontend bucket, keep it private and grant `s3:GetObject` to the CloudFront OAC distribution only. The Lambda execution role needs CloudWatch Logs write access; set finite log retention. Do not grant the browser direct S3 access to review objects.

## Build and configure

Run from the repository root with Python 3.12, Node 22, AWS CLI v2, and an approved deployment profile.

### Backend ZIP and Lambda alias

Build and inspect the exact package used by backend CI:

```powershell
python -m pip install -r backend/requirements-dev.txt
python -m backend.build_lambda --output backend/build/solarloss-lambda.zip
python -m backend.validate_lambda_package backend/build/solarloss-lambda.zip
```

Set the Lambda environment in the approved AWS account:

```text
REVIEW_BUCKET=<private review bucket>
REVIEW_PREFIX=artifacts/reviews/
REPORT_PREFIX=artifacts/reports/
REPORT_URL_TTL_SECONDS=900
ALLOWED_ORIGINS=https://<approved CloudFront domain>
```

Keep Lambda configuration at Python 3.12 / x86_64 and the API integration payload at 2.0. Attach the least-privilege execution role above. Configure an alias named `prod` and have API Gateway invoke that alias. After the function and alias already exist, a code-only release can be applied with:

```powershell
aws lambda update-function-code `
  --function-name $env:LAMBDA_FUNCTION `
  --zip-file fileb://backend/build/solarloss-lambda.zip
$version = aws lambda publish-version `
  --function-name $env:LAMBDA_FUNCTION `
  --description "SolarLoss release <git-sha>" `
  --query Version --output text
aws lambda update-alias `
  --function-name $env:LAMBDA_FUNCTION `
  --name prod `
  --function-version $version
```

Do not run these commands until the function, role, alias, and account are confirmed. No workflow deploys this ZIP automatically.

### API Gateway HTTP API

Configure routes and integration for payload format 2.0. Use the `$default` stage or a custom-domain API mapping that presents `/api/v1/...` to the Lambda; an unstripped named-stage prefix will not match the application's routes.

| Route                                        | Response                                                 |
| -------------------------------------------- | -------------------------------------------------------- |
| `GET /api/v1/health`                         | `200 {"status":"ok"}`                                    |
| `GET /api/v1/experiments`                    | Validated v0.1 experiment listing from the review prefix |
| `GET /api/v1/reviews/{experiment_id}`        | The validated stored artifact, unchanged                 |
| `GET /api/v1/reviews/{experiment_id}/report` | `302` to a short-lived S3 report download                |

Configure API Gateway CORS with the exact frontend origin, methods `GET` and `OPTIONS`, and header `Content-Type`. The browser's `Accept: application/json` request header is CORS-safelisted. Set the same exact origins in Lambda `ALLOWED_ORIGINS`; wildcard origins are rejected by the application. Ensure API errors are not rewritten to the frontend SPA document.

The API expects review objects at `artifacts/reviews/review_<experiment_id>.json`. The filename, `experiment.identifier`, and `review_id` must match the documented identity contract. Upload only an approved v0.1 artifact after running `python -m backend.validate_artifact <artifact-path>`.

### Frontend and CloudFront

Build the React app with the API origin, without an `/api/v1` suffix:

```powershell
cd web
npm ci
$env:VITE_API_BASE_URL = "https://<api-id>.execute-api.<region>.amazonaws.com"
npm run build
cd ..
```

Sync `web/dist/` to the confirmed private frontend bucket. CloudFront must use OAC, serve `index.html` as the default root, and support client-side routes such as `/experiments/shading_01`. Configure the static distribution's 403/404 SPA fallback to `/index.html` with a 200 response; keep API responses on the separate API origin so API errors and the report redirect are not rewritten or cached as HTML.

```powershell
$env:FRONTEND_BUCKET = "<confirmed-private-frontend-bucket>"
$env:CLOUDFRONT_DISTRIBUTION_ID = "<confirmed-distribution-id>"
aws s3 sync .\web\dist "s3://$env:FRONTEND_BUCKET" --delete
aws cloudfront create-invalidation `
  --distribution-id $env:CLOUDFRONT_DISTRIBUTION_ID `
  --paths "/index.html" "/assets/*"
```

The `--delete` sync applies to the named frontend bucket root. Confirm that it contains only this site's static build before using it. Keep each known-good build as an immutable release artifact so rollback does not depend on rebuilding old code.

## Cost controls

- Keep the Lambda ZIP small; it intentionally excludes analysis and ML packages. Set a request timeout and memory appropriate to JSON validation/report rendering, and a reserved-concurrency ceiling agreed with the owner.
- Set API Gateway throttles and CloudFront cache policies; do not cache API review or report responses.
- Set short CloudWatch log retention and an S3 lifecycle expiry for generated HTML reports. Keep review artifact retention/versioning separate.
- Create a monthly AWS Budget alert before serving traffic. Do not upload the raw research dataset to AWS as part of this deployment.
- Avoid NAT gateways, ML containers, and always-on compute for this artifact-serving application.

## Verify a release

Set the confirmed API and site origins first:

```powershell
$api = "https://<api-id>.execute-api.<region>.amazonaws.com"
$site = "https://<approved CloudFront domain>"
curl.exe --fail --silent --show-error "$api/api/v1/health"
curl.exe --fail --silent --show-error "$api/api/v1/experiments"
curl.exe --fail --silent --show-error --output NUL --write-out "%{http_code}`n" `
  "$site/experiments"
```

The health body must be `{"status":"ok"}`; the list must contain only stored, valid reviews; a client-side route must return the SPA. With an approved artifact ID, check the artifact and report path:

```powershell
$id = "<experiment.identifier from an approved artifact>"
curl.exe --fail --silent --show-error "$api/api/v1/reviews/$id" --output "$env:TEMP/solarloss-review.json"
curl.exe --fail --silent --show-error --location `
  "$api/api/v1/reviews/$id/report" `
  --output "$env:TEMP/solarloss-report.html"
```

The report request should return a downloadable HTML attachment through the API's 302 redirect. Run the backend artifact compatibility validator against the original artifact and downloaded JSON/report before announcing a demo. Do not substitute the Vite research preview for this check.

## Rollback

1. Point the existing `prod` Lambda alias back to the recorded previous published version with `aws lambda update-alias`; do not edit API integration to `$LATEST`.
2. Re-sync the previously retained `web/dist/` release artifact to the frontend bucket and invalidate `/index.html` and `/assets/*` in CloudFront.
3. Recheck `/api/v1/health`, the SPA deep link, one known valid review, and its report redirect.
4. If a schema or artifact change caused the failure, restore the previous compatible artifact version in S3 and preserve both S3 object versions for investigation.

## Failure cases to expect

| Symptom                                    | Likely cause                                                                                      |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| Health route returns 500                   | Lambda environment, handler, alias integration, or execution-role configuration is wrong.         |
| Review/list route returns 503              | S3 access, bucket/region, or network/service availability issue.                                  |
| Review/list route returns 500              | Stored JSON fails v0.1 schema, structural invariants, or identity checks.                         |
| Review route returns 404                   | No object exists at the exact `review_<id>.json` key.                                             |
| Browser reports a CORS error               | API Gateway and Lambda origin lists differ, or the request origin is not explicitly allowed.      |
| Deep link returns S3 XML/403/404           | CloudFront default root or SPA fallback is missing; check OAC bucket policy.                      |
| Report link fails after redirect           | Report-prefix IAM permissions, encryption, URL TTL, or browser/network access to S3 is incorrect. |
| UI shows no research preview in production | Expected: the preview is development-only and guarded from production bundles.                    |

No live endpoint, CloudFront distribution, bucket, or AWS identity is recorded in this repository. The infrastructure owner must fill and verify those values before deployment can be called ready.
