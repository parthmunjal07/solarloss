import { lazy, Suspense } from "react";
const SolarArray = lazy(() => import("../solar-array/SolarArray"));
export default function Method() {
  return (
    <article className="container app-page method-page">
      <p className="eyebrow">Methodology & limitations</p>
      <h1>
        A fair comparison.
        <br />A bounded conclusion.
      </h1>
      <p className="lead">
        SolarLoss presents precomputed scientific evidence. Understanding how it
        was collected and tested is part of understanding the result.
      </p>
      <section>
        <h2>Data source</h2>
        <p>
          The analysis uses Graillet et al.'s electrical and meteorological
          measurements from a rooftop photovoltaic installation at the
          University of La Réunion. The pinned source is Zenodo record 7291380,
          version v2, licensed CC BY 4.0.
        </p>
        <p>
          Two inverter streams are paired at exact timestamps. Inverter 1
          carries documented experimental shading labels; inverter 2 supplies a
          comparison signal. The arrays differ, so raw reference output is not
          the expected output of the experimental array.
        </p>
        <a href="https://zenodo.org/records/7291380">
          Read the dataset citation
        </a>
      </section>
      <section>
        <h2>Healthy model calibration</h2>
        <p>
          A regression model learns the relationship between the target line and
          comparison inputs during earlier healthy periods. The selected V2
          model also uses measured environmental inputs. Healthy training,
          selection and threshold calibration use separate whole local days
          before the first intervention day.
        </p>
        <p>
          Applying this frozen model produces the calibrated expected
          experimental power. Measured power is what the experimental line
          actually recorded. A signed residual is expected minus measured power;
          it may be negative.
        </p>
        <p>
          Model calibration error describes prediction performance on a stated
          healthy population. It is not detector accuracy.
        </p>
      </section>
      <Suspense
        fallback={
          <p className="small">Loading the experimental setup explanation…</p>
        }
      >
        <SolarArray />
      </Suspense>
      <section>
        <h2>Evidence rules and false alarms</h2>
        <p>
          The V2 detector uses a threshold calibrated on healthy signed
          residuals and requires two consecutive eligible five-minute windows.
          Experimental shading labels are used for evaluation after prediction;
          a documented label is distinct from an automatic alert.
        </p>
        <div className="method-callout">
          <span className="eyebrow">Research validation verdict · LIMIT</span>
          <h3>23 of 23 interventions were detected retrospectively.</h3>
          <p>
            The selected detector also produced 0.08526 alert runs per evaluated
            healthy hour, above the frozen acceptance limit of 0.05 per hour.
            This is one installation, with no prospective test. It does not
            establish operational deployment readiness.
          </p>
        </div>
        <p>
          An artifact's Supported change, Inconclusive or Insufficient evidence
          decision is a separate review result. The research-level GO, LIMIT and
          REJECT verdicts cannot supply that decision.
        </p>
      </section>
      <section>
        <h2>Uncertainty and missingness</h2>
        <p>
          Generation deviation totals come from the scientific artifact. The V2
          analysis integrates original consecutive eligible measured intervals;
          it excludes unsupported gaps and never fills them by interpolation.
          The browser formats values and reduces chart points for display only.
        </p>
        <p>
          Signed modelled generation deviation and positive-only generation
          deviation describe different comparisons. Neither is confirmed
          recoverable energy. Positive-only truncation can produce a positive
          value in healthy conditions.
        </p>
        <p>
          Matched healthy periods provide an empirical model-error band. This is
          not a confidence interval for true counterfactual loss. Per-sample
          expected-power bounds appear only when the source supplies them.
          Missing metrics are shown as Not available, with their reason.
        </p>
      </section>
      <section>
        <h2>Placebo and robustness</h2>
        <p>
          The V2 results compare labelled events with matched healthy blocks
          under similar predictor conditions. Only 10 of the 23 events have
          adequate matched placebo support. Adjacent days may remain dependent.
        </p>
        <p>
          Predeclared alternative windows and baselines provide sensitivity
          context. They do not permit selecting a better detector after seeing
          protected outcomes. Synthetic robustness tests, where present in an
          artifact, describe deliberately modified test data and are labelled
          separately.
        </p>
      </section>
      <section>
        <h2>Electrical context and next checks</h2>
        <p>
          PV-side voltage and current describe an operating point. Voltage
          departures can be consistent with several explanations, including
          temperature, irradiance, mismatch and MPPT behaviour. These signals do
          not prove a unique physical root cause.
        </p>
        <p>
          Technician next checks in the committed E5 guidance are proposed and
          unapproved. Existing acquisition records, inverter state logs and
          independent irradiance observations may help an investigation. Further
          electrical inspection belongs with qualified PV personnel following
          site and equipment requirements.
        </p>
      </section>
      <section>
        <h2>Limitations</h2>
        <p>
          The study is retrospective, dataset-aware and limited to one
          installation. There is no observed unshaded counterfactual for
          inverter 1 and no per-row fault ground truth for inverter 2.
        </p>
        <p>
          No long-term panel-ageing analysis, validated cause classifier,
          maintenance recovery or commercial benefit has been established. The
          application does not connect to live rooftop systems.
        </p>
        <p>
          The architecture is offline Python scientific analysis, a validated
          artifact in private S3, Python Lambda and API Gateway, then this React
          evidence renderer. Lambda validates and presents the artifact; it does
          not run pvlib inference or Newey-West calculations. Production API
          serving requires a separately approved stored artifact. The frontend
          accepts v0.1 and artifact-approved v0.2 responses from the API; local
          research previews remain development-only.
        </p>
      </section>
      <aside className="provenance">
        <p className="eyebrow">Method sources</p>
        <p className="small">
          Committed analysis/EXPERIMENT_PROTOCOL_V2.md, EXPERIMENT_REPORT_V2.md,
          EXECUTIVE_SUMMARY_V2.md, DATA_PROVENANCE.md and
          INVESTIGATION_GUIDANCE_PROPOSAL.md. Backend boundary:
          docs/phase-3-scientific-v2-integration.md.
        </p>
        <a href="https://github.com/parthmunjal07/solarloss/tree/main/analysis">
          Read the scientific source documents
        </a>
      </aside>
    </article>
  );
}
