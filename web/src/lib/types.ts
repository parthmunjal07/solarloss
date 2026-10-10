import type { DecisionState, Sample, ReviewV1 } from "./schemas";

export interface Metric {
  value: number | null;
  unit: string;
  reason: string;
  label: string;
}
export interface NextCheck {
  title: string;
  observed: string;
  candidate: string;
  support: string;
  alternatives: string;
  needed: string;
  qualification: string;
  source: string;
  status: "unapproved" | "methodology";
}
export interface Review {
  origin: "api-v1" | "research-preview";
  id: string;
  title: string;
  type: string;
  start: string;
  end: string;
  analysisVersion: string;
  producedAt: string;
  dataset: {
    name: string;
    source: string;
    version: string;
    extractionDate?: string;
    checksums: { algorithm: string; digest: string; scope: string }[];
  };
  target: string;
  reference: string;
  powerUnit: string;
  samples: Sample[];
  metrics: {
    expected: Metric;
    measured: Metric;
    deviation: Metric;
    positive: Metric;
    coverage: Metric;
  };
  decision: { state: DecisionState; reasons: string[]; rules: string } | null;
  observations: string[];
  limitations: string[];
  nextChecks: NextCheck[];
  exclusions: { start: string; end: string; reason: string }[];
  event: { start: string; end: string; label: string } | null;
  alerts: string[];
  maxGapSeconds: number | null;
  original?: ReviewV1;
  residuals?: Record<string, number | null>;
  research?: {
    verdict: string;
    detected: number;
    episodes: number;
    falseAlarmRate: number;
    falseAlarmLimit: number;
    errorBand: number[];
    placeboBlocks: number;
    placeboDays: number;
    voltageDelta: number;
    protocol: string;
    model: string;
    boundaries: Record<string, string[] | string>;
    sourceFiles: string[];
  };
}
