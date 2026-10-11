import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { ArrowRight } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchReview } from "../../lib/api";
import { useMode } from "../../app/Mode";
import { downsample, plotPoints } from "../../lib/chart-data";
import { numeric, dateLabel, timeLabel } from "../../lib/formatters";
import ArraySchematic from "../solar-array/ArraySchematic";
const SolarArray = lazy(() => import("../solar-array/SolarArray"));

function CasePreview() {
  // The production adapter validates this real response. Never fall back to research data.
  const query = useQuery({
    queryKey: ["review", "shading_01"],
    queryFn: ({ signal }) => fetchReview("shading_01", signal),
    retry: false,
    staleTime: 60_000,
  });
  const r = query.data;
  if (!r)
    return (
      <div className="case-preview preview-placeholder">
        <p className="eyebrow">
          {query.isPending
            ? "Loading the recorded case"
            : "A fair comparison starts here"}
        </p>
        <h2>Two measured lines. One calibrated expectation.</h2>
        <ArraySchematic
          mode="reference"
          selected={null}
          highlighted={null}
          onSelect={() => {}}
          onHover={() => {}}
        />
        <p className="small" role="status">
          {query.isPending
            ? "Retrieving validated case evidence…"
            : "Explanatory illustration · Case evidence is currently unavailable."}
        </p>
        {query.isError && (
          <button className="text-button" onClick={() => void query.refetch()}>
            Retry case preview
          </button>
        )}
      </div>
    );
  const data = downsample(plotPoints(r), [], 320);
  const max = Math.max(
    1,
    ...data.flatMap((p) => [p.measured ?? 0, p.expected ?? 0]),
  );
  const start = data[0]?.time ?? 0,
    span = (data.at(-1)?.time ?? 1) - start || 1;
  function path(key: "measured" | "expected") {
    let open = false;
    return data
      .map((p) => {
        const v = p[key];
        if (v === null) {
          open = false;
          return "";
        }
        const command = open ? "L" : "M";
        open = true;
        return `${command}${(24 + ((p.time - start) / span) * 432).toFixed(1)},${(176 - (v / max) * 136).toFixed(1)}`;
      })
      .join(" ");
  }
  return (
    <div className="case-preview">
      <div className="preview-top">
        <p className="eyebrow">From the recorded case</p>
        <span className="mono">{r.id}</span>
      </div>
      <h2>One module under documented shading.</h2>
      <p className="small">
        {dateLabel(r.start)} · La Réunion research installation
      </p>
      <svg
        className="preview-power"
        viewBox="0 0 480 212"
        role="img"
        aria-label="Source-backed recorded measured and model-expected target power. Missing model estimates remain gaps."
      >
        <path
          d="M24 40H456 M24 108H456 M24 176H456"
          stroke="var(--border)"
          fill="none"
        />
        <path
          d={path("expected")}
          stroke="var(--reference)"
          strokeWidth="2"
          strokeDasharray="5 4"
          fill="none"
        />
        <path
          d={path("measured")}
          stroke="var(--measured)"
          strokeWidth="2"
          fill="none"
        />
        <text x="24" y="201" fill="var(--text-muted)" fontSize="12">
          {timeLabel(r.start)} UTC
        </text>
        <text
          x="456"
          y="201"
          textAnchor="end"
          fill="var(--text-muted)"
          fontSize="12"
        >
          {timeLabel(r.end)} UTC
        </text>
      </svg>
      <div className="preview-legend small">
        <span>
          <i className="mini-line measured-line" />
          Measured
        </span>
        <span>
          <i className="mini-line expected-line" />
          Model-expected
        </span>
      </div>
      <div className="preview-result">
        <span className="small">Signed modelled deviation</span>
        <strong className="num">
          {r.metrics.deviation.value !== null && r.metrics.deviation.value >= 0
            ? "+"
            : ""}
          {numeric(r.metrics.deviation.value, 3)} <small>kWh</small>
        </strong>
      </div>
      <p className="small">
        Full supported event · Comparison evidence; cause and recoverable energy
        remain unconfirmed.
      </p>
    </div>
  );
}
function SetupExplanation() {
  const ref = useRef<HTMLDivElement>(null),
    [ready, setReady] = useState(false);
  useEffect(() => {
    if (!ref.current || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setReady(true);
          observer.disconnect();
        }
      },
      { rootMargin: "100px" },
    );
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);
  const fallback = (
    <div className="setup-placeholder">
      <ArraySchematic
        mode="reference"
        selected={null}
        highlighted={null}
        onSelect={() => {}}
        onHover={() => {}}
      />
      <p className="small">
        Illustrative two-inverter setup. Interactive controls load as this
        section comes into view.
      </p>
    </div>
  );
  return (
    <div ref={ref}>
      {ready ? (
        <Suspense fallback={fallback}>
          <SolarArray />
        </Suspense>
      ) : (
        fallback
      )}
    </div>
  );
}
export default function Landing() {
  const { href } = useMode();
  // The commercial entry always opens the approved API case, even from a development preview URL.
  const caseHref = "/experiments/shading_01?mode=summary";
  return (
    <div className="landing container">
      <section className="hero two-column">
        <div>
          <p className="eyebrow">For solar operations & maintenance teams</p>
          <h1>When solar output drops, see what to investigate next.</h1>
          <p className="lead">
            SolarLoss compares recorded generation with a calibrated healthy
            expectation, brings the evidence together, and helps maintenance
            teams prepare their next investigation.
          </p>
          <div className="actions">
            <Link className="button primary" to={caseHref}>
              Explore a real solar case <ArrowRight size={18} aria-hidden />
            </Link>
            <a href="#how-it-works">How SolarLoss works</a>
          </div>
          <p className="small hero-footnote">
            Recorded generation → evidence → proposed next checks
          </p>
        </div>
        <CasePreview />
      </section>
      <section id="how-it-works" className="landing-section workflow-section">
        <div className="section-intro">
          <p className="eyebrow">
            A clearer route from a drop to an investigation
          </p>
          <h2>
            A power curve gives you a question.
            <br />
            Bring the evidence to your next check.
          </h2>
        </div>
        <div className="three-column steps">
          <div>
            <span className="step-number">01</span>
            <h3>Compare generation</h3>
            <p>
              Explore recorded output against a healthy expectation calibrated
              on earlier measurements.
            </p>
          </div>
          <div>
            <span className="step-number">02</span>
            <h3>Understand evidence</h3>
            <p>
              Inspect the timing, supported coverage and electrical context. See
              what the comparison leaves unresolved.
            </p>
          </div>
          <div>
            <span className="step-number">03</span>
            <h3>Plan next checks</h3>
            <p>
              Review proposed information-gathering checks and take a readable
              evidence report into the investigation.
            </p>
          </div>
        </div>
      </section>
      <section className="landing-section setup-story">
        <p className="eyebrow">Understand the comparison</p>
        <h2>Why use a second inverter line?</h2>
        <p>
          A reference line helps put changing production in context. SolarLoss
          uses its recorded output and weather measurements to estimate the
          target line’s healthy expectation.
        </p>
        <SetupExplanation />
      </section>
      <section className="landing-section trust-strip">
        <div>
          <p className="eyebrow">
            Documented intervention. Recorded measurements.
          </p>
          <h2>A real case you can inspect.</h2>
          <p>
            The current case uses Graillet et al.’s University of La Réunion
            dataset, with documented experimental shading and two measured
            inverter lines.
          </p>
        </div>
        <Link to={href("/method")}>
          Method, sources & limitations <ArrowRight size={18} aria-hidden />
        </Link>
      </section>
      <section className="landing-section closing">
        <div>
          <p className="eyebrow">Start with one recorded case</p>
          <h2>
            See the observation.
            <br />
            Prepare the next investigation.
          </h2>
        </div>
        <Link className="button primary" to={caseHref}>
          Explore a real solar case <ArrowRight size={18} aria-hidden />
        </Link>
      </section>
    </div>
  );
}
