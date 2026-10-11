import { useMemo, useState, useId } from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceArea,
  ReferenceLine,
  Brush,
} from "recharts";
import { downsample, missingRegions, plotPoints } from "../../lib/chart-data";
import type { PlotPoint } from "../../lib/chart-data";
import type { Review } from "../../lib/types";
import { labels, numeric, timeLabel } from "../../lib/formatters";

function MeasurementTooltip({
  active,
  payload,
  unit,
  analyst,
  sourceV2 = false,
}: {
  active?: boolean;
  payload?: readonly { payload?: PlotPoint }[];
  unit: string;
  analyst: boolean;
  sourceV2?: boolean;
}) {
  const p = payload?.[0]?.payload;
  if (!active || !p) return null;
  return (
    <div className="chart-tooltip">
      <strong className="num">{timeLabel(p.timestamp)} UTC</strong>
      <p>
        {p.gap
          ? "Unsupported measurement gap"
          : p.valid
            ? "Valid"
            : sourceV2
              ? "Invalid source sample; missing-channel reason not supplied"
              : "Excluded"}
      </p>
      <dl>
        <div>
          <dt>Measured experimental</dt>
          <dd className="num">
            {numeric(p.measured, 2)} {p.measured !== null && unit}
          </dd>
        </div>
        <div>
          <dt>Calibrated expected</dt>
          <dd className="num">
            {numeric(p.expected, 2)} {p.expected !== null && unit}
          </dd>
        </div>
        {analyst && (
          <div>
            <dt>Raw reference</dt>
            <dd className="num">
              {numeric(p.reference, 2)} {p.reference !== null && unit}
            </dd>
          </div>
        )}
      </dl>
      <span className="small mono">{p.timestamp}</span>
    </div>
  );
}
export default function PowerChart({
  review,
  analyst,
}: {
  review: Review;
  analyst: boolean;
}) {
  const patternId = useId().replaceAll(":", "");
  const data = useMemo(
    () =>
      downsample(plotPoints(review), [
        ...(review.event
          ? [Date.parse(review.event.start), Date.parse(review.event.end)]
          : []),
        ...review.alerts.map(Date.parse),
      ]),
    [review],
  );
  const [range, setRange] = useState<{
    startIndex: number;
    endIndex: number;
  } | null>(null);
  const [channels, setChannels] = useState({
    measured: true,
    expected: true,
    reference: false,
  });
  const [selected, setSelected] = useState(0);
  const source = review.samples[selected];
  const visible = range
    ? data.slice(range.startIndex, range.endIndex + 1)
    : data;
  const missing = useMemo(() => missingRegions(visible), [visible]);
  const unit = review.powerUnit === "W" ? "kW" : review.powerUnit;
  if (!data.length)
    return (
      <div className="empty-state">
        <h3>Chart not available</h3>
        <p>
          There are too many measurement gaps to preserve safely within the
          chart budget. Inspect the original measurement table.
        </p>
      </div>
    );
  const domain: [number, number] = [
    visible[0].time,
    visible[visible.length - 1].time,
  ];
  const tick = { fill: "var(--text-muted)", fontSize: 12 };
  return (
    <section
      className="chart-panel"
      id="performance-comparison"
      aria-label="Performance comparison"
      tabIndex={-1}
    >
      <div className="chart-heading">
        <div>
          <p className="eyebrow">Power over the recorded interval</p>
          <h2>Measured against expected</h2>
        </div>
        <span className="small">UTC · {unit}</span>
      </div>
      <div
        className="chart-legend chart-toggles"
        role="group"
        aria-label="Power channels"
      >
        {(
          [
            ["measured", "Measured"],
            ["expected", "Model-expected"],
            ["reference", "Raw reference"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            aria-pressed={channels[key]}
            onClick={() => setChannels((c) => ({ ...c, [key]: !c[key] }))}
          >
            <i
              className={`mini-line ${key === "measured" ? "measured-line" : key === "expected" ? "expected-line" : "raw-line"}`}
            />
            {label}
          </button>
        ))}
      </div>
      <div className="sr-only">
        <span>
          <i className="mini-line measured-line" />
          {labels.measured}
        </span>
        <span>
          <i className="mini-line expected-line" />
          {labels.expected}
        </span>
        {analyst && (
          <span>
            <i className="mini-line raw-line" />
            {labels.reference}
          </span>
        )}
      </div>
      <div
        className="main-chart num"
        role="img"
        aria-label={
          review.v2
            ? "Measured target power, calibrated expected target power and separate reference measurements. Invalid model estimates remain gaps; recorded measured channels remain available. Original values are available in Inspect measurements."
            : "Measured experimental power compared with calibrated expected experimental power. Excluded measurements are gaps. Original values are available in Inspect measurements."
        }
      >
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={visible}
            margin={{ top: 24, right: 16, bottom: 8, left: 0 }}
            onClick={(e) => {
              const i = Number(e.activeTooltipIndex);
              const point = visible[i];
              if (point && !point.gap) {
                const index = review.samples.findIndex(
                  (s) => s.timestamp === point.timestamp,
                );
                if (index >= 0) setSelected(index);
              }
            }}
          >
            <defs>
              <pattern
                id={patternId}
                width="6"
                height="6"
                patternUnits="userSpaceOnUse"
                patternTransform="rotate(45)"
              >
                <line
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="6"
                  stroke="var(--insufficient-border)"
                  strokeWidth="1"
                />
              </pattern>
            </defs>
            <CartesianGrid vertical={false} stroke="var(--border)" />
            <XAxis
              dataKey="time"
              type="number"
              domain={domain}
              tickFormatter={(v) => timeLabel(v)}
              tickCount={6}
              tick={tick}
              minTickGap={48}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={tick}
              axisLine={false}
              tickLine={false}
              width={48}
              tickFormatter={(v) => numeric(v, 1)}
            />
            {review.event && (
              <ReferenceArea
                x1={Date.parse(review.event.start)}
                x2={Date.parse(review.event.end)}
                fill="var(--interval)"
                fillOpacity={0.6}
                label={{
                  value: "Documented shading",
                  position: "insideTopLeft",
                  fill: "var(--text-muted)",
                  fontSize: 12,
                }}
              />
            )}
            {missing.map((m) => (
              <ReferenceArea
                key={m.start}
                x1={m.start}
                x2={m.end}
                fill={`url(#${patternId})`}
                fillOpacity={1}
              />
            ))}
            {analyst && (
              <Area
                type="linear"
                dataKey="bounds"
                fill="var(--reference-band)"
                stroke="none"
                connectNulls={false}
                isAnimationActive={false}
              />
            )}
            {channels.expected && (
              <Line
                type="linear"
                dataKey="expected"
                name="Calibrated expected experimental power"
                stroke="var(--reference)"
                strokeWidth={2}
                strokeDasharray="6 4"
                dot={false}
                connectNulls={false}
                isAnimationActive={false}
              />
            )}
            {channels.measured && (
              <Line
                type="linear"
                dataKey="measured"
                name="Measured experimental power"
                stroke="var(--measured)"
                strokeWidth={2}
                dot={false}
                connectNulls={false}
                isAnimationActive={false}
              />
            )}
            {channels.reference && (
              <Line
                type="linear"
                dataKey="reference"
                name="Raw reference inverter power"
                stroke="var(--text-muted)"
                strokeWidth={1}
                strokeDasharray="2 4"
                dot={false}
                connectNulls={false}
                isAnimationActive={false}
              />
            )}
            {review.alerts.map((time, i) => (
              <ReferenceLine
                key={time}
                x={Date.parse(time)}
                stroke="var(--text)"
                strokeDasharray="3 3"
                label={{
                  value: `Detector ${i + 1}`,
                  position: "insideBottomRight",
                  fill: "var(--text)",
                  fontSize: 12,
                }}
              />
            ))}
            <Tooltip
              content={
                <MeasurementTooltip
                  unit={unit}
                  analyst={channels.reference}
                  sourceV2={!!review.v2}
                />
              }
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <p className="small chart-note">
        Solid amber: measured. Dashed blue: calibrated expectation. Hatched
        regions: invalid or unsupported samples.{" "}
        {review.event
          ? "The shaded interval is a documented experimental label; the alert line is the automatic detector confirmation."
          : "Precise intervention boundaries and detector timestamps are not supplied by this artifact."}
      </p>
      <div className="source-selection">
        <label htmlFor={`${patternId}-sample`}>
          Inspect an exact source timestamp
        </label>
        <input
          id={`${patternId}-sample`}
          type="range"
          min="0"
          max={review.samples.length - 1}
          value={selected}
          onChange={(e) => setSelected(Number(e.target.value))}
          aria-valuetext={source?.timestamp}
        />
        {source && (
          <div className="selected-source" aria-live="polite">
            <strong className="mono">{source.timestamp}</strong>
            <p className="small">
              {source.valid
                ? "Valid source sample"
                : "Invalid source sample · model expectation unavailable where null"}
            </p>
            <dl>
              {(
                [
                  ["Measured", source.measured_power],
                  ["Model-expected", source.expected_power],
                  ["Raw reference", source.raw_reference_power],
                ] as const
              ).map(([label, value]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd className="num">
                    {value === null ? "Not available" : String(value)}{" "}
                    {value !== null && review.powerUnit}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        )}
      </div>
      <div className="brush">
        <span className="small">
          Chart range · drag handles or use arrow keys on a focused handle
        </span>
        <ResponsiveContainer width="100%" height={48}>
          <ComposedChart data={data}>
            <Brush
              dataKey="time"
              height={32}
              stroke="var(--reference)"
              fill="var(--surface-muted)"
              tickFormatter={(v) => timeLabel(v)}
              startIndex={range?.startIndex ?? 0}
              endIndex={range?.endIndex ?? data.length - 1}
              onChange={(v) => {
                if (
                  v.startIndex !== undefined &&
                  v.endIndex !== undefined &&
                  v.endIndex > v.startIndex
                )
                  setRange({
                    startIndex: v.startIndex,
                    endIndex: v.endIndex,
                  });
              }}
            />
          </ComposedChart>
        </ResponsiveContainer>
        <button className="text-button" onClick={() => setRange(null)}>
          Reset chart range
        </button>
      </div>
      <p className="small">
        Chart range: {timeLabel(domain[0])}–{timeLabel(domain[1])} UTC.
        Full-event energy totals above remain unchanged.
      </p>
      <details className="channel-explanation">
        <summary>What do the power channels mean?</summary>
        <p className="small">
          Measured: target inverter AC output. Model-expected: calibrated
          healthy target expectation, not a measurement. Raw reference:
          uncalibrated comparison-inverter AC output, a model input. Missing
          model values remain gaps. The recorded intervention bounds and
          automatic detector confirmation describe different events.
        </p>
      </details>
      {analyst && (
        <>
          {review.residuals ? (
            <div className="residual-section">
              <h3>Signed residual</h3>
              <p className="small">
                Expected minus measured, from source residual values · {unit}
              </p>
              <div
                className="residual-chart num"
                role="img"
                aria-label="Source signed residual values, with positive values showing expected above measured and honest gaps at excluded intervals."
              >
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart
                    data={visible}
                    margin={{ right: 16, top: 8, bottom: 8 }}
                  >
                    <CartesianGrid vertical={false} stroke="var(--border)" />
                    <XAxis
                      dataKey="time"
                      type="number"
                      domain={domain}
                      tickFormatter={(v) => timeLabel(v)}
                      tickCount={6}
                      tick={tick}
                      minTickGap={48}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tick={tick}
                      axisLine={false}
                      tickLine={false}
                      width={48}
                    />
                    <ReferenceLine y={0} stroke="var(--text-muted)" />
                    <Area
                      dataKey="residual"
                      stroke="var(--reference)"
                      fill="var(--reference-band)"
                      connectNulls={false}
                      isAnimationActive={false}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>
          ) : (
            <p className="small">
              Signed residual chart: Not available. Per-sample residuals are not
              supplied by this artifact.
            </p>
          )}
          <p className="small">
            Chart presentation uses {data.length} points from{" "}
            {review.samples.length} original records. Energy figures always come
            from the scientific source, never from the plotted points.
          </p>
        </>
      )}
    </section>
  );
}
