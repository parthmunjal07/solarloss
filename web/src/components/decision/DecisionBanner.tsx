import type { DecisionState } from "../../lib/schemas";
import { decisionLabels } from "../../lib/formatters";
export function DecisionBanner({
  decision,
  sample = false,
}: {
  decision: { state: DecisionState; reasons: string[]; rules: string } | null;
  sample?: boolean;
}) {
  const Heading = sample ? "h2" : "h1";
  return (
    <section
      className={`decision-banner ${decision?.state ?? "insufficient_evidence"}`}
      aria-label={sample ? "Sample decision" : "Review decision"}
    >
      <div className="decision-top">
        <span className="eyebrow">Review decision</span>
        {sample && <span className="badge">SAMPLE</span>}
      </div>
      <Heading>
        {decision
          ? decisionLabels[decision.state]
          : "Review decision not available"}
      </Heading>
      <p>
        {decision?.reasons[0] ??
          "The committed research results have no approved three-state artifact decision. A research LIMIT verdict does not supply one."}
      </p>
      <p className="small">
        {decision
          ? `Rules version: ${decision.rules}`
          : "Research preview · Approval pending"}
      </p>
    </section>
  );
}
