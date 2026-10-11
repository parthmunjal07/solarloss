type Interval = { start: string; end: string };
type Confirmations = Partial<
  Record<"1_minute" | "5_minute_primary" | "15_minute_sensitivity", string>
>;
type EventReview =
  | { availability: "unavailable"; state: null; reason: string }
  | {
      availability: "available";
      state: "supported_change" | "inconclusive" | "insufficient_evidence";
      reason: string;
    };
export interface ApprovalRecord {
  approver: string;
  approved_at: string;
  schema_version: "0.2.0";
  schema_sha256: string;
  protocol_sha256: string;
  decision_reference: string;
  scope: string;
}
type Experiment = { identifier: string; start: string; end: string } & (
  | {
      type: "documented_shading";
      event_context: {
        label_interval_utc: Interval | null;
        label_source: string;
        label_description: string;
        detector_confirmations_utc: Confirmations;
        detector_latency_seconds_from_first_label: Partial<
          Record<keyof Confirmations, number>
        >;
      };
    }
  | {
      type: "healthy_stability";
      event_context: {
        label_interval_utc: null;
        label_source: string;
        detector_calibration_population: boolean;
        observed_raw_support_utc: Interval;
        note: string;
      };
    }
);
type Unit = "W" | "kWh" | "1" | "alarms/hour";
export interface ReviewMetric {
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
  availability: "estimated" | "unavailable" | "not_applicable";
  value: number | null;
  unit: Unit;
  reason: string | null;
  population: string;
  definition: string;
  calculation: string;
  coverage: {
    valid_seconds: number | null;
    observed_labelled_seconds: number | null;
    wall_span_seconds: number | null;
  };
  ratio: {
    numerator: number;
    denominator: number;
    numerator_unit: string;
    denominator_unit: string;
  } | null;
  uncertainty: {
    kind:
      "empirical_model_error_band" | "day_bootstrap_interval" | "not_estimated";
    method: string;
    unit: Unit;
    lower: number | null;
    upper: number | null;
    group_count: number;
    limitations: string[];
  } | null;
}
export interface ReviewV2 {
  schema_version: "0.2.0";
  approval_status: "proposed" | "owner_approved";
  review_id: string;
  experiment: Experiment;
  provenance: {
    protocol_sha256: string;
    source_checksums: Array<{
      file: string;
      md5: string;
      sha256: string;
      byte_count: number;
      role:
        | "pinned Zenodo record 7291380 source file"
        | "committed V2 analysis input"
        | "synthetic test fixture; not source evidence";
      source_verification: string;
    }>;
    model: {
      name: string;
      target: string;
      predictors: string[];
      intercept_w: number;
      coefficients: Record<string, number>;
      training_rows: number;
      preprocessing: string;
      expected_power_semantics: string;
    };
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
      label_interval: Interval | null;
      detector_confirmations: Confirmations;
      label_source: string;
      episode_gap_rule_seconds: number;
      event_review_decision: EventReview;
      notes: string;
    };
    label_use: string;
    exclusions: Array<Interval & { reason: string }>;
    retrospective: true;
    code_version: string;
  };
  metrics: ReviewMetric[];
  series: {
    timestamp_basis: "UTC";
    power_unit: "W";
    downsampling: {
      method: string;
      source_count: number;
      retained_count: number;
      gap_markers: Array<
        Interval & { duration_seconds: number; reason: string }
      >;
    };
    samples: Array<{
      timestamp: string;
      measured_power: number | null;
      raw_reference_power: number | null;
      expected_power: number | null;
      valid: boolean;
    }>;
  };
  electrical_evidence: Array<{
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
  }>;
  candidate_checks: Array<{
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
  }>;
  decision: {
    verdict: "GO" | "LIMIT" | "REJECT";
    reasons: string[];
    rule_version: string;
    owner_review: ApprovalRecord | null;
    event_review: EventReview;
  };
  limitations: string[];
}
