# Frontend/backend handoff

Phase 5: the production frontend accepts v0.1 and artifact-approved v0.2 API responses. No frontend change promotes an artifact or activates backend serving. The semantics approval (`SOLARLOSS-SCI-V02-20261011-SEMANTICS`) is distinct from each stored artifact's owner-review record.

The browser lazily validates v0.2 against a byte-identical copy of the approved schema (SHA-256 `51001cac97423b454afac7b98ee733306666fe52e3ba22f5cb422ce987c461bd`). It requires `approval_status: owner_approved`, a complete owner-review record with that schema hash and a protocol hash matching the artifact. Proposed files, missing/mismatched approval records, available event decisions and owner-approved technician checks are outside this bounded release and are rejected. No frontend code generates approval metadata. Genuine V3 fixtures are test-only filesystem reads; production contains schema definitions and no research measurements.

Ready for the backend's promoted artifacts: mixed v0.1/v0.2 listings; all three power channels; exact source energy totals; distinct signed/positive-only labels; original-duration populations; null estimate gaps with measured/reference values retained; label bounds separate from primary detector confirmation; LIMIT and unavailable event review; metric ratios/uncertainty; model coefficients/splits/thresholds; hash verification scopes; contextual electrical summaries; proposed checks with supporting/opposing evidence, next information, qualification, safety and sources; the genuine HTML report route. v0.2 report details are available in both reading modes. The 3D view is explanatory and needs no new backend fields.

Backend owner: promote and verify each artifact separately, enforce the approved schema hash gate, serve the approved stored bytes unchanged, and verify the report endpoint's 302/HTML. Infrastructure owner: supply the real API origin, private store, deployment and exact-origin CORS. The browser's approval validation is an additional display boundary, not a substitute for server enforcement or authentication.

| Missing source field                               | Screen        | Expected type and scientific source                                         | Current behavior                                               |
| -------------------------------------------------- | ------------- | --------------------------------------------------------------------------- | -------------------------------------------------------------- |
| Observed/expected energy                           | Investigation | Availability-aware kWh metric from original science integration             | Not available; never reconstructed from chart points           |
| Signed/positive-only deviation semantics           | Investigation | Approved metric definitions and population                                  | v0.1 deficit explicitly provisional, never shading loss        |
| Per-sample signed residual                         | Analyst chart | Timestamped source expected-minus-measured values with unit                 | Unavailable for v0.1; preview reads committed CSV residual     |
| Intervention boundaries and detector confirmations | Chart         | Separate label intervals and detector timestamps                            | v0.1 unavailable; no inference from review window              |
| Dataset metadata in listing                        | Explorer      | Dataset name/source/version, extraction/checksums                           | Read existing individual review endpoint, reuse query cache    |
| Cadence / maximum supported gap                    | Chart         | Explicit science-owned elapsed-time rule, seconds                           | v0.1 uses flags/exclusions; preview uses frozen 18-second rule |
| Model coefficients and training splits             | Analyst       | Scientific provenance object                                                | v0.1 unavailable; committed split dates shown in preview       |
| Technician checks                                  | Report        | Approved observations, alternatives, source, qualification, approval record | v0.1 unavailable; preview E5 proposals visibly unapproved      |
| Three-state event review decision                  | Report        | Approved state, reasons, rules, approval provenance                         | Preview unavailable; research LIMIT stays separate             |
| Event-specific exclusion intervals                 | Analyst       | Timed scientific exclusions with reasons                                    | Only supplied records shown; no fabricated count/duration      |

The table above records the original v0.1 dependencies. Rachit has now approved v0.2 field meanings for bounded research presentation. Remaining science dependencies: per-channel missingness reasons (not supplied for the 28 invalid shading estimates), temporal support for electrical summaries, and any future event decisions or technician-check approval. The data-gap sidecar remains outside the approved review/listing types. No unsupported reason, timestamp or state is inferred.

## Live integration checks

Verify health, listing, identity, full schema and source equality against a compatible real v0.1 artifact. Click Export report and check the actual 302 followed by a private S3 HTML attachment. The frontend uses an anchor to the backend report route; it neither rewrites the signed URL nor creates a PDF. No deployed API URL or approved S3 review was supplied, so AWS download verification remains an infrastructure integration check.

## AWS hosting

Host `web/dist/` as static S3/CloudFront assets. Configure SPA fallback to `index.html` for deep links without rewriting `/api/*`. Route `/api/*` to API Gateway, or set `VITE_API_BASE_URL` to the API origin at build time. Cross-origin fetch needs the exact frontend origin in API Gateway/Lambda CORS. Report navigation must preserve the 302 Location and S3 attachment headers. Review/report buckets stay private. No credentials belong in the browser. No infrastructure/backend resources are changed here.
