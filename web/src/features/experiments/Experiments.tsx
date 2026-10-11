import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { ArrowRight } from "lucide-react";
import { useMode } from "../../app/Mode";
import { useReview } from "../../app/queries";
import { fetchExperiments, fetchResearch, shouldRetry } from "../../lib/api";
import { dateLabel, timeLabel } from "../../lib/formatters";
import { decisionLabels } from "../../lib/formatters";
import { ErrorState, Loading } from "../../components/ui/Common";
import type { ExperimentListItem } from "../../lib/schemas";

function ExperimentCard({ experiment }: { experiment: ExperimentListItem }) {
  const { mode, href, preview } = useMode(),
    details = useReview(experiment.experiment_id);
  const r = details.data;
  return (
    <article className="card experiment-card">
      <div className="card-top">
        <span className="eyebrow mono">{experiment.experiment_id}</span>
        <span className="small">
          {preview
            ? "Research preview"
            : experiment.research_verdict
              ? `Research ${experiment.research_verdict} · Event unavailable`
              : experiment.decision_state
                ? decisionLabels[experiment.decision_state]
                : "Not available"}
        </span>
      </div>
      <h2>{r?.title ?? experiment.experiment_type.replaceAll("_", " ")}</h2>
      <p>
        {preview
          ? "Documented experimental shading of one complete module."
          : "A stored scientific review of the experimental and reference inverter lines."}
      </p>
      <p className="small num">
        {dateLabel(experiment.time_window.start)} ·{" "}
        {timeLabel(experiment.time_window.start)} to{" "}
        {timeLabel(experiment.time_window.end)} UTC
      </p>
      <div className="source-line small">
        {r ? (
          <>
            <span>{r.dataset.name}</span>
            <a href={r.dataset.source}>Dataset source</a>
          </>
        ) : (
          <span>
            Dataset source:{" "}
            {details.isError
              ? "Not available. Review details could not be loaded."
              : "Loading source record…"}
          </span>
        )}
      </div>
      {mode === "analyst" && (
        <dl className="metadata">
          <div>
            <dt>Experimental</dt>
            <dd>
              {experiment.experimental_system.identifier}:{" "}
              {experiment.experimental_system.description}
            </dd>
          </div>
          <div>
            <dt>Reference</dt>
            <dd>
              {experiment.reference_system.identifier}:{" "}
              {experiment.reference_system.description}
            </dd>
          </div>
          <div>
            <dt>Experiment type</dt>
            <dd>{experiment.experiment_type}</dd>
          </div>
          <div>
            <dt>Data coverage</dt>
            <dd>
              {r
                ? r.metrics.coverage.reason
                : "Not available in the listing response"}
            </dd>
          </div>
        </dl>
      )}
      <Link
        className="button primary"
        to={href(`/experiments/${experiment.experiment_id}`)}
      >
        Review experiment <ArrowRight size={18} aria-hidden />
      </Link>
    </article>
  );
}
export default function Experiments() {
  const { mode, href, preview } = useMode(),
    [filter, setFilter] = useState("all");
  const query = useQuery<{ experiments: ExperimentListItem[] }>({
    queryKey: [preview ? "research-list" : "experiments"],
    queryFn: async ({ signal }) => {
      if (!preview) return fetchExperiments(signal);
      const r = await fetchResearch(signal);
      return {
        experiments: [
          {
            experiment_id: r.id,
            review_id: `review_${r.id}`,
            analysis_version: r.analysisVersion,
            experiment_type: r.type,
            experimental_system: {
              identifier: "Inverter 1",
              description: "Experimentally shaded line",
            },
            reference_system: {
              identifier: "Inverter 2",
              description: "Comparison line",
            },
            time_window: { start: r.start, end: r.end },
            decision_state: null,
          },
        ],
      };
    },
    retry: shouldRetry,
    staleTime: 60_000,
  });
  if (query.isPending) return <Loading label="Loading available experiments" />;
  if (query.isError)
    return (
      <>
        <ErrorState error={query.error} retry={() => void query.refetch()} />
        {import.meta.env.DEV && !preview && (
          <div className="container preview-entry">
            <p className="small">
              For local development, the committed V2 measurements are available
              separately.
            </p>
            <Link
              className="button secondary"
              to={`/experiments?mode=${mode}&preview=research`}
            >
              Open research preview
            </Link>
          </div>
        )}
      </>
    );
  const experiments = query.data.experiments,
    types = [...new Set(experiments.map((e) => e.experiment_type))];
  const visible = experiments.filter(
    (e) => filter === "all" || e.experiment_type === filter,
  );
  return (
    <div className="container app-page">
      <div className="page-heading">
        <p className="eyebrow">01 · Select an experiment</p>
        <h1>Start with a real observation.</h1>
        <p>
          Choose a recorded experiment, compare its production and follow the
          evidence through to the review.
        </p>
      </div>
      {mode === "analyst" && types.length > 0 && (
        <div className="filter">
          <label htmlFor="experiment-type">Experiment type</label>
          <select
            id="experiment-type"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="all">All types</option>
            {types.map((t) => (
              <option key={t} value={t}>
                {t.replaceAll("_", " ")}
              </option>
            ))}
          </select>
        </div>
      )}
      {visible.length ? (
        <div className="experiment-grid">
          {visible.map((e) => (
            <ExperimentCard key={e.experiment_id} experiment={e} />
          ))}
        </div>
      ) : (
        <section className="empty-state">
          <h2>
            {experiments.length
              ? "No experiments match this filter."
              : "No reviews are available yet."}
          </h2>
          <p>
            {experiments.length
              ? "Choose another experiment type."
              : "The API returned no stored reviews. An approved scientific artifact must be supplied before an experiment appears here."}
          </p>
          <Link to={href("/method")}>Read the method & limitations</Link>
        </section>
      )}
      <aside className="about-data">
        <p className="eyebrow">About the research dataset</p>
        <h2>University of La Réunion</h2>
        <p>
          Graillet et al. · Two recorded inverter lines and documented shading
          interventions.
        </p>
        <a href="https://zenodo.org/records/7291380">
          Pinned Zenodo record 7291380 · v2
        </a>
        {mode === "analyst" && (
          <p className="small">
            Source electrical timestamps carry UTC+4; API review timestamps are
            shown in UTC. Exact coverage, checksums and extraction dates appear
            with each source review when supplied.
          </p>
        )}
      </aside>
      {import.meta.env.DEV && !preview && (
        <div className="preview-entry">
          <p className="small">
            Development only · Committed scientific measurements, approval
            pending.
          </p>
          <Link to={`/experiments?mode=${mode}&preview=research`}>
            Open research preview
          </Link>
        </div>
      )}
    </div>
  );
}
