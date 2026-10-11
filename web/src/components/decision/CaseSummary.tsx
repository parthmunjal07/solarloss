import type { Review } from "../../lib/types";
import { dateLabel, numeric, timeLabel } from "../../lib/formatters";

export function CaseMetrics({ review }: { review: Review }) {
  const coverage = review.v2?.metrics.find(
    (m) => m.id === "signed_generation_deviation",
  )?.coverage;
  return (
    <div className="case-metrics">
      {(
        [
          ["Measured energy", review.metrics.measured, false],
          ["Model-expected energy", review.metrics.expected, false],
          ["Signed modelled deviation", review.metrics.deviation, true],
        ] as const
      ).map(([label, metric, signed]) => (
        <div className="case-metric" key={label}>
          <p className="eyebrow">{review.v2 ? label : metric.label}</p>
          <p className="case-value num">
            {metric.value === null ||
            (signed && review.decision?.state === "insufficient_evidence") ? (
              "Unavailable"
            ) : (
              <>
                {signed && metric.value >= 0 ? "+" : ""}
                {numeric(metric.value, 3)} <span>{metric.unit}</span>
              </>
            )}
          </p>
        </div>
      ))}
      <div className="case-metric">
        <p className="eyebrow">Supported coverage</p>
        <p className="case-value coverage-value num">
          {coverage?.valid_seconds != null &&
          coverage.observed_labelled_seconds != null ? (
            <>
              {numeric(coverage.valid_seconds, 0)}{" "}
              <span>/ {numeric(coverage.observed_labelled_seconds, 0)} s</span>
            </>
          ) : (
            numeric(review.metrics.coverage.value, 0)
          )}
        </p>
        <p className="small">
          {coverage
            ? "Observed labelled seconds"
            : review.metrics.coverage.unit}
        </p>
      </div>
    </div>
  );
}
export function CaseWindow({ review }: { review: Review }) {
  return (
    <p className="small num">
      {dateLabel(review.start)} · {timeLabel(review.start)}–
      {timeLabel(review.end)} UTC · {review.id}
    </p>
  );
}
export function CaseObservation({ review }: { review: Review }) {
  const m = review.metrics.deviation;
  return (
    <p className="case-observation">
      {review.v2 ? (
        <>
          Recorded target generation{" "}
          {m.value === null
            ? "is compared with"
            : m.value >= 0
              ? "fell below"
              : "exceeded"}{" "}
          its calibrated healthy expectation
          {review.event
            ? " during a documented shading intervention"
            : " over this recorded interval"}
          .
          {m.value !== null && (
            <>
              {" "}
              The signed modelled deviation is {m.value >= 0 ? "+" : ""}
              {numeric(m.value, 6)} {m.unit} over supported source intervals.
            </>
          )}{" "}
          The comparison does not establish a physical cause or recoverable
          energy.
        </>
      ) : (
        (review.observations[0] ??
        "Inspect the recorded comparison and its source limitations.")
      )}
    </p>
  );
}
