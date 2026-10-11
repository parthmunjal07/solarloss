"""Bounded, self-contained SVG presentation of validated source samples."""

import math
from datetime import datetime, timezone
from html import escape
from typing import Any

from .errors import InvalidArtifact

MAX_CHART_SAMPLES = 50_000
MAX_CHART_POINTS = 1_500


def _time(value: str) -> float:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.utcoffset() is None:
            raise ValueError("Timestamp has no timezone")
        result = parsed.timestamp()
    except (ValueError, TypeError, OverflowError) as exc:
        raise InvalidArtifact("Invalid chart timestamp") from exc
    if not math.isfinite(result):
        raise InvalidArtifact("Nonfinite chart timestamp")
    return result


def render_power_chart(review: dict[str, Any]) -> str:
    """Reduce display points only, pinning every channel gap and boundary.

    All original values remain in the HTML appendix. No scientific total is
    integrated or inferred here. Unsafe reduction yields an explicit unavailable
    chart rather than connecting unsupported intervals.
    """
    samples = review["series"]["samples"]
    unavailable = '<p class="chart-unavailable">Chart unavailable within the safe display budget. All original measurements remain in the technical appendix.</p>'
    if not 2 <= len(samples) <= MAX_CHART_SAMPLES:
        return unavailable
    times = [_time(s["timestamp"]) for s in samples]
    if any(b <= a for a, b in zip(times, times[1:])):
        raise InvalidArtifact("Chart samples must be strictly chronological")
    exclusions = [
        (_time(e["start"]), _time(e["end"]))
        for e in [
            *review["provenance"]["exclusions"],
            *review["series"]["downsampling"]["gap_markers"],
        ]
    ]
    keys = ("measured_power", "expected_power", "raw_reference_power")
    channels: list[list[float | None]] = []
    for key in keys:
        values = []
        for s, t in zip(samples, times):
            value = s[key]
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, (float, int))
                or not math.isfinite(value)
                or abs(value) > 1e12
            ):
                raise InvalidArtifact("Chart power must be finite and bounded")
            excluded = any(a <= t <= b for a, b in exclusions)
            values.append(
                None if excluded or (key == "expected_power" and not s["valid"]) else value
            )
        channels.append(values)
    # Mark edges crossing a source-declared gap even if it contains no sample.
    breaks = {
        i
        for i in range(1, len(times))
        if any(a < times[i] and b > times[i - 1] for a, b in exclusions)
    }
    pinned = {0, len(samples) - 1}
    for values in channels:
        for i in range(1, len(values)):
            if (values[i] is None) != (values[i - 1] is None):
                pinned.update((i - 1, i))
    for i in breaks:
        pinned.update((i - 1, i))
    context = review["experiment"]["event_context"]
    boundary_times = list((context.get("detector_confirmations_utc") or {}).values())
    boundary_times += list((context.get("label_interval_utc") or {}).values())
    for boundary in map(_time, boundary_times):
        for i, t in enumerate(times):
            if t >= boundary:
                pinned.update((max(0, i - 1), i))
                break
    if len(pinned) > MAX_CHART_POINTS:
        return unavailable
    if len(samples) <= MAX_CHART_POINTS:
        indices = list(range(len(samples)))
    else:
        buckets = (MAX_CHART_POINTS - len(pinned)) // 6
        if buckets < 1:
            return unavailable
        width = math.ceil(len(samples) / buckets)
        for start in range(0, len(samples), width):
            for values in channels:
                eligible = [
                    i
                    for i in range(start, min(len(samples), start + width))
                    if values[i] is not None
                ]
                if eligible:
                    pinned.add(min(eligible, key=lambda i: values[i]))
                    pinned.add(max(eligible, key=lambda i: values[i]))
        indices = sorted(pinned)
    all_values = [v for values in channels for v in values if v is not None]
    if not all_values:
        return unavailable
    low, high = min(0, min(all_values)), max(1, max(all_values))
    scale = 1000 if review["series"]["power_unit"] == "W" else 1
    unit = "kW" if scale == 1000 else review["series"]["power_unit"]

    def x(t: float) -> float:
        return 64 + (t - times[0]) / (times[-1] - times[0]) * 772

    def y(v: float) -> float:
        return 260 - (v - low) / (high - low) * 216

    paths = []
    for key, values, color, dash in zip(
        keys, channels, ("#b45309", "#3b5b8c", "#4a5568"), ("", "6 4", "2 5")
    ):
        commands, open_segment = [], False
        previous = -1
        for i in indices:
            value = values[i]
            if value is None:
                open_segment = False
                previous = i
                continue
            if any(previous < b <= i for b in breaks):
                open_segment = False
            commands.append(f"{'L' if open_segment else 'M'}{x(times[i]):.2f},{y(value):.2f}")
            open_segment, previous = True, i
        paths.append(
            f'<path data-channel="{key}" d="{" ".join(commands)}" '
            f'stroke="{color}" stroke-width="2" stroke-dasharray="{dash}" fill="none"/>'
        )
    grid, labels = [], []
    for i in range(5):
        value = low + (high - low) * i / 4
        gy = y(value)
        grid.append(f'<path d="M64 {gy:.2f}H836" stroke="#e4ded3"/>')
        labels.append(f'<text x="52" y="{gy + 4:.2f}" text-anchor="end">{value / scale:.2f}</text>')
        t = times[0] + (times[-1] - times[0]) * i / 4
        labels.append(
            f'<text x="{x(t):.2f}" y="287" text-anchor="middle">'
            f"{datetime.fromtimestamp(t, tz=timezone.utc).strftime('%H:%M')}</text>"
        )
    timing = []
    interval = context.get("label_interval_utc")
    if interval:
        left, right = (
            max(times[0], _time(interval["start"])),
            min(times[-1], _time(interval["end"])),
        )
        if right >= left:
            timing.append(
                f'<rect x="{x(left):.2f}" y="44" width="{x(right) - x(left):.2f}" height="216" fill="#eadfc8" opacity="0.5"/>'
            )
            timing.append('<text x="70" y="31">Source-labelled intervention</text>')
    confirmation = (context.get("detector_confirmations_utc") or {}).get("5_minute_primary")
    if confirmation:
        t = _time(confirmation)
        if times[0] <= t <= times[-1]:
            timing.append(f'<path d="M{x(t):.2f} 44V260" stroke="#14213d" stroke-dasharray="3 3"/>')
    return (
        '<svg class="power-chart" viewBox="0 0 900 316" role="img" aria-labelledby="power-title power-description" xmlns="http://www.w3.org/2000/svg">'
        '<title id="power-title">Measured versus model-expected target power</title>'
        '<desc id="power-description">Amber measured target AC power; dashed blue model-expected target power; dotted gray raw reference inverter power. Missing model estimates and source-declared gaps are not connected. When supplied, shading bounds are source labels and the vertical dashed line is the primary detector confirmation.</desc>'
        '<g font-family="system-ui,sans-serif" font-size="12" fill="#4a5568">'
        + "".join(timing + grid + paths + labels)
        + f'<text x="64" y="309">UTC · {escape(unit, quote=True)}</text></g></svg>'
        + f'<p class="small">Display: {len(indices):,} points from {len(samples):,} retained records. Source values are unchanged; energy totals use original supported intervals.</p>'
    )
