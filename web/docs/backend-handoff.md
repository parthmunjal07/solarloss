# Frontend/backend handoff

Production accepts schema v0.1.0 only. Proposed v0.2 responses fail frontend validation. No frontend change activates v0.2 serving.

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

Rachit must approve v0.2 metric meanings, null/reason semantics, populations, uncertainty and provenance before exporter/backend serving can change. See `analysis/SCHEMA_FEEDBACK_V2.md` and `docs/phase-3-scientific-v2-integration.md`. The frontend's development projection does not freeze the proposed contract.

## Live integration checks

Verify health, listing, identity, full schema and source equality against a compatible real v0.1 artifact. Click Export report and check the actual 302 followed by a private S3 HTML attachment. The frontend uses an anchor to the backend report route; it neither rewrites the signed URL nor creates a PDF. No deployed API URL or approved S3 review was supplied, so AWS download verification remains an infrastructure integration check.

## AWS hosting

Host `web/dist/` as static S3/CloudFront assets. Configure SPA fallback to `index.html` for deep links without rewriting `/api/*`. Route `/api/*` to API Gateway, or set `VITE_API_BASE_URL` to the API origin at build time. Cross-origin fetch needs the exact frontend origin in API Gateway/Lambda CORS. Report navigation must preserve the 302 Location and S3 attachment headers. Review/report buckets stay private. No credentials belong in the browser. No infrastructure/backend resources are changed here.
