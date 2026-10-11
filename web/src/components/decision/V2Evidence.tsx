import type { ReviewV2 } from "../../lib/v2-types";
import { numeric, safeExternalUrl } from "../../lib/formatters";
import { Disclosure, SourceList } from "../ui/Common";

export function ResearchStatus({ review }: { review: ReviewV2 }) {
  return (
    <section
      className="method-callout"
      aria-label="Research verdict and event status"
    >
      <span className="eyebrow">Separate research verdict</span>
      <h3>{review.decision.verdict}</h3>
      <SourceList items={review.decision.reasons} />
      <p>
        <strong>Event-level review: Unavailable.</strong>{" "}
        {review.decision.event_review.reason}
      </p>
      <p className="small">
        Artifact approval covers bounded research evidence. It does not certify
        a fault cause, maintenance action or detector deployment readiness.
      </p>
    </section>
  );
}
export function V2Evidence({ review }: { review: ReviewV2 }) {
  return (
    <>
      <Disclosure title="Metric definitions, coverage and uncertainty">
        {review.metrics.map((m) => (
          <article className="v2-metric" key={m.id}>
            <h3>{m.id.replaceAll("_", " ")}</h3>
            <p className="num">
              {m.availability === "estimated"
                ? `${numeric(m.value, 6)} ${m.unit}`
                : `${m.availability === "not_applicable" ? "Not applicable" : "Not available"}. ${m.reason}`}
            </p>
            <p>{m.definition}</p>
            <p className="small">Population: {m.population}</p>
            <p className="small">Calculation: {m.calculation}</p>
            <p className="small">
              Coverage: {m.coverage.valid_seconds ?? "Not available"} valid
              seconds; {m.coverage.observed_labelled_seconds ?? "Not available"}{" "}
              observed labelled seconds;{" "}
              {m.coverage.wall_span_seconds ?? "Not available"} wall-span
              seconds.
            </p>
            {m.ratio && (
              <p className="small">
                Ratio: {m.ratio.numerator} {m.ratio.numerator_unit} /{" "}
                {m.ratio.denominator} {m.ratio.denominator_unit}.
              </p>
            )}
            {m.uncertainty ? (
              <>
                <p>
                  {m.uncertainty.kind.replaceAll("_", " ")}:{" "}
                  {m.uncertainty.lower === null || m.uncertainty.upper === null
                    ? "Not estimated"
                    : `${numeric(m.uncertainty.lower, 6)} to ${numeric(m.uncertainty.upper, 6)} ${m.uncertainty.unit}`}
                  . {m.uncertainty.group_count} groups. {m.uncertainty.method}
                </p>
                <p className="small">
                  Empirical model-error context is not a causal-loss confidence
                  interval.
                </p>
                <SourceList items={m.uncertainty.limitations} />
              </>
            ) : (
              <p className="small">
                Uncertainty: Not supplied for this metric.
              </p>
            )}
          </article>
        ))}
      </Disclosure>
      <Disclosure title="Model and provenance">
        <p>
          {review.provenance.model.name}:{" "}
          {review.provenance.model.expected_power_semantics}
        </p>
        <p>
          Target: {review.provenance.model.target}. Predictors:{" "}
          {review.provenance.model.predictors.join(", ")}.{" "}
          {review.provenance.model.training_rows} training rows.
        </p>
        <p>{review.provenance.model.preprocessing}</p>
        <dl className="metadata">
          <div>
            <dt>Model intercept / coefficients</dt>
            <dd>
              {review.provenance.model.intercept_w} W;{" "}
              {Object.entries(review.provenance.model.coefficients)
                .map(([k, v]) => `${k}: ${v}`)
                .join("; ")}
            </dd>
          </div>
          {Object.entries(review.provenance.splits).map(([k, v]) => (
            <div key={k}>
              <dt>{k}</dt>
              <dd>{Array.isArray(v) ? v.join(" to ") : v}</dd>
            </div>
          ))}
          <div>
            <dt>Detector calibration</dt>
            <dd>
              {review.provenance.thresholds.primary_window_minutes} minute
              primary windows;{" "}
              {review.provenance.thresholds.persistence_windows} consecutive
              windows; {review.provenance.thresholds.statistic}. Thresholds:{" "}
              {Object.entries(review.provenance.thresholds.by_window_minutes)
                .map(([k, v]) => `${k} min: ${v}`)
                .join("; ")}
              . {review.provenance.thresholds.calibration_population}
            </dd>
          </div>
          <div>
            <dt>Evaluation population</dt>
            <dd>{review.provenance.evaluation_population}</dd>
          </div>
          <div>
            <dt>Grouping and labels</dt>
            <dd>
              {review.provenance.grouping.notes} {review.provenance.label_use}
            </dd>
          </div>
          <div>
            <dt>Series presentation</dt>
            <dd>
              {review.series.downsampling.method};{" "}
              {review.series.downsampling.retained_count} retained from{" "}
              {review.series.downsampling.source_count} source records. Energy
              comes from original supported intervals.
            </dd>
          </div>
          <div>
            <dt>Protocol SHA-256</dt>
            <dd className="mono">{review.provenance.protocol_sha256}</dd>
          </div>
          <div>
            <dt>Code provenance</dt>
            <dd className="mono">{review.provenance.code_version}</dd>
          </div>
          <div>
            <dt>Artifact approval</dt>
            <dd>
              {review.decision.owner_review?.approver} ·{" "}
              {review.decision.owner_review?.approved_at} ·{" "}
              {review.decision.owner_review?.decision_reference}.{" "}
              {review.decision.owner_review?.scope}
            </dd>
          </div>
        </dl>
      </Disclosure>
      <Disclosure title="Electrical evidence — window-level contextual summaries">
        <p>
          No per-measurement observation time is supplied. These summaries are
          operating context, not precisely timestamped fault triggers or
          diagnoses.
        </p>
        {review.electrical_evidence.length ? (
          review.electrical_evidence.map((e) => (
            <article className="v2-metric" key={e.signal}>
              <h3>
                {e.signal} · {e.strength}
              </h3>
              <p>
                {e.measurement === null
                  ? "Not available"
                  : `${numeric(e.measurement, 3)} ${e.unit}`}
                . {e.quality}
              </p>
              <p>Comparison population: {e.comparison_population}</p>
              <p>Supports: {e.supports}</p>
              <p>Does not prove: {e.does_not_prove}</p>
              <p>Alternatives: {e.alternatives.join("; ")}</p>
              <p>Missing measurements: {e.missing_measurements.join("; ")}</p>
            </article>
          ))
        ) : (
          <p>Not available. No electrical evidence entries were supplied.</p>
        )}
      </Disclosure>
    </>
  );
}
export function V2Checks({ review }: { review: ReviewV2 }) {
  return (
    <section>
      <p className="eyebrow">A bounded next step</p>
      <h2>Candidate technician checks</h2>
      <p>
        Proposed evidence-gathering prompts. No physical cause or maintenance
        recommendation is approved.
      </p>
      {review.candidate_checks.length ? (
        <div className="next-checks">
          {review.candidate_checks.map((c) => (
            <article key={c.id}>
              <div className="check-title">
                <h3>{c.id.replaceAll("_", " ")}</h3>
                <span className="badge proposal">
                  {c.status === "unavailable"
                    ? "Unavailable"
                    : "Proposed · Unapproved"}
                </span>
              </div>
              <p>{c.observed_fact}</p>
              <Disclosure
                title="Hypothesis, evidence and next information"
                open
              >
                <dl className="metadata">
                  <div>
                    <dt>Candidate hypothesis</dt>
                    <dd>{c.hypothesis}</dd>
                  </div>
                  <div>
                    <dt>Supporting evidence</dt>
                    <dd>{c.supporting_evidence.join("; ")}</dd>
                  </div>
                  <div>
                    <dt>Opposing evidence</dt>
                    <dd>{c.opposing_evidence.join("; ")}</dd>
                  </div>
                  <div>
                    <dt>Next information</dt>
                    <dd>{c.next_information.join("; ")}</dd>
                  </div>
                  <div>
                    <dt>Qualification</dt>
                    <dd>{c.qualification}</dd>
                  </div>
                  <div>
                    <dt>Safety constraint</dt>
                    <dd>{c.safety_constraint}</dd>
                  </div>
                  <div>
                    <dt>Sources</dt>
                    <dd>
                      {c.sources.map((s) => {
                        const url = safeExternalUrl(s);
                        return <p key={s}>{url ? <a href={url}>{s}</a> : s}</p>;
                      })}
                    </dd>
                  </div>
                </dl>
              </Disclosure>
            </article>
          ))}
        </div>
      ) : (
        <p>
          Not available. No candidate checks were supplied for this interval.
        </p>
      )}
    </section>
  );
}
