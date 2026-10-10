# Public release checklist

**Status: owner review required before changing repository visibility or announcing a live service.** This pass did not change GitHub visibility, AWS resources, or a scientific schema.

## Audit findings by severity

### P0 — Critical

- None found in the bounded automated and source review.

### P1 — Resolve before public release or a live-demo claim

- [ ] **Project source license is missing.** `LICENSE`/`COPYING` is absent. Suggested owner decision: MIT is a reasonable permissive starting point for this small Python/TypeScript project; consider Apache-2.0 if an explicit contributor patent grant is desired. The MIT and Apache texts specify different reuse and patent terms; the owner must choose, confirm the copyright holder/contributor rights, and add the license. No license was selected or added in this pass. See the [OSI MIT text](https://opensource.org/license/mit) and [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0).
- [x] **Active dependency scans and test-tool update.** On 10 October 2026, `pip-audit` found pytest versions below 9.0.3 in the current science/backend test requirements. Those active requirements now use 9.0.3, which the [OSV advisory](https://osv.dev/vulnerability/PYSEC-2026-1845) identifies as fixed. `pip-audit` then found no known issues in the active science, backend development, or Lambda dependency sets; `npm audit` found zero issues in the locked frontend tree. The unchanged historical `requirements-v2-lock.txt` still records pytest 8.3.5 and the advisory. A dedicated Git-history secret scanner was not installed; the owner should still run one before public visibility.
- [ ] **Insufficient-evidence artifact identity mismatch.** The committed file `analysis/results/review_la-reunion_healthy-placebo-no-posttraining-shading_0.1.0.json` records `insufficient_evidence`, but its filename, `experiment.identifier`, and `review_id` disagree. The backend validator rejects it. Preserve the historical artifact; the science owner must provide a corrected, provenance-preserving artifact before it can be shown through the API.
- [ ] **AWS and demo are unverified.** No account, live API origin, CloudFront site, S3 review object, or downloadable report was available. Deployment and the AWS demo path remain blocked until the infrastructure owner deploys and verifies the documented stack.
- [ ] **Science-owner handoff remains open.** Review schema v0.1.0 is the current serving contract with provisional semantics. Schema v0.2.0, technician checks, and the new scientific handoff require explicit Rachit approval; do not enable v0.2 serving during a public release pass.
- [ ] **Confirm third-party distribution notices.** Dataset attribution is present and its source license is CC BY 4.0. The frontend bundles the Inter font under OFL-1.1 and now includes its license in `web/public/licenses/Inter-OFL-1.1.txt`; verify the production output retains it and review bundled JavaScript dependency notices before release.

### P2 — Maintainability and release polish

- [x] Add area-specific CI coverage and root setup/check instructions.
- [x] Document actual component ownership, schema boundary, scientific limitations, deployment target, and demo status.
- [ ] Large `model.py`, `review.py`, `report.py`, and `globals.css` files remain cohesive; split only when a future change gives a testable responsibility boundary. No broad refactor is justified now.
- [ ] The schema is represented in the producer, backend, and frontend because each validates the shared contract. Keep the copies in parity; do not “deduplicate” by introducing a runtime cross-language dependency.
- [ ] The preserved `analysis/requirements-v2-lock.txt` records the original run environment, including pytest 8.3.5. Keep it as historical provenance; use `analysis/requirements-v2.txt` for current installs and do not run the old test environment on a shared Unix host.

## Security and repository hygiene review

- The current worktree was clean before this pass. Redacted pattern scans covered **157 tracked/unignored working-tree files** and **193 reachable Git blobs across refs**. No high-confidence AWS key IDs/secrets, common GitHub/Slack/Google tokens, private-key blocks, or personal home-directory paths were found. This is a targeted pattern scan, not a substitute for the owner's dedicated secret scanner and human history review.
- No tracked `.env` file or raw source dataset was present. `.env.example` contains an empty API URL. Repository examples use placeholders; no production bucket identifier, account ID, or live endpoint was confirmed.
- Git tracks research notebooks and outputs because they preserve methods, source attribution, and reproducibility. The largest committed numeric result is `analysis/results/five_minute_evaluation_v2.csv` (about 12.9 MB); it is not a raw source dataset. Do not delete notebooks/results as cleanup.
- Build directories, `node_modules`, QA screenshots, and Playwright output are ignored in this checkout. The tracked `web/src/assets/hero.png` is decorative art, not a verified application screenshot.
- The review API uses explicit CORS origins, validates object identity, escapes HTML, and stores report downloads privately. Preserve these controls in any deployment.

## Data and code licensing

The La Réunion dataset is separately attributed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Preserve the dataset record/version, author attribution, and indication that derived material is based on that source, as recorded in [`analysis/DATA_PROVENANCE.md`](analysis/DATA_PROVENANCE.md). This does not license SolarLoss source code. The proposed code-license choice remains an owner decision; do not imply the dataset license applies to the repository.

## Owner approval and release sequence

1. Confirm contributor/copyright ownership and choose/add the source-code license.
2. Run a dedicated secret scan over the full Git history and a Python dependency audit; resolve any findings before making the repository public.
3. Approve attribution/notice handling for bundled dependencies and retain CC BY 4.0 dataset attribution.
4. Decide whether and when to approve scientific v0.2 semantics; keep production v0.1 if the handoff is still open.
5. Have the infrastructure owner deploy and verify the API, private buckets, explicit CORS, CloudFront SPA behavior, report redirect, IAM policy, logs, and cost controls.
6. Repair or supersede the mismatched insufficient-evidence artifact through the science owner; then verify the real API review and HTML download.
7. Add a screenshot, live demo URL, or video URL only after checking the deployed page and submission link directly.
8. Obtain explicit repository-owner approval before changing GitHub visibility. This pass intentionally did not change it.
