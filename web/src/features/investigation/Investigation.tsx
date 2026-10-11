import { Link, useParams } from "react-router";
import { lazy, Suspense } from "react";
import { ArrowRight } from "lucide-react";
import { useMode } from "../../app/Mode";
import { useReview } from "../../app/queries";
import {
  CaseMetrics,
  CaseObservation,
  CaseWindow,
} from "../../components/decision/CaseSummary";
import {
  Disclosure,
  ErrorState,
  Loading,
  MetricFigure,
  Provenance,
  SourceList,
} from "../../components/ui/Common";
import Measurements from "../../components/ui/Measurements";
import PowerChart from "../../components/charts/PowerChart";
import { ResearchStatus } from "../../components/decision/V2Evidence";
const SolarArray = lazy(() => import("../solar-array/SolarArray"));
export default function Investigation() {
  const { id = "" } = useParams(),
    { mode, href } = useMode(),
    query = useReview(id);
  if (query.isPending) return <Loading />;
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
    <div className="container app-page">
      <div className="page-heading case-heading">
        <p className="eyebrow">Recorded solar case · Investigation</p>
        <h1>
          {r.v2 && r.event
            ? "One shaded module. A measurable departure."
            : r.title}
        </h1>
        <CaseWindow review={r} />
        <CaseObservation review={r} />
        <p className="small">
          {r.title}. Target: {r.target}; comparison: {r.reference}.
        </p>
      </div>
      <CaseMetrics review={r} />
      <p className="small population-note">
        Energy totals cover supported intervals in the full recorded event,{" "}
        {r.start} to {r.end}. Selecting a chart range does not change these
        totals.
      </p>
      {r.id === "shading_01" && (
        <p className="small setup-entry">
          <a href="#experimental-setup">Explore the two-inverter setup ↓</a> ·
          Illustrative 3D explanation
        </p>
      )}
      <PowerChart review={r} analyst={analyst} />
      <div className="chart-followup">
        <p className="small">
          {r.metrics.coverage.reason}. Inspect the original retained
          measurements and unavailable model estimates below.
        </p>
        <Measurements review={r} />
      </div>
      {r.v2 && <ResearchStatus review={r.v2} />}
      {r.id === "shading_01" && (
        <Suspense
          fallback={
            <p className="small">Loading the experimental setup explanation…</p>
          }
        >
          <SolarArray review={r} />
        </Suspense>
      )}
      {analyst && (
        <div className="analyst-sections">
          <Disclosure title="Calculation method and calibration" open>
            <p>
              {r.v2
                ? `Frozen model: ${r.v2.provenance.model.name}. ${r.v2.provenance.model.expected_power_semantics}`
                : r.research
                  ? `Frozen model: ${r.research.model}. Predictions were produced offline on the original measured pairs.`
                  : "The artifact provides a precomputed calibrated expected series. It does not provide model coefficients or training-split metadata."}
            </p>
            <ol>
              <li>
                Align experimental and reference measurements at exact
                timestamps.
              </li>
              <li>Apply the source eligibility and gap screens.</li>
              <li>Fit and calibrate on earlier healthy periods only.</li>
              <li>
                Compare measured experimental power with model-expected power.
              </li>
              <li>
                Report source energy totals over supported original intervals.
              </li>
            </ol>
            {r.research && (
              <dl className="metadata">
                {Object.entries(r.research.boundaries).map(([name, values]) => (
                  <div key={name}>
                    <dt>{name}</dt>
                    <dd>
                      {Array.isArray(values) ? values.join(" to ") : values}
                    </dd>
                  </div>
                ))}
              </dl>
            )}
            <p className="small">
              Per-sample uncertainty bounds:{" "}
              {r.samples.some((s) => s.expected_lower_bound !== undefined)
                ? "Shown where supplied in the source."
                : "Not available. No uncertainty area has been fabricated."}
            </p>
          </Disclosure>
          <Disclosure title="Exclusions and energy definitions">
            <p>
              {r.exclusions.length
                ? `${r.exclusions.length} excluded intervals are reported in the artifact.`
                : r.origin === "research-preview"
                  ? "An event-specific excluded-interval list is not supplied in this projection. The source eligibility flags and elapsed measurement gaps are shown in the chart."
                  : "The artifact reports no excluded intervals."}
            </p>
            <SourceList
              items={r.exclusions.map(
                (e) => `${e.start} to ${e.end}: ${e.reason}`,
              )}
            />
            <MetricFigure metric={r.metrics.positive} />
            <p>
              Signed deviation can be negative. Positive-only deviation
              truncates negative contributions and cannot establish abnormality
              by itself.
            </p>
          </Disclosure>
        </div>
      )}
      <div className="next-stage">
        <div>
          <p className="eyebrow">Continue the investigation</p>
          <h2>Prepare the next checks.</h2>
          <p>
            Review the observation, uncertainty and proposed information to
            gather next.
          </p>
        </div>
        <Link className="button primary" to={href(`/experiments/${id}/report`)}>
          Check the evidence <ArrowRight size={18} aria-hidden />
        </Link>
      </div>
      <Provenance review={r} />
    </div>
  );
}
