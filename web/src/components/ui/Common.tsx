import { Link } from "react-router";
import { useMode } from "../../app/Mode";
import { numeric } from "../../lib/formatters";
import type { Metric, Review } from "../../lib/types";
import { ApiError } from "../../lib/api";

export function Loading({ label = "Loading review" }: { label?: string }) {
  return (
    <div className="container app-page" role="status" aria-label={label}>
      <span className="sr-only">{label}</span>
      <div className="skeleton skeleton-heading" />
      <div className="skeleton skeleton-line" />
      <div className="skeleton skeleton-panel" />
    </div>
  );
}
export function ErrorState({
  error,
  retry,
  id,
}: {
  error: Error;
  retry: () => void;
  id?: string;
}) {
  const { href } = useMode();
  return (
    <section className="container app-page">
      <p className="eyebrow system-error">
        {error instanceof ApiError && error.status
          ? `API response ${error.status}`
          : "Results unavailable"}
      </p>
      <h1>We could not load {id ? "this review" : "the experiments"}.</h1>
      <p>
        {error instanceof ApiError
          ? error.message
          : "The API could not be reached. Check your connection and API configuration."}
      </p>
      {id && <p className="small mono">Experiment: {id}</p>}
      <div className="actions">
        <button className="button primary" onClick={retry}>
          Try again
        </button>
        <Link to={href("/method")}>Read the method & limitations</Link>
      </div>
    </section>
  );
}
export function MetricFigure({
  metric,
  coverage = false,
  hidden = false,
}: {
  metric: Metric;
  coverage?: boolean;
  hidden?: boolean;
}) {
  const available = metric.value !== null && !hidden;
  return (
    <div className="metric">
      <div className="eyebrow">{metric.label}</div>
      <div className={`figure num ${available ? "" : "unavailable"}`}>
        {available
          ? numeric(
              coverage && ["1", "fraction"].includes(metric.unit)
                ? metric.value! * 100
                : metric.value,
              coverage ? 0 : 1,
            )
          : "Not available"}
        {available && (
          <span>
            {coverage
              ? ["1", "fraction"].includes(metric.unit)
                ? "percent"
                : metric.unit
              : metric.unit}
          </span>
        )}
      </div>
      <p className="small">
        {hidden
          ? "The artifact decision is insufficient evidence. No energy-deviation figure is presented."
          : metric.reason}
      </p>
    </div>
  );
}
export function Provenance({ review }: { review: Review }) {
  return (
    <aside className="provenance">
      <span className="eyebrow">Source record</span>
      <p>
        {review.dataset.name} · {review.dataset.version}
      </p>
      <p className="small">
        Analysis {review.analysisVersion} · Produced {review.producedAt}
        {review.dataset.extractionDate &&
          ` · Extracted ${review.dataset.extractionDate}`}
      </p>
      <a href={review.dataset.source}>View dataset source</a>
      <details>
        <summary>Checksums and source provenance</summary>
        {review.dataset.checksums.map((c) => (
          <p key={c.scope} className="small">
            {c.scope}
            <br />
            <span className="mono">
              {c.algorithm}: {c.digest}
            </span>
          </p>
        ))}
      </details>
    </aside>
  );
}
export function Disclosure({
  title,
  children,
  open = false,
}: {
  title: string;
  children: React.ReactNode;
  open?: boolean;
}) {
  return (
    <details className="disclosure" open={open}>
      <summary>{title}</summary>
      <div>{children}</div>
    </details>
  );
}

export function SourceList({ items }: { items: string[] }) {
  return (
    <>
      <ul>
        {items.slice(0, 5).map((item, i) => (
          <li key={`${i}-${item}`}>{item}</li>
        ))}
      </ul>
      {items.length > 5 && (
        <details className="disclosure">
          <summary>Show more</summary>
          <ul>
            {items.slice(5).map((item, i) => (
              <li key={`${i}-${item}`}>{item}</li>
            ))}
          </ul>
        </details>
      )}
    </>
  );
}
