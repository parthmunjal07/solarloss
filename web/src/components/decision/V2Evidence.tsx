import type { ReviewV2 } from "../../lib/v2-types";
import { numeric, safeExternalUrl } from "../../lib/formatters";
import { Disclosure, SourceList } from "../ui/Common";

export function ResearchStatus({ review }: { review: ReviewV2 }) {
  return (
    <section
      className="research-status"
      aria-label="Research verdict and event status"
    >
      <div>
        <p className="eyebrow">Research validation</p>
        <h3>{review.decision.verdict}</h3>
        <p className="small">
          The selected detector exceeded its frozen false-alarm limit in the
          retrospective evaluation.
        </p>
      </div>
      <div>
        <p className="eyebrow">Event-level decision</p>
        <h3>Unavailable</h3>
        <p className="small">
          The true unshaded output of this target line was not measured. The
          comparison cannot establish a unique physical cause.
        </p>
      </div>
      <Disclosure title="Original scientific status and reasons">
        <SourceList items={review.decision.reasons} />
        <p>
          <strong>Event-level review: Unavailable.</strong>{" "}
          {review.decision.event_review.reason}
        </p>
        <p className="small">
          Artifact approval covers bounded research evidence only.
        </p>
      </Disclosure>
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
export function V2Checks({
  review,
  technical = false,
}: {
  review: ReviewV2;
  technical?: boolean;
}) {
  const titles: Record<string, string> = {
    review_inverter_operating_records: "Review inverter operating records",
    verify_measurement_and_reference_context:
      "Verify measurements and reference context",
    request_shading_observation_context: "Request shading observation context",
  };
  return (
    <section id="suggested-investigation" className="investigation-plan">
      <p className="eyebrow">Prepare the next investigation</p>
      <h2>Suggested investigation plan</h2>
      <p>
        Proposed evidence-gathering prompts from this review. Each check is
        unapproved; it establishes no diagnosis and authorizes no repair.
      </p>
      {review.candidate_checks.length ? (
        <div className="next-checks">
          {review.candidate_checks.map((c, i) => (
            <article key={c.id}>
              <div className="check-title">
                <span className="check-number num">0{i + 1}</span>
                <h3>{titles[c.id] ?? c.id.replaceAll("_", " ")}</h3>
                <span className="badge proposal">
                  {c.status === "unavailable"
                    ? "Unavailable"
                    : "Proposed · Unapproved"}
                </span>
              </div>
              <dl className="check-summary">
                <div>
                  <dt>Observation</dt>
                  <dd>{c.observed_fact}</dd>
                </div>
                <div>
                  <dt>Information required</dt>
                  <dd>
                    <SourceList items={c.next_information} />
                  </dd>
                </div>
              </dl>
              <Disclosure
                title="Why inspect this, alternatives & professional constraints"
                open={technical}
              >
                <dl className="metadata">
                  <div>
                    <dt>Why inspect this</dt>
                    <dd>
                      {c.status === "unavailable"
                        ? "This proposed check is unavailable; its hypothesis is withheld."
                        : c.hypothesis}
                    </dd>
                  </div>
                  <div>
                    <dt>Supporting evidence</dt>
                    <dd>
                      <SourceList items={c.supporting_evidence} />
                    </dd>
                  </div>
                  <div>
                    <dt>Opposing evidence / alternatives</dt>
                    <dd>
                      <SourceList items={c.opposing_evidence} />
                    </dd>
                  </div>
                  <div>
                    <dt>Professional qualification</dt>
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
              <p className="small check-safety">{c.safety_constraint}</p>
            </article>
          ))}
        </div>
      ) : (
        <p>No proposed checks were supplied for this interval.</p>
      )}
    </section>
  );
}
