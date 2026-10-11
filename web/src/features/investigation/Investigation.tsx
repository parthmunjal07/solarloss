import { Link, useParams } from "react-router";
import { lazy, Suspense } from "react";
import { ArrowRight } from "lucide-react";
import { useMode } from "../../app/Mode";
import { useReview } from "../../app/queries";
import { dateLabel, timeLabel, numeric } from "../../lib/formatters";
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
      <div className="breadcrumb">
        <Link to={href("/experiments")}>Experiments</Link>
        <span>/</span>
        <span className="mono">{r.id}</span>
      </div>
      <div className="page-heading">
        <p className="eyebrow">02 · Analyse performance</p>
        <h1>{r.title}</h1>
        <p>
          Compare the experimental line with its calibrated healthy expectation.
        </p>
        <p className="small num">
          {dateLabel(r.start)} · {timeLabel(r.start)} to {timeLabel(r.end)} UTC
          {r.origin === "research-preview" && " · Réunion local time is UTC+4"}
        </p>
      </div>
      <div className="metrics">
        <MetricFigure metric={r.metrics.expected} />
        <MetricFigure metric={r.metrics.measured} />
        <MetricFigure
          metric={r.metrics.deviation}
          hidden={r.decision?.state === "insufficient_evidence"}
        />
        {analyst && <MetricFigure metric={r.metrics.coverage} coverage />}
      </div>
      {r.id === "shading_01" && (
        <p className="small setup-entry">
          <a href="#experimental-setup">Explore the two-inverter setup ↓</a> ·
          Illustrative 3D explanation
        </p>
      )}
      <PowerChart review={r} analyst={analyst} />
      <div className="chart-followup">
        <p className="small">
          {r.metrics.coverage.label}:{" "}
          {numeric(
            r.metrics.coverage.value === null
              ? null
              : ["1", "fraction"].includes(r.metrics.coverage.unit)
                ? r.metrics.coverage.value * 100
                : r.metrics.coverage.value,
            0,
          )}{" "}
          {["1", "fraction"].includes(r.metrics.coverage.unit)
            ? "percent"
            : r.metrics.coverage.unit}
          . {r.metrics.coverage.reason}.{" "}
          {r.origin === "research-preview"
            ? "Totals refer to the labelled event, while the chart also includes its surrounding recorded context."
            : "Expected and observed energy totals are unavailable when the artifact does not supply them."}
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
          <h2>What does the evidence support?</h2>
          <p>Read the decision, its reasons and what remains uncertain.</p>
        </div>
        <Link className="button primary" to={href(`/experiments/${id}/report`)}>
          Check the evidence <ArrowRight size={18} aria-hidden />
        </Link>
      </div>
      <Provenance review={r} />
    </div>
  );
}
