# Phase 4 frontend handoff: candidate v0.2

**Status: implementation contract only; not approved or live.** The backend currently serves v0.1 only. Do not add v0.2 to the frontend's production parser or treat this proposal as science-owner signoff. Source fixtures are the unchanged [shading review](../analysis/results/reviews_v3/review_shading_01.json) and [zero-labelled comparison](../analysis/results/reviews_v3/review_healthy_20220126_0300.json).

## Candidate API responses

After the scientific approval and deployment gates are cleared, `GET /api/v1/reviews/shading_01` returns the complete source review object unchanged. The object is the committed exporter file above; these excerpts show exact source fields, not a second or normalized verdict:

```json
{
  "schema_version": "0.2.0",
  "approval_status": "proposed",
  "review_id": "review_shading_01",
  "experiment": {
    "identifier": "shading_01",
    "type": "documented_shading",
    "start": "2022-02-08T07:11:02Z",
    "end": "2022-02-08T10:09:56Z",
    "event_context": {
      "label_interval_utc": {
        "start": "2022-02-08T07:11:02Z",
        "end": "2022-02-08T10:09:56Z"
      },
      "detector_confirmations_utc": {
        "1_minute": "2022-02-08T07:12:00Z",
        "5_minute_primary": "2022-02-08T07:20:00Z",
        "15_minute_sensitivity": "2022-02-08T07:30:00Z"
      },
      "detector_latency_seconds_from_first_label": {
        "1_minute": 58,
        "5_minute_primary": 538,
        "15_minute_sensitivity": 1138
      },
      "label_source": "dt2_electrical_production_inverter_1_with_faults.csv:Fault; source metadata table 3; label 2.1",
      "label_description": "Constant partial shading, entire module; 1 shaded module"
    }
  },
  "decision": {
    "verdict": "LIMIT",
    "rule_version": "frozen-v2-research-gates-2026-10-10",
    "event_review": {
      "availability": "unavailable",
      "state": null,
      "reason": "Unavailable: the event has documented intervention label 2.1 and measured-versus-modelled evidence, but no true unshaded target counterfactual; reference mismatch, operating state and sensor alternatives are not ruled out. Do not assign supported_change solely from Fault=2.1."
    },
    "owner_review": null
  }
}
```

The production `GET /api/v1/experiments` candidate item should expose the two decision levels separately. Its precise proposed v0.2 listing shape is:

```json
{
  "experiment_id": "shading_01",
  "review_id": "review_shading_01",
  "schema_version": "0.2.0",
  "experiment_type": "documented_shading",
  "time_window": {
    "start": "2022-02-08T07:11:02Z",
    "end": "2022-02-08T10:09:56Z"
  },
  "research_verdict": "LIMIT",
  "event_review": {
    "availability": "unavailable",
    "state": null,
    "reason": "Unavailable: the event has documented intervention label 2.1 and measured-versus-modelled evidence, but no true unshaded target counterfactual; reference mismatch, operating state and sensor alternatives are not ruled out. Do not assign supported_change solely from Fault=2.1."
  }
}
```

The listing shape above is a frontend/API proposal, not a current backend response. `LIMIT` must never map to `insufficient_evidence`; no event state has been assigned in either genuine review.

## Field-level TypeScript handoff

