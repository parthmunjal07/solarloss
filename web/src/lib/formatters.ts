import type { DecisionState } from "./schemas";
export const decisionLabels: Record<DecisionState, string> = {
  supported_change: "Supported change",
  inconclusive: "Inconclusive",
  insufficient_evidence: "Insufficient evidence",
};
export const labels = {
  measured: "Measured experimental power",
  expected: "Calibrated expected experimental power",
  reference: "Raw reference inverter power",
  deviation: "Signed modelled generation deviation",
};
export const unavailable = "Not available";
export function numeric(value: number | null | undefined, digits = 1) {
  return value == null || !Number.isFinite(value)
    ? unavailable
    : new Intl.NumberFormat("en-GB", {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      }).format(value);
}
export function dateLabel(value: string, zone = "UTC") {
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: zone,
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}
export function timeLabel(value: string | number, zone = "UTC") {
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: zone,
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).format(new Date(value));
}
export function power(value: number | null | undefined, unit: string) {
  if (value == null) return unavailable;
  return `${numeric(unit === "W" ? value / 1000 : value, 2)} ${unit === "W" ? "kW" : unit}`;
}
export function safeExternalUrl(value: string) {
  try {
    const url = new URL(value);
    return ["https:", "http:"].includes(url.protocol) ? url.href : undefined;
  } catch {
    return undefined;
  }
}
