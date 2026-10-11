# shading_01 artifact-specific bounded research release

**Decision: artifact-specific release authorized by Rachit, as explicitly confirmed by the user in the project conversation.** This is separate from the earlier approval of scientific field definitions. No historical export was edited.

- Approver: Rachit, designated SolarLoss science owner. The user confirmed the exact artifact-specific authorization requested below.
- Approval recorded at: `2026-10-11T05:33:44Z` UTC. This is the recording time of the confirmation, not a reused semantics-approval timestamp.
- Decision reference: `SOLARLOSS-SCI-V02-20261011-SHADING01-RELEASE`.
- Exact candidate: `artifacts/releases/v0.2.0/shading_01/candidate/review_shading_01.json`.
- Candidate/committed source SHA-256: `92ac86f3150c69d931d4a326b01eb3418c3f6cc1275ff965452e39e5e64b4c1e`, hashing the LF Git blob, not the Windows CRLF checkout.
- Schema version: `0.2.0`; approved schema SHA-256: `51001cac97423b454afac7b98ee733306666fe52e3ba22f5cb422ce987c461bd`.
- Frozen protocol SHA-256: `457cc47db4989634b2de317e241b7744d47639c50d0c86c73f170b1376df0a4b`.
- Field-definition approval: [scientific decision sheet](phase-4-scientific-decision-sheet.md), `SOLARLOSS-SCI-V02-20261011-SEMANTICS`.
- Separate output: `artifacts/releases/v0.2.0/shading_01/approved/review_shading_01.json`; exact output hash is recorded in the [release manifest](../artifacts/releases/v0.2.0/shading_01/release-manifest.json).

## Traceable authorization

After the exact candidate was prepared and strictly validated, the user was asked to confirm Rachit's authorization to release the named candidate/hash for read-only bounded research presentation, creating a separate owner-approved copy and changing only `approval_status` and `decision.owner_review`. The request expressly preserved `LIMIT`, unavailable event review, proposed checks and every scientific limitation, and excluded AWS deployment authorization.

The user's explicit confirmation was:

> Rachit authorizes this exact bounded artifact release

The release record attributes the science-owner approval to Rachit as confirmed by the user; it does not assert an independently authenticated external signature or invent a broader approval.

## Authorized scope and preserved findings

Read-only, source-attributed, bounded retrospective research presentation of this exact `shading_01` artifact. The release changes only its top-level approval status and typed artifact-owner review record. All other parsed fields are checked for equality against the candidate and original source.

The research verdict remains `LIMIT`. Event-level review remains unavailable with a null state and the original reason. Technician checks remain proposed/unapproved. Preserve all measured/reference/model-expected power channels, 28 null expected-power samples, exact energy estimands and coverage populations, model-error limitations, label bounds and detector confirmations, contextual electrical evidence, checksums and provenance-verification scopes.

This authorization does not approve fault diagnosis, maintenance outcomes, detector generalisation or deployment readiness, causal/recovered electricity, commercial savings, or other research artifacts. The healthy example and data-gap sidecar have not been promoted by this decision.

## Deployment authorization and remaining dependencies

The user separately replied **“yes”** to authorizing deployment and gate activation once artifact signoff and validation pass. That conditional workflow authorization is recorded; it does not identify an AWS account, region, bucket, Lambda/API Gateway, frontend origin or API URL. Inspection found no AWS profile, credentials, region or configured deployment targets in this workspace. No S3 upload or AWS configuration change has occurred. The actual production environment variable remains unset.

Local integration may enable the approved hash only in an isolated `ReviewApplication` instance using this genuine approved release. It must not substitute a research preview, synthetic approval or locally generated report URL as evidence of private S3 deployment. AWS release requires the actual targets and authenticated access, followed by private-storage and deployed-journey verification documented in the [release handoff](../artifacts/releases/v0.2.0/shading_01/README.md).
