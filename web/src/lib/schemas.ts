import { z } from "zod";

const text = z.string().min(1);
export const identifier = z.string().regex(/^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$/);
const date = z.iso.datetime({ offset: true });
const number = z.number().finite();
const quantity = z.strictObject({ value: number, unit: text });
const system = z.strictObject({ identifier: text, description: text });
const window = z.strictObject({ start: date, end: date });
export const decisionState = z.enum([
  "supported_change",
  "inconclusive",
  "insufficient_evidence",
]);
export const sampleSchema = z
  .strictObject({
    timestamp: date,
    measured_power: number.nullable(),
    raw_reference_power: number.nullable(),
    expected_power: number.nullable(),
    valid: z.boolean(),
    expected_lower_bound: number.optional(),
    expected_upper_bound: number.optional(),
  })
  .superRefine((s, ctx) => {
    if (
      s.valid &&
      [s.measured_power, s.raw_reference_power, s.expected_power].some(
        (v) => v === null,
      )
    )
      ctx.addIssue({
        code: "custom",
        message: "Valid samples require all three power measurements",
      });
    if (
      (s.expected_lower_bound === undefined) !==
      (s.expected_upper_bound === undefined)
    )
      ctx.addIssue({
        code: "custom",
        message: "Expected bounds must be paired",
      });
    if (
      s.expected_lower_bound !== undefined &&
      s.expected_upper_bound !== undefined &&
      s.expected_lower_bound > s.expected_upper_bound
    )
      ctx.addIssue({ code: "custom", message: "Expected bounds are reversed" });
  });
const ratio = z.strictObject({
  value: number,
  unit: text,
  numerator: quantity,
  denominator: quantity,
  calculation: z.string().optional(),
});
const finding = z.strictObject({
  name: text,
  status: z.enum(["passed", "failed", "not_evaluated", "reported"]),
  detail: text,
  result: z.string().optional(),
  synthetic: z.boolean().optional(),
});
const comparison = z.strictObject({ name: text, value: number });
export const reviewV1Schema = z
  .strictObject({
    schema_version: z.literal("0.1.0"),
    review_id: z.string().regex(/^review_[A-Za-z0-9][A-Za-z0-9._-]{0,99}$/),
    analysis_version: text.max(100),
    produced_at: date,
    dataset: z.strictObject({
      name: text,
      source: z
        .url()
        .refine(
          (v) => /^https?:\/\//i.test(v),
          "Dataset source must use HTTP(S)",
        ),
      version: text,
      extraction_date: z.iso.date().optional(),
      checksums: z
        .array(z.strictObject({ algorithm: text, digest: text, scope: text }))
        .min(1),
    }),
    experiment: z.strictObject({
      identifier,
      type: text,
      experimental_system: system,
      reference_system: system,
      time_window: window,
      label_provenance: z.strictObject({
        source: text,
        method: text,
        label: text,
        reference: z.string().optional(),
      }),
    }),
    series: z.strictObject({
      timestamp_basis: z.literal("UTC"),
      power_unit: text,
      samples: z.array(sampleSchema).min(1),
    }),
    metrics: z.strictObject({
      energy_deficit: z.strictObject({
        value: number,
        unit: text,
        calculation: text,
      }),
      deficit_fraction: ratio,
      coverage: ratio,
      calibration_error: z.strictObject({
        value: number,
        unit: text,
        statistic: text,
        evaluation_population: z.literal("held_out_healthy"),
        numerator: quantity.optional(),
        denominator: quantity,
      }),
      valid_interval_count: z.number().int().nonnegative(),
      total_interval_count: z.number().int().positive(),
    }),
    baseline_comparison: z.strictObject({
      metric: text,
      unit: text,
      evaluation_population: text,
      simple_baseline: comparison,
      calibrated_reference: comparison,
      reported_difference: quantity.optional(),
      calculation: z.string().optional(),
    }),
    uncertainty: z.strictObject({
      method: text,
      independent_blocks: z.strictObject({
        count: z.number().int().nonnegative(),
        unit: text,
      }),
      interval: z
        .strictObject({
          level: number.gt(0).lt(1),
          lower: number,
          upper: number,
          unit: text,
        })
        .nullable()
        .optional(),
      not_estimated_reason: z.string().optional(),
      exploratory: z.boolean(),
      limitations: z.array(text),
    }),
    quality_checks: z.array(finding),
    exclusions: z.array(
      z.strictObject({ start: date, end: date, reason: text }),
    ),
    decision: z.strictObject({
      state: decisionState,
      reasons: z.array(text),
      rules_version: text,
    }),
    limitations: z.array(text),
    robustness: z.strictObject({
      status: z.enum(["evaluated", "not_evaluated"]),
      findings: z.array(finding.extend({ synthetic: z.boolean() })),
    }),
    placebo: z.strictObject({
      status: z.enum(["evaluated", "not_evaluated"]),
      findings: z.array(finding),
    }),
  })
  .superRefine((r, ctx) => {
    if (r.review_id !== `review_${r.experiment.identifier}`)
      ctx.addIssue({
        code: "custom",
        message: "Review and experiment identifiers disagree",
      });
    if (
      Date.parse(r.experiment.time_window.end) <=
      Date.parse(r.experiment.time_window.start)
    )
      ctx.addIssue({ code: "custom", message: "Invalid experiment interval" });
    if (
      r.series.samples.some(
        (s, i, a) =>
          i > 0 && Date.parse(s.timestamp) <= Date.parse(a[i - 1].timestamp),
      )
    )
      ctx.addIssue({
        code: "custom",
        message: "Samples must be strictly chronological",
      });
    if (r.metrics.valid_interval_count > r.metrics.total_interval_count)
      ctx.addIssue({
        code: "custom",
        message: "Valid count exceeds total count",
      });
    if (
      r.uncertainty.interval &&
      r.uncertainty.interval.lower > r.uncertainty.interval.upper
    )
      ctx.addIssue({
        code: "custom",
        message: "Uncertainty interval is reversed",
      });
    if (r.exclusions.some((e) => Date.parse(e.start) >= Date.parse(e.end)))
      ctx.addIssue({
        code: "custom",
        message: "Excluded interval is reversed",
      });
  });
export const experimentSchema = z.strictObject({
  experiment_id: identifier,
  review_id: text,
  analysis_version: text,
  experiment_type: text,
  experimental_system: system,
  reference_system: system,
  time_window: window,
  decision_state: decisionState,
});
export const experimentsSchema = z.strictObject({
  experiments: z.array(experimentSchema),
});
export type ReviewV1 = z.infer<typeof reviewV1Schema>;
export type Experiment = z.infer<typeof experimentSchema>;
export type ExperimentListItem = Omit<Experiment, "decision_state"> & {
  decision_state: DecisionState | null;
};
export type Sample = z.infer<typeof sampleSchema>;
export type DecisionState = z.infer<typeof decisionState>;