```ts
type Availability = "estimated" | "unavailable" | "not_applicable";
type ResearchVerdict = "GO" | "LIMIT" | "REJECT";
type EventReviewState = "supported_change" | "inconclusive" | "insufficient_evidence";

interface AvailableEventReview {
  availability: "available";
  state: EventReviewState;
  reason: string | null;
}

interface UnavailableEventReview {
  availability: "unavailable";
  state: null;
  reason: string;
}

interface ReviewMetric {
  id:
    | "healthy_mae"
    | "healthy_nmae"
    | "healthy_bias"
    | "episode_recall"
    | "healthy_alarm_runs_per_hour"
    | "signed_generation_deviation"
    | "positive_only_generation_deviation"
    | "observed_energy"
    | "expected_energy";
  availability: Availability;
  value: number | null;
  unit: "W" | "kWh" | "1" | "alarms/hour";
  population: string;
  definition: string;
  calculation: string;
  reason: string | null;
  coverage: {
    valid_seconds: number | null;
    observed_labelled_seconds: number | null;
    wall_span_seconds: number | null;
  };
  ratio: null | {
    numerator: number;
    denominator: number;
    numerator_unit: string;
    denominator_unit: string;
  };
  uncertainty: null | {
    // The containing metric.id is the typed estimand.
    kind: "empirical_model_error_band" | "day_bootstrap_interval" | "not_estimated";
    method: string;
    unit: string;
    lower: number | null;
    upper: number | null;
    group_count: number;
    limitations: string[];
  };
}

interface ApprovalRecord {
  approver: string;
  approved_at: string; // RFC 3339 UTC, serialized with Z
  schema_version: "0.2.0";
  schema_sha256: string;
  protocol_sha256: string;
  decision_reference: string;
  scope: string;
}

type EventContext =
  | {
      label_interval_utc: { start: string; end: string };
      label_source: string;
      label_description: string;
      detector_confirmations_utc: {
        "1_minute": string;
        "5_minute_primary": string;
        "15_minute_sensitivity": string;
      };
      detector_latency_seconds_from_first_label: {
        "1_minute": number;
        "5_minute_primary": number;
        "15_minute_sensitivity": number;
      };
    }
  | {
      label_interval_utc: null;
      label_source: string;
      detector_calibration_population: boolean;
      observed_raw_support_utc: { start: string; end: string };
      note: string;
    };

interface SourceChecksum {
  file: string;
  md5: string; // lowercase 32-hex digest
  sha256: string; // lowercase 64-hex digest
  role:
    | "pinned Zenodo record 7291380 source file"
    | "committed V2 analysis input";
  source_verification: string;
  byte_count: number;
}

interface ModelProvenance {
  name: string;
  target: string;
  predictors: string[];
  intercept_w: number;
  coefficients: Record<string, number>;
  training_rows: number;
  preprocessing: string;
  expected_power_semantics: string;
}

interface ReviewProvenance {
  protocol_sha256: string;
  source_checksums: SourceChecksum[];
  model: ModelProvenance;
  splits: {
    train: [string, string];
    selection: [string, string];
    calibration: [string, string];
    protected_start: string;
  };
  thresholds: {
    primary_window_minutes: 1 | 5 | 15;
    persistence_windows: number;
    statistic: string;
    by_window_minutes: { "1": number; "5": number; "15": number };
    calibration_population: string;
  };
  evaluation_population: string;
  grouping: {
    label_interval: { start: string; end: string } | null;
    detector_confirmations: Record<string, string>;
    label_source: string;
    episode_gap_rule_seconds: number;
    event_review_decision: AvailableEventReview | UnavailableEventReview;
    notes: string;
  };
  label_use: string;
  exclusions: Array<{ start: string; end: string; reason: string }>;
  retrospective: true;
  code_version: string;
}

interface ElectricalEvidence {
  signal: "Va" | "Ia" | "Ig" | "Vg" | "Fg";
  measurement: number | null;
  unit: "V" | "A" | "Hz";
  quality: string;
  comparison_population: string;
  supports: string;
  does_not_prove: string;
  alternatives: string[];
  missing_measurements: string[];
  strength: "SUPPORTED" | "LIMITED" | "UNSUPPORTED";
}

interface CandidateCheck {
  id: string;
  observed_fact: string;
  hypothesis: string;
  supporting_evidence: string[];
  opposing_evidence: string[];
  next_information: string[];
  qualification: string;
  safety_constraint: string;
  sources: string[];
  status: "proposed" | "owner_approved" | "unavailable";
  approval?: ApprovalRecord | null;
}

interface ReviewV02 {
  schema_version: "0.2.0";
  approval_status: "proposed" | "owner_approved";
  review_id: string;
  experiment: {
    identifier: string;
    type: "documented_shading" | "healthy_stability";
    start: string; // RFC 3339 UTC, serialized with Z
    end: string;
    event_context: EventContext;
  };
  provenance: ReviewProvenance;
  metrics: ReviewMetric[];
  series: {
    timestamp_basis: "UTC";
    power_unit: "W";
    downsampling: {
      method: string;
      source_count: number;
      retained_count: number;
      gap_markers: Array<{ start: string; end: string; duration_seconds: number; reason: string }>;
    };
    samples: Array<{
      timestamp: string;
      measured_power: number | null;
      raw_reference_power: number | null;
      expected_power: number | null;
      valid: boolean;
    }>;
  };
  electrical_evidence: ElectricalEvidence[];
  candidate_checks: CandidateCheck[]; // proposed prompts; render status and boundaries
  decision: {
    verdict: ResearchVerdict;
    rule_version: string;
    reasons: string[];
    owner_review: ApprovalRecord | null;
    event_review: AvailableEventReview | UnavailableEventReview;
  };
  limitations: string[];
}

interface ExperimentListItemV02 {
  experiment_id: string;
  review_id: string;
  schema_version: "0.2.0";
  experiment_type: ReviewV02["experiment"]["type"];
  time_window: { start: string; end: string };
  research_verdict: ResearchVerdict;
  event_review: AvailableEventReview | UnavailableEventReview;
}
```

