# shading_01 bounded research release candidate

Status: **artifact-specific release authorized, separate approved copy strictly validated; AWS targets and access pending**. This directory does not activate production serving. The real local backend/frontend journey and HTML download pass on desktop and mobile.

`candidate/review_shading_01.json` is byte-identical to the committed historical V3 source (LF Git blob), SHA-256 `92ac86f3150c69d931d4a326b01eb3418c3f6cc1275ff965452e39e5e64b4c1e`. The parsed candidate equals the Windows working-tree source despite checkout line-ending conversion. No source export was overwritten. The manifest records the original commit, schema/protocol hashes, validation results and exact proposed storage key.

The [scientific decision sheet](../../../../docs/phase-4-scientific-decision-sheet.md) approves field definitions under `SOLARLOSS-SCI-V02-20261011-SEMANTICS`. Its release-gate interpretation explicitly requires a separate artifact signoff. That signoff was explicitly confirmed by the user as Rachit's authorization and recorded in the [artifact approval document](../../../../docs/phase-5-shading-01-release-approval.md) under `SOLARLOSS-SCI-V02-20261011-SHADING01-RELEASE`. The candidate stays proposed with a null owner record; `approved/review_shading_01.json` carries the genuine typed signoff. Its SHA-256 is `e4bc5e87841c63c0d6a247947b77fe193398ca3fbe87c446e502e286687da214`. Only `approval_status` and `decision.owner_review` changed; every other parsed field equals the original.

## Checks completed

- Exact approved schema SHA-256: `51001cac97423b454afac7b98ee733306666fe52e3ba22f5cb422ce987c461bd`; byte parity with analysis/backend/frontend contracts.
- Frozen protocol SHA-256: `457cc47db4989634b2de317e241b7744d47639c50d0c86c73f170b1376df0a4b`; equals source provenance.
- Strict backend JSON Schema, format and mechanical invariant validation; unchanged V3 exporter validation; actual backend HTML preview generation.
- Every original scientific field retained: 2,148 samples, 28 null expected-power values, measured/reference values, metric definitions/populations/calculations, uncertainty limitations, checksums and verification scope, label bounds and detector confirmations.
- Research verdict `LIMIT`, event review unavailable with null state, all technician checks proposed.
- Production loader rejects this proposed candidate both with the default gate and with the exact schema hash supplied. Offline preview is not an approved API response.

Reproduce from repository root:

```powershell
python analysis/tools/export_reviews_v3.py validate
python -m backend.validate_artifact artifacts/releases/v0.2.0/shading_01/candidate/review_shading_01.json --experimental-v2 --report-output "$env:TEMP/solarloss-release-candidate.html"
```

## Recorded artifact-specific signoff

The user explicitly confirmed: **“Rachit authorizes this exact bounded artifact release.”** This authorizes the separate release for **read-only, source-attributed, bounded research presentation**, with the exact candidate/schema/protocol hashes. Rachit is the recorded approver, the confirmation was recorded at `2026-10-11T05:33:44Z`, and the artifact-specific decision reference is separate from the semantics approval. `LIMIT`, unavailable event review, proposed checks and all existing limitations remain. Diagnosis, maintenance outcomes, detector deployment and recovered energy remain outside approval.

The release passes `load_versioned_review(..., approved_v02_schema_sha256=<exact hash>)`. Backend tests pin both file hashes and every preserved field; the default production gate still rejects the approved release until explicitly configured. The real `ReviewApplication` serves the exact approved JSON and listing through the loopback-only `backend.local_release_server` adapter. Playwright drives the production frontend and verifies the actual report 302, downloaded HTML, its content hash, research/event/check semantics and accessibility at 375/1280px. This adapter does not contact S3, mutate deployment environment variables or bypass approval validation.

Reproduce the approved integration:

```powershell
python -m pip install -r backend/requirements.txt
cd web
npm run build
npm run test:api
```

## Private storage and deployment handoff

The intended review key is `artifacts/reviews/review_shading_01.json`. Only the future approved release may be uploaded; **never upload this candidate into the live review prefix**. The infrastructure owner must identify and authorize the AWS account, region, private bucket, deployment workflow, Lambda/API Gateway, IAM permissions and frontend/CORS origins. Verify bucket public-access blocking, versioning and encryption; retain any previous object version for rollback. Generated report keys remain `artifacts/reports/shading_01/{sha256-of-html}.html`, with private short-lived attachment URLs.

Use the existing backend packaging and validation commands; no new backend fields or service dependencies are required. The user conditionally authorized deployment and gate activation after approval and validation, but supplied no AWS targets or access. The validated Python 3.12/x86_64 ZIP is locally prepared at `backend/build/solarloss-lambda.zip` (ignored build output), with the serving gate disabled in its manifest. After the actual deployment configuration is supplied and checked, deploy the package and add `APPROVED_REVIEW_SCHEMA_V02_SHA256` to the existing Lambda configuration while preserving all other settings. Then verify the actual private S3 read, exact review/listing responses, frontend journey and report 302/download. Keep the production variable unset until those conditions are met. No AWS upload, configuration change or production gate activation has occurred.
