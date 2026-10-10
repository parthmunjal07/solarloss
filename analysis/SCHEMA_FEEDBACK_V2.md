# Backend handoff and proposed v0.2 semantics

Status: proposal only; Rachit approves scientific semantics before the backend contract is frozen. No backend/, web/ or infra/ files are changed. No production review artifact, upload or deployment is performed.

The current main backend correctly treats artifacts as producer-supplied precomputed evidence, validates identities and does not run ML. Its v0.1 mandatory numeric energy_deficit cannot express unavailable shading energy. The historical healthy-placebo export remains unchanged for provenance, but should not be displayed as shading loss. Updated research code refuses an unapproved production review export and refuses substituting a healthy placebo when shading is unavailable. V2 research JSONs are intentionally not v0.1 review artifacts.

Identity correction: review_identity(experiment_id) derives review_id='review_'+experiment_id and filename=review_id+'.json'. Exporter uses the artifact's experiment.identifier for both. No date/version independently embedded in another identity. Tests enforce this convention. Private legacy placebo construction is retained only as historical implementation context; the public export path cannot call it for unavailable shading.

## Proposed contract

See contracts/review.schema.v0.2.0.proposed.json for a reviewable draft. It is not installed into the backend. Use distinct metric identifiers for healthy MAE/nMAE/bias, recall, healthy alarm-run rate, signed generation deviation, positive-only generation deviation, observed and expected energy. No metric is named recovered electricity or savings. Every metric identifies its unit, evaluated population, definition and calculation. availability=unavailable requires value=null and a reason; availability=estimated requires a finite numeric value and reason=null. Signed energy may be negative. Positive-only energy cannot be negative and never proves abnormality. Fractions require explicit numerator/denominator with units. No unavailable value may display as zero.

Coverage has distinct valid elapsed seconds, observed labelled support and event wall span. Energy must use raw elapsed-time integration, never the downsampled display series. Uncertainty declares kind: empirical healthy-model-error band versus day-bootstrap interval. It never presents a placebo range as a counterfactual-loss confidence interval. Record group count and dependence limitations; unavailable bounds remain null. Application validation must enforce paired ordered bounds and unique metric identifiers, and reject NaN/Infinity.

Provenance records source hashes, protocol SHA256, code version, coefficients/features, whole-day split boundaries, selection population/rules, frozen thresholds/window sizes/persistence, predictor screens, label use, grouping, counts, retrospective design and exclusions. Electrical evidence carries sensor semantics, measured value/unit, comparison population, requirements, support, non-proof, alternatives and strength. Candidate checks carry observed facts separately from hypotheses, evidence for/against, missing next information, qualification/safety constraints, primary references and proposal/approval status. These are technician investigation prompts, not diagnoses.

## Exact integration work after approval

1. Owner resolves metric definitions, electrical wording and proposed enums. Backend owner adds a versioned v0.2 validator/renderer alongside v0.1 with explicit version dispatch. Retain historical artifacts.
2. Add invariants for filename/review/experiment identity agreement, unique metric identity, null/availability semantics, finite values, numerator/denominator population consistency, ordered uncertainty bounds, chronological series and gap markers.
3. Science exporter produces an owner-approved event-specific artifact under review_<experiment_id>.json, with validated original raw-derived energy and compact display series. Run the existing local backend compatibility tool against the corresponding new version before upload.
4. Frontend shows signed deviation, positive-only deviation and healthy calibration as separate labelled metrics; unavailable values get a reason; physical labels and automatic alarms use different visual marks. Show scope, coverage and uncertainty type. Ig is not independent corroboration of Pg.
5. Infrastructure owner handles existing versioned storage/deployment procedures only after compatibility validation and approvals. This scientific package makes no infrastructure change.

Draft schema tests verify negative signed values, forbidden negative positive-only values, and unavailable-null rules. JSON Schema cannot alone establish scientific validity, authorization, cross-field identity equality or true causal interpretation.