The `Record<string, unknown>` placeholders above are not permission to render unvalidated nested data. The backend schema closes and types those objects; frontend production types should mirror that schema before activation.

## Metric labels and values for `shading_01`

| Metric id | Display label | Exact source value | Required context |
| --- | --- | ---: | --- |
| `observed_energy` | Measured target AC energy | 2.381648888888889 kWh | Same 10,549 valid source-record seconds as expected energy |
| `expected_energy` | Model-expected target AC energy | 2.778697866302768 kWh | Calibrated expected target, not raw reference Pg |
| `signed_generation_deviation` | Signed model-expected minus measured generation deviation | 0.39704897741387934 kWh | Negative values are valid; not causal loss or recovery |
| `positive_only_generation_deviation` | Positive-only model-expected minus measured generation deviation | 0.3971261454108439 kWh | Nonnegative; not verified recoverable electricity or savings |

The signed identity reconciles: expected energy minus measured energy equals signed deviation within floating point tolerance. The 0.37014211825708937–0.3948064694632774 kWh uncertainty bounds are empirical matched-placebo model-error context, not a causal confidence interval. Shading coverage values are 10,549 valid seconds, 10,734 observed labelled seconds, and 10,734 wall-span seconds. If displaying a percentage, name the denominator beside it.

## Provenance, timestamps, checks, and reports

- Keep target measured Pg, raw comparison-inverter Pg, and calibrated model-expected target Pg as separate W-valued series. A sample with `valid: false` and `expected_power: null` remains unavailable; do not chart it as zero or bridge an explicit gap.
- In `shading_01`, 28 of 2,148 retained samples are invalid because `expected_power` is null; measured and raw-reference values remain available. The source has no per-sample missing-channel reason and its gap-marker list is empty. Render the null as a break and do not guess why the estimate is unavailable. Rachit should decide whether a future exporter version adds channel-specific validity and reason codes.
- Source intervention interval is 2022-02-08 07:11:02–10:09:56 UTC. The primary five-minute detector confirms at 07:20:00 UTC. The 1-minute and 15-minute values are sensitivity outputs. Render the intervention band separately from detector markers.
- Source checksums include the verification scope. Do not state that V3 rehashed the raw Zenodo files; raw bytes were unavailable to that export run. Committed V2 analysis inputs were rehashed.
- Render the 2022-01-26 example as zero-labelled and inside detector calibration. Do not describe it as independently certified fault-free or as a holdout.
- Candidate technician checks have `status: "proposed"`. Keep observed fact, hypothesis, evidence for and against, next information, qualification, safety constraint, and source together. Do not show a diagnosis badge or repair action.
- Electrical evidence is currently a window-level comparison summary; individual measurements have no timestamp/interval field. Present it as contextual summary evidence, not as a timestamped trigger. A future actionable prompt requires Rachit's decision about explicit temporal support.
- A not-estimated value uses `availability: "unavailable"` or `"not_applicable"`, `value: null`, and a reason. Never replace null with zero.
- Report export remains `GET /api/v1/reviews/{id}/report` and returns a 302 to a short-lived private S3 URL. The HTML attachment must preserve provenance, availability reasons, separate research/event status, label and detector times, and proposed status. URLs and all artifact text are untrusted display content and must be escaped.
- The insufficient-data gap sidecar is not a v0.2 review and must not appear in the experiment listing unless its own versioned case contract is approved.
