import { Link } from "react-router";
import { ArrowRight } from "lucide-react";
import { useMode } from "../../app/Mode";
import { DecisionBanner } from "../../components/decision/DecisionBanner";

function SampleLines() {
  return (
    <div className="sample-chart">
      <span className="badge">SAMPLE · illustrative shape</span>
      <svg
        viewBox="0 0 640 140"
        role="img"
        aria-label="Illustrative solar output dips and recovers. This is not a measured research series."
      >
        <path className="sample-grid" d="M0 30H640 M0 75H640 M0 120H640" />
        <path
          className="sample-expected"
          d="M8 105L56 87L104 61L152 39L200 27L248 26L296 31L344 38L392 50L440 61L488 80L536 97L584 110L632 122"
        />
        <path
          className="sample-measured"
          d="M8 107L56 90L104 64L152 42L200 29L248 27L280 55L310 88L344 94L374 84L404 66L440 64L488 84L536 99L584 113L632 122"
        />
      </svg>
    </div>
  );
}
export default function Landing() {
  const { href } = useMode();
  return (
    <div className="landing container">
      <section className="hero two-column">
        <div>
          <p className="eyebrow">Evidence review for solar performance</p>
          <h1>
            Was it the weather,
            <br className="desktop-break" /> or the panels?
          </h1>
          <p className="lead">
            SolarLoss compares measured solar output with a calibrated healthy
            expectation, then helps you review what the evidence supports.
          </p>
          <p className="hero-detail">
            When the evidence is not good enough, the review says so.
          </p>
          <div className="actions">
            <Link className="button primary" to={href("/experiments")}>
              Review a real experiment <ArrowRight size={18} aria-hidden />
            </Link>
            <Link to={href("/#how-it-works")}>See how it works</Link>
          </div>
          <p className="small hero-footnote">
            Real measurements. Visible limitations. No automatic diagnosis.
          </p>
        </div>
        <div className="hero-evidence">
          <p className="eyebrow">A clear answer starts with honest evidence</p>
          <DecisionBanner
            sample
            decision={{
              state: "insufficient_evidence",
              reasons: [
                "The available measurements do not yet support a performance conclusion.",
              ],
              rules: "illustrative example",
            }}
          />
          <div className="hero-card-bottom">
            <span>Measured output</span>
            <span>Healthy expectation</span>
            <span>Evidence checks</span>
          </div>
        </div>
      </section>
      <section className="landing-section problem">
        <div className="section-intro">
          <p className="eyebrow">The question behind the curve</p>
          <h2>A dip in the chart does not tell you why.</h2>
          <p>
            Less sunlight and a real performance change can look similar. A
            measured drop needs a fair comparison before it becomes a finding.
          </p>
        </div>
        <SampleLines />
        <div className="two-column causes">
          <div>
            <span className="eyebrow">01 · Environment</span>
            <h3>Less sunlight</h3>
            <p>
              Clouds and changing conditions can reduce generation across both
              inverter lines.
            </p>
          </div>
          <div>
            <span className="eyebrow">02 · Performance</span>
            <h3>A real performance change</h3>
            <p>
              The experimental line may depart from its calibrated healthy
              expectation. Evidence helps assess that departure.
            </p>
          </div>
        </div>
      </section>
      <section id="how-it-works" className="landing-section">
        <p className="eyebrow">From measurements to a review</p>
        <h2>Compare. Check. Decide.</h2>
        <div className="three-column steps">
          <div>
            <span className="step-number">01</span>
            <h3>Compare</h3>
            <p>
              Read measured output alongside model-expected output, calibrated
              on healthy periods.
            </p>
          </div>
          <div>
            <span className="step-number">02</span>
            <h3>Check</h3>
            <p>
              Review coverage, exclusions and model limitations. See which
              evidence is missing.
            </p>
          </div>
          <div>
            <span className="step-number">03</span>
            <h3>Decide</h3>
            <p>
              Read the artifact's decision and its reasons, then export the
              scientific review when available.
            </p>
          </div>
        </div>
      </section>
      <section className="landing-section">
        <p className="eyebrow">Three possible review outcomes</p>
        <h2>Clarity includes knowing when to stop.</h2>
        <div className="three-column outcome-cards">
          <article className="outcome supported_change">
            <h3>Supported change</h3>
            <p>
              The review's evidence rules support a performance change. Read the
              reasons and limitations before further investigation.
            </p>
          </article>
          <article className="outcome inconclusive">
            <h3>Inconclusive</h3>
            <p>
              The evidence does not settle the comparison. Review the
              uncertainty and what could resolve it.
            </p>
          </article>
          <article className="outcome insufficient_evidence">
            <h3>Insufficient evidence</h3>
            <p>
              Required evidence is missing or unsuitable. Obtain the missing
              information before reassessing.
            </p>
          </article>
        </div>
        <p className="quiet-line">
          Insufficient evidence is a result, not an error.
        </p>
      </section>
      <section className="landing-section">
        <p className="eyebrow">One result, two reading modes</p>
        <h2>The answer first. The detail when you need it.</h2>
        <div className="two-column reading-cards">
          <article className="card">
            <div
              className="reading-preview"
              aria-label="Sample summary interface"
            >
              <span className="badge">SAMPLE</span>
              <span className="preview-label">Review decision</span>
              <strong>Insufficient evidence</strong>
              <span>What we saw · What remains uncertain</span>
            </div>
            <h3>Summary</h3>
            <p>
              A clear decision, a short explanation and the evidence that
              matters most.
            </p>
          </article>
          <article className="card">
            <div
              className="reading-preview analyst-preview"
              aria-label="Sample analyst interface"
            >
              <span className="badge">SAMPLE</span>
              <span>
                Measured <span className="mini-line measured-line" /> Expected{" "}
                <span className="mini-line expected-line" />
              </span>
              <svg viewBox="0 0 320 50" aria-hidden>
                <path
                  className="sample-expected"
                  d="M0 42L40 25L80 12L120 6L160 8L200 16L240 26L280 39L320 45"
                />
                <path
                  className="sample-measured"
                  d="M0 43L40 27L80 15L120 9L160 32L200 38L240 30L280 41L320 46"
                />
              </svg>
              <span>Coverage · Exclusions · Model provenance</span>
            </div>
            <h3>Analyst</h3>
            <p>
              The same result, with measurement inspection, model context and
              source provenance.
            </p>
          </article>
        </div>
      </section>
      <section className="landing-section two-column research-scope">
        <div>
          <p className="eyebrow">Grounded in a real installation</p>
          <h2>A documented experiment, not a fictional fleet.</h2>
          <p>
            The University of La Réunion research installation records two
            inverter lines and imposed shading. The analysis calibrates on
            healthy periods, evaluates held-out interventions and compares with
            matched healthy periods.
          </p>
          <a href="https://zenodo.org/records/7291380">
            Graillet et al. · Pinned Zenodo dataset v2
          </a>
        </div>
        <div className="scope-notes">
          <h3>What the research does not establish</h3>
          <p>Deployment readiness or universal fault detection.</p>
          <p>
            A validated physical diagnosis or measured maintenance recovery.
          </p>
          <p>A true unshaded counterfactual for the experimental line.</p>
          <Link to={href("/method")}>
            Read the full limitations <ArrowRight size={16} aria-hidden />
          </Link>
        </div>
        <div className="architecture small">
          <span>Offline Python · Scientific analysis</span>
          <span>S3 · Private artifact storage</span>
          <span>Lambda · Validates and presents</span>
          <span>API Gateway · Serves review routes</span>
        </div>
      </section>
      <section className="landing-section closing">
        <p className="eyebrow">Start with the evidence</p>
        <h2>See what the evidence supports.</h2>
        <Link className="button primary" to={href("/experiments")}>
          Review a real experiment <ArrowRight size={18} aria-hidden />
        </Link>
        <div className="closing-links">
          <Link to={href("/method")}>Method & limitations</Link>
          <a href="https://github.com/parthmunjal07/solarloss">GitHub</a>
          <span className="small">Demo video: Not available</span>
        </div>
      </section>
    </div>
  );
}
