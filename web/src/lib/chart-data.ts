import type { Review } from "./types";
export interface PlotPoint {
  time: number;
  timestamp: string;
  measured: number | null;
  expected: number | null;
  reference: number | null;
  residual: number | null;
  bounds: [number, number] | null;
  valid: boolean;
  gap?: boolean;
}
export function plotPoints(review: Review): PlotPoint[] {
  const scale = review.powerUnit === "W" ? 1000 : 1;
  const convert = (v: number | null | undefined) =>
    v == null ? null : v / scale;
  const points: PlotPoint[] = [];
  const exclusions = review.exclusions.map((e) => ({
    start: Date.parse(e.start),
    end: Date.parse(e.end),
  }));
  review.samples.forEach((sample, i) => {
    const time = Date.parse(sample.timestamp),
      previous = review.samples[i - 1];
    if (previous) {
      const prior = Date.parse(previous.timestamp),
        markers = new Set<number>();
      if (
        review.maxGapSeconds !== null &&
        time - prior > review.maxGapSeconds * 1000
      )
        markers.add(prior + 1);
      // Explicit exclusions must break a line even when the source has no row inside them.
      for (const e of exclusions)
        if (e.start < time && e.end > prior) {
          markers.add(Math.max(prior + 1, e.start));
          markers.add(Math.min(time - 1, e.end));
        }
      for (const marker of [...markers]
        .filter((t) => t > prior && t < time)
        .sort((a, b) => a - b))
        points.push({
          time: marker,
          timestamp: previous.timestamp,
          measured: null,
          expected: null,
          reference: null,
          residual: null,
          bounds: null,
          valid: false,
          gap: true,
        });
    }
    const excluded = exclusions.some((e) => time >= e.start && time <= e.end);
    const valid = sample.valid && !excluded;
    // v0.2 retains measured channels even when the model estimate is unavailable.
    // Keep explicit exclusion/gap markers across all channels; never fill nulls.
    const measuredAvailable =
      !excluded && (valid || review.origin === "api-v2");
    points.push({
      time,
      timestamp: sample.timestamp,
      measured: measuredAvailable ? convert(sample.measured_power) : null,
      expected: valid ? convert(sample.expected_power) : null,
      reference: measuredAvailable ? convert(sample.raw_reference_power) : null,
      residual: valid ? convert(review.residuals?.[sample.timestamp]) : null,
      bounds:
        valid &&
        sample.expected_lower_bound !== undefined &&
        sample.expected_upper_bound !== undefined
          ? [
              sample.expected_lower_bound / scale,
              sample.expected_upper_bound / scale,
            ]
          : null,
      valid,
    });
  });
  return points;
}
// Keep invalid runs, surrounding valid points, event/alert boundaries and bucket extrema.
// If mandatory markers exceed the budget, refuse a misleading continuous chart.
export function downsample(
  points: PlotPoint[],
  boundaries: number[] = [],
  limit = 1500,
): PlotPoint[] {
  if (points.length <= limit) return points;
  const pinned = new Set([0, points.length - 1]);
  points.forEach((p, i) => {
    const before = points[i - 1],
      after = points[i + 1];
    if (
      p.gap ||
      (before && (before.bounds === null) !== (p.bounds === null)) ||
      (after && (after.bounds === null) !== (p.bounds === null)) ||
      (before && before.valid !== p.valid) ||
      (after && after.valid !== p.valid)
    )
      pinned.add(i);
    for (const boundary of boundaries)
      if (p.time >= boundary && (!before || before.time < boundary)) {
        pinned.add(i);
        if (i) pinned.add(i - 1);
      }
  });
  if (pinned.size > limit) return [];
  const buckets = Math.floor((limit - pinned.size) / 12);
  if (buckets < 1) return [];
  const size = Math.ceil(points.length / buckets);
  for (let start = 0; start < points.length; start += size) {
    const end = Math.min(start + size, points.length);
    for (const key of [
      "measured",
      "expected",
      "reference",
      "residual",
      "lower",
      "upper",
    ] as const) {
      const get = (i: number) =>
        key === "lower"
          ? (points[i].bounds?.[0] ?? null)
          : key === "upper"
            ? (points[i].bounds?.[1] ?? null)
            : points[i][key];
      let min = -1,
        max = -1;
      for (let i = start; i < end; i++) {
        const value = get(i);
        if (value === null) continue;
        if (min < 0 || value < get(min)!) min = i;
        if (max < 0 || value > get(max)!) max = i;
      }
      if (min >= 0) pinned.add(min);
      if (max >= 0) pinned.add(max);
    }
  }
  return [...pinned].sort((a, b) => a - b).map((i) => points[i]);
}
export function missingRegions(points: PlotPoint[]) {
  const regions: { start: number; end: number }[] = [];
  let start: number | null = null;
  points.forEach((p, i) => {
    if (!p.valid && start === null) start = points[Math.max(0, i - 1)].time;
    if (start !== null && (p.valid || i === points.length - 1)) {
      regions.push({ start, end: p.time });
      start = null;
    }
  });
  return regions;
}
