import { Link, useParams } from "react-router";
import { Download } from "lucide-react";
import { useMode } from "../../app/Mode";
import { useReview } from "../../app/queries";
import { reportUrl } from "../../lib/api";
import { numeric } from "../../lib/formatters";
import { DecisionBanner } from "../../components/decision/DecisionBanner";
import {
  Disclosure,
  ErrorState,
  Loading,
  Provenance,
  SourceList,
} from "../../components/ui/Common";
import type { NextCheck, Review } from "../../lib/types";
import {
  ResearchStatus,
  V2Evidence,
  V2Checks,
} from "../../components/decision/V2Evidence";

function NextChecks({ review, analyst }: { review: Review; analyst: boolean }) {
  const missing = review.decision?.state === "insufficient_evidence";
  const checks: NextCheck[] = review.nextChecks.slice(0, analyst ? 5 : 2);
  return (
    <section>
      <p className="eyebrow">A bounded next step</p>
      <h2>{missing ? "What evidence is missing" : "Technician next checks"}</h2>
      {missing ? (
        <>
          <p>
            Start with the artifact's reasons and unmet checks before reaching a
            production conclusion.
          </p>
          <ul>
            {review.decision?.reasons.slice(0, 5).map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </>
      ) : checks.length ? (
        <div className="next-checks">
          {checks.map((c) => (
            <article key={c.title}>
              <div className="check-title">
                <h3>{c.title}</h3>
                <span className="badge proposal">
                  {c.status === "unapproved"
                    ? "Proposed · Unapproved"
                    : "Static methodology guidance"}
                </span>
              </div>
              <p>{c.needed}</p>
              {analyst && (
                <Disclosure title="Observation, alternatives and source">
                  <dl className="metadata">
                    <div>
                      <dt>Observed</dt>
                      <dd>{c.observed}</dd>
                    </div>
                    <div>
                      <dt>Candidate explanation</dt>
                      <dd>{c.candidate}</dd>
                    </div>
                    <div>
                      <dt>Supporting evidence</dt>
                      <dd>{c.support}</dd>
                    </div>
                    <div>
                      <dt>Alternatives</dt>
                      <dd>{c.alternatives}</dd>
                    </div>
                    <div>
                      <dt>Additional information</dt>
                      <dd>{c.needed}</dd>
                    </div>
                    <div>
                      <dt>Qualification</dt>
                      <dd>{c.qualification}</dd>
                    </div>
                    <div>
                      <dt>Source / status</dt>
                      <dd>{c.source}. Not approved diagnostic guidance.</dd>
                    </div>
                  </dl>
                </Disclosure>
              )}
            </article>
          ))}
        </div>
      ) : (
        <p>
          Not available. The v0.1 artifact has no approved technician-check
          fields. Consult the methodology and obtain the missing observational
          context.
        </p>
      )}
      <p className="small">
        General guidance, not a diagnosis. Electrical inspection should be done
        by qualified personnel.
      </p>
    </section>
  );
}
function ModelEvidence({ review }: { review: Review }) {
  const r = review.original,
    research = review.research;
  return (
    <>
      <Disclosure title="Why the decision" open>
        {review.decision ? (
          <>
            <SourceList items={review.decision.reasons} />
            {r?.quality_checks.slice(0, 5).map((c) => (
              <div className="check-row" key={c.name}>
                <div>
                  <h3>{c.name}</h3>
                  <span
                    className={`check-status ${c.status === "passed" ? "supported_change" : "insufficient_evidence"}`}
                  >
                    {c.status === "passed"
                      ? "Met"
                      : c.status === "failed"
                        ? "Not met"
                        : c.status === "not_evaluated"
                          ? "Not evaluated"
                          : "Reported"}
                  </span>
                </div>
                <p>{c.detail}</p>
                {c.result && <p className="small">{c.result}</p>}
              </div>
            ))}
            {r && r.quality_checks.length > 5 && (
              <Disclosure title="Show more checks">
                <SourceList
                  items={r.quality_checks
                    .slice(5)
                    .map(
                      (c) =>
                        `${c.name}: ${c.status === "passed" ? "Met" : c.status === "failed" ? "Not met" : c.status.replaceAll("_", " ")}. ${c.detail}`,
                    )}
                />
              </Disclosure>
            )}
          </>
        ) : (
          <p>
            No approved artifact decision or artifact-quality check list is
            supplied by the research projection. The research findings below
            retain their original validation meaning.
          </p>
        )}
      </Disclosure>
      <Disclosure title="Model evidence and baseline comparison">
        {r ? (
          <>
            <p>
              Healthy calibration:{" "}
              {numeric(r.metrics.calibration_error.value, 2)}{" "}
              {r.metrics.calibration_error.unit},{" "}
              {r.metrics.calibration_error.statistic}, evaluated on{" "}
              {r.metrics.calibration_error.evaluation_population}.
            </p>
            <p className="small">
              Denominator: {r.metrics.calibration_error.denominator.value}{" "}
              {r.metrics.calibration_error.denominator.unit}. Model error is not
              detector accuracy.
            </p>
            <div className="two-column baseline">
              <div>
                <span className="eyebrow">
                  {r.baseline_comparison.simple_baseline.name}
                </span>
                <p className="num">
                  {numeric(r.baseline_comparison.simple_baseline.value, 2)}{" "}
                  {r.baseline_comparison.unit}
                </p>
              </div>
              <div>
                <span className="eyebrow">
                  {r.baseline_comparison.calibrated_reference.name}
                </span>
                <p className="num">
                  {numeric(r.baseline_comparison.calibrated_reference.value, 2)}{" "}
                  {r.baseline_comparison.unit}
                </p>
              </div>
            </div>
            <p>
              {r.baseline_comparison.metric} ·{" "}
              {r.baseline_comparison.evaluation_population}
            </p>
          </>
        ) : (
          research && (
            <>
              <p>
                {research.detected}/{research.episodes} documented interventions
                were detected retrospectively on one installation.
              </p>
              <p>
                The selected detector produced{" "}
                {numeric(research.falseAlarmRate, 5)} alert runs per evaluated
                healthy hour, exceeding the frozen{" "}
                {numeric(research.falseAlarmLimit, 2)} per-hour limit. Research
                verdict: {research.verdict}.
              </p>
              <p>
                All simple baselines also detected 23/23 events. Better healthy
                regression error does not establish a better detector. The
                frozen selection was not changed after seeing these protected
                results.
              </p>
              <p className="small mono">
                Protocol SHA-256: {research.protocol}
              </p>
            </>
          )
        )}
      </Disclosure>
      <Disclosure title="Uncertainty and empirical error">
        {r ? (
          <>
            <p>Method: {r.uncertainty.method}</p>
            <p>
              {r.uncertainty.independent_blocks.count}{" "}
              {r.uncertainty.independent_blocks.unit} reported as independent
              blocks.
            </p>
            {r.uncertainty.exploratory && (
              <span className="badge proposal">Exploratory estimate</span>
            )}
            <p>
              {r.uncertainty.interval
                ? `Source interval: ${numeric(r.uncertainty.interval.lower, 2)} to ${numeric(r.uncertainty.interval.upper, 2)} ${r.uncertainty.interval.unit}; level ${numeric(r.uncertainty.interval.level * 100, 1)} percent.`
                : `Not available. ${r.uncertainty.not_estimated_reason ?? "The source does not supply an uncertainty interval."}`}
            </p>
            <SourceList items={r.uncertainty.limitations} />
          </>
        ) : (
          research && (
            <>
              <p>
                Matched empirical model-error band:{" "}
                {numeric(research.errorBand[0], 3)} to{" "}
                {numeric(research.errorBand[1], 3)} kWh, using{" "}
                {research.placeboBlocks} matched blocks across{" "}
                {research.placeboDays} days.
              </p>
              <p>
                This is not a counterfactual-loss confidence interval. Adjacent
                days may remain dependent, and the comparison does not observe
                the true unshaded target output.
              </p>
            </>
          )
        )}
      </Disclosure>
      <Disclosure title="Placebo and robustness">
        {r ? (
          <>
            <h3>Placebo</h3>
            <p>{r.placebo.status.replaceAll("_", " ")}</p>
            {r.placebo.findings.map((f) => (
              <p key={f.name}>
                {f.name}: {f.detail}
              </p>
            ))}
            <h3>Robustness</h3>
            <p>{r.robustness.status.replaceAll("_", " ")}</p>
            {r.robustness.findings.map((f) => (
              <div key={f.name}>
                {f.synthetic && (
                  <span className="badge">
                    Synthetic test, data removed on purpose
                  </span>
                )}
                <p>
                  {f.name}: {f.detail}
                </p>
              </div>
            ))}
          </>
        ) : (
          <>
            <p>
              Only 10 of the 23 events have adequate matched healthy placebo
              support. Predeclared windows and baselines provide sensitivity
              context, not a post-test model selection.
            </p>
            <p>
              Event-specific synthetic robustness findings: Not available in
              this research projection.
            </p>
          </>
        )}
      </Disclosure>
      <Disclosure title="Exclusions and missing evidence">
        {review.exclusions.length ? (
          <SourceList
            items={review.exclusions.map(
              (e) => `${e.start} to ${e.end}: ${e.reason}`,
            )}
          />
        ) : (
          <p>
            {review.origin === "research-preview"
              ? "An event-specific exclusion list is not supplied. Inspect the chart gaps and original eligibility flags. No generation deviation is assigned to unsupported time."
              : "The artifact reports no excluded intervals."}
          </p>
        )}
        <p>
          Inverter-state logs, independent irradiance and string-level or
          inspection evidence are not supplied here. Electrical operating
          measurements cannot resolve a unique physical cause.
        </p>
        {research && (
          <p>
            Observed matched PV-voltage departure:{" "}
            {numeric(research.voltageDelta, 2)} V. This is operating context,
            not a diagnosis.
          </p>
        )}
      </Disclosure>
      <Disclosure title="Source limitations">
        <SourceList items={review.limitations} />
      </Disclosure>
    </>
  );
}
export default function Report() {
  const { id = "" } = useParams(),
    { mode, href } = useMode(),
    query = useReview(id);
  if (query.isPending) return <Loading label="Loading evidence report" />;
  if (query.isError)
    return (
      <ErrorState
        error={query.error}
        retry={() => void query.refetch()}
        id={id}
      />
    );
  const r = query.data,
    analyst = mode === "analyst";
  return (
    <div className="container app-page report-page">
      <DecisionBanner
        decision={r.decision}
        apiV2={!!r.v2}
        unavailableReason={r.v2?.decision.event_review.reason}
      />
      <div className="report-context small">
        <span className="mono">{r.id}</span>
        <span>{r.title}</span>
        <span>
          {r.origin === "api-v1"
            ? "Stored API review · v0.1 provisional semantics"
            : r.origin === "api-v2"
              ? "Stored API review · v0.2 bounded research evidence"
              : "Research preview · No approved review decision"}
        </span>
      </div>
      <section className="plain-words">
        <p className="eyebrow">The finding, without the jargon</p>
        <h2>In plain words</h2>
        <dl>
          <div>
            <dt>What we looked at</dt>
            <dd>
              {r.origin === "research-preview"
                ? "A documented shading experiment, using measured output and a healthy-period calibrated expectation."
                : `${r.title}. Measured experimental output is compared with the artifact's calibrated expected series.`}
            </dd>
          </div>
          <div>
            <dt>What we observed</dt>
            <dd>
              {r.decision
                ? (r.decision.reasons[0] ??
                  "The artifact provides a decision but no reason text.")
                : r.observations[1]}
            </dd>
          </div>
          <div>
            <dt>What remains uncertain</dt>
            <dd>
              {r.limitations[0] ??
                "Additional scientific limitations are not supplied by the source."}{" "}
              A performance comparison does not prove a physical root cause.
            </dd>
          </div>
        </dl>
      </section>
      <section>
        <h2>What this does not tell you</h2>
        <ul className="limitation-list">
          <li>Which physical cause is responsible.</li>
          <li>How much energy could be recovered by maintenance.</li>
          <li>Whether this detector is ready for a different installation.</li>
        </ul>
        {r.research && (
          <div className="method-callout">
            <span className="eyebrow">
              Separate research validation verdict
            </span>
            <h3>LIMIT</h3>
            <p>
              The detector's healthy false-alarm rate exceeds its frozen
              acceptance limit. Retrospective detection of 23/23 interventions
              does not establish deployment readiness.
            </p>
          </div>
        )}
      </section>
      {r.v2 && (
        <>
          <ResearchStatus review={r.v2} />
          <V2Evidence review={r.v2} />
        </>
      )}
      {analyst && !r.v2 && (
        <section className="analyst-sections">
          <h2>Behind the review</h2>
          <ModelEvidence review={r} />
        </section>
      )}
      {r.v2 ? (
        <V2Checks review={r.v2} />
      ) : (
        <NextChecks review={r} analyst={analyst} />
      )}
      <section className="next-stage export-stage">
        <div>
          <p className="eyebrow">05 · Export the source review</p>
          <h2>Keep the evidence with the conclusion.</h2>
          <p>
            {r.origin !== "research-preview"
              ? "Download the backend-generated HTML report through its short-lived private S3 link."
              : "Report export is not available for an unapproved research preview."}
          </p>
        </div>
        <div className="export-actions">
          {r.origin !== "research-preview" ? (
            <a className="button primary" href={reportUrl(id)}>
              Export report <Download size={18} aria-hidden />
            </a>
          ) : (
            <button className="button primary" disabled>
              Export unavailable
            </button>
          )}
          <Link to={href(`/experiments/${id}`)}>Back to the chart</Link>
        </div>
      </section>
      <Provenance review={r} />
    </div>
  );
}
