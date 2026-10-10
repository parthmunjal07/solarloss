"""Download and audit the pinned La Réunion Zenodo record."""

from __future__ import annotations

import hashlib
import json
import math
import time
import urllib.request
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import pandas as pd

RECORD_ID = 7291380
RECORD_DOI = "10.5281/zenodo.7291380"
RECORD_URL = "https://zenodo.org/records/7291380"
API_URL = "https://zenodo.org/api/records/7291380"
FILES: dict[str, dict[str, Any]] = {
    "dt1_solar_and_meteorological_measurement.csv": {
        "size": 1_541_026_563,
        "md5": "5b1e14695adbae4918bff49840916616",
        "role": "weather",
    },
    "dt2_electrical_production_inverter_1_with_faults.csv": {
        "size": 135_034_852,
        "md5": "b97d75f39d9545578f5ee85733a514be",
        "role": "target",
    },
    "dt3_electrical_production_inverter_2.csv": {
        "size": 126_216_618,
        "md5": "c03a8016450adb65a260be7be2fff2ca",
        "role": "reference",
    },
    "00_metadata_variable.jpg": {
        "size": 209_622,
        "md5": "e0f3296375eb4af0d38add7027f33261",
        "role": "metadata",
    },
}
ELECTRICAL_COLUMNS = ["time", "Fault", "Ia", "Ig", "Eg", "Fg", "Pg", "Va", "Vg"]
WEATHER_COLUMNS = ["time", "GTI", "DTI", "TA", "TPV"]
LABEL_DESCRIPTIONS = {
    0.0: "No-fault condition",
    1.0: "Uniform shading",
    2.1: "Constant partial shading, entire module; 1 shaded module",
    2.2: "Constant partial shading, entire module; 2 shaded modules",
    2.3: "Constant partial shading, entire module; 3 shaded modules",
    3.1: "Constant partial shading, portion of a module; one-third shaded module",
    3.2: "Constant partial shading, portion of a module; two-thirds shaded module",
    4.0: "Intermittent partial shading, static",
}
UNITS = {
    "Pg": "W",
    "Eg": "kWh",
    "Ia": "A",
    "Ig": "A",
    "Va": "V",
    "Vg": "V",
    "Fg": "Hz",
    "GTI": "W/m^2",
    "DTI": "W/m^2",
    "TA": "degC",
    "TPV": "degC",
}


def canonical_fault_label(value: float) -> float:
    """Restore documented decimal categories after float32 parsing, without rounding unknowns."""
    if pd.isna(value):
        return float('nan')
    for label in LABEL_DESCRIPTIONS:
        if abs(float(value) - label) <= 1e-6:
            return label
    return float(value)


def _url_for(name: str) -> str:
    if name not in FILES:
        raise KeyError(f"File is not part of pinned Zenodo record: {name}")
    return f"{RECORD_URL}/files/{name}?download=1"


def _md5(path: Path, block_size: int = 4 * 1024 * 1024) -> str:
    digest = hashlib.md5()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(block_size), b""):
            digest.update(block)
    return digest.hexdigest()


def download_file(name: str, data_dir: str | Path, *, verify: bool = True) -> Path:
    """Stream one file from the pinned record and verify its published size/MD5."""
    info = FILES[name]
    directory = Path(data_dir)
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / name
    if destination.exists() and destination.stat().st_size == info["size"]:
        if not verify or _md5(destination) == info["md5"]:
            return destination
    temporary = destination.with_suffix(destination.suffix + ".part")
    last_error: Exception | None = None
    for attempt in range(1, 6):
        try:
            request = urllib.request.Request(
                _url_for(name), headers={"User-Agent": "SolarLossResearch/0.1"}
            )
            digest = hashlib.md5()
            byte_count = 0
            with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as out:
                while True:
                    block = response.read(4 * 1024 * 1024)
                    if not block:
                        break
                    out.write(block)
                    digest.update(block)
                    byte_count += len(block)
            if byte_count != info["size"]:
                raise IOError(f"Expected {info['size']} bytes, received {byte_count}")
            if verify and digest.hexdigest() != info["md5"]:
                raise IOError(f"MD5 mismatch for {name}: {digest.hexdigest()}")
            temporary.replace(destination)
            return destination
        except Exception as exc:  # network failures are retried without accepting partial bytes
            last_error = exc
            temporary.unlink(missing_ok=True)
            if attempt < 5:
                time.sleep(min(attempt * 2, 8))
    raise IOError(f"Could not download verified {name}") from last_error


def verify_file(path: str | Path, name: str) -> dict[str, Any]:
    """Return a provenance check for an already downloaded file."""
    file_path = Path(path)
    info = FILES[name]
    digest = _md5(file_path)
    size = file_path.stat().st_size
    return {
        "file": name,
        "bytes": size,
        "expected_bytes": info["size"],
        "md5": digest,
        "expected_md5": info["md5"],
        "size_matches": size == info["size"],
        "checksum_matches": digest == info["md5"],
    }


def _time_offsets(values: pd.Series) -> Counter[str]:
    # The source stamps are ISO local times with explicit numeric offsets.
    offsets = values.astype("string").str.extract(r"([+-]\d{2}:\d{2})$")[0]
    return Counter(offsets.dropna().astype(str).tolist())


def audit_csv(
    path: str | Path,
    *,
    chunksize: int = 250_000,
    timestamp_column: str = "time",
    expected_frequency_seconds: float | None = None,
) -> dict[str, Any]:
    """Audit a CSV in bounded row chunks; retain only timestamp deltas and summaries."""
    file_path = Path(path)
    header = list(pd.read_csv(file_path, nrows=0).columns)
    row_count = 0
    null_counts: Counter[str] = Counter()
    min_values: dict[str, float] = {}
    max_values: dict[str, float] = {}
    label_counts: Counter[str] = Counter()
    offsets: Counter[str] = Counter()
    delta_parts: list[np.ndarray] = []
    invalid_timestamp_count = 0
    out_of_order_count = 0
    duplicate_timestamp_count = 0
    first_timestamp: pd.Timestamp | None = None
    last_timestamp: pd.Timestamp | None = None
    previous_timestamp: pd.Timestamp | None = None
    previous_raw: str | None = None

    for chunk in pd.read_csv(file_path, chunksize=chunksize, low_memory=False):
        row_count += len(chunk)
        null_counts.update({col: int(chunk[col].isna().sum()) for col in chunk.columns})
        if "Fault" in chunk:
            label_counts.update(
                {str(label): int(count) for label, count in chunk["Fault"].value_counts(dropna=False).items()}
            )
        for col in chunk.columns:
            if col == timestamp_column:
                continue
            numeric = pd.to_numeric(chunk[col], errors="coerce")
            if numeric.notna().any():
                low = float(numeric.min())
                high = float(numeric.max())
                min_values[col] = min(low, min_values.get(col, low))
                max_values[col] = max(high, max_values.get(col, high))
        offsets.update(_time_offsets(chunk[timestamp_column]))
        stamps = pd.to_datetime(chunk[timestamp_column], utc=True, errors="coerce")
        invalid_timestamp_count += int(stamps.isna().sum())
        valid = stamps.dropna()
        if valid.empty:
            continue
        if first_timestamp is None:
            first_timestamp = valid.iloc[0]
        if previous_timestamp is not None:
            boundary_delta = (valid.iloc[0] - previous_timestamp).total_seconds()
            if boundary_delta == 0:
                duplicate_timestamp_count += 1
            elif boundary_delta < 0:
                out_of_order_count += 1
            elif boundary_delta > 0:
                delta_parts.append(np.array([boundary_delta], dtype=np.float64))
        deltas = stamps.diff().dt.total_seconds().dropna().to_numpy(dtype=np.float64)
        duplicate_timestamp_count += int(np.count_nonzero(deltas == 0))
        out_of_order_count += int(np.count_nonzero(deltas < 0))
        delta_parts.append(deltas[deltas > 0])
        previous_timestamp = valid.iloc[-1]
        previous_raw = str(chunk[timestamp_column].iloc[-1])
        last_timestamp = valid.iloc[-1]

    delta = np.concatenate(delta_parts) if delta_parts else np.array([], dtype=np.float64)
    positive = delta[delta > 0]
    median_delta = float(np.median(positive)) if len(positive) else None
    common_intervals: list[dict[str, Any]] = []
    if len(positive):
        rounded = np.round(positive, 3)
        values, counts = np.unique(rounded, return_counts=True)
        order = np.argsort(counts)[::-1][:10]
        common_intervals = [
            {"seconds": float(values[i]), "count": int(counts[i])} for i in order
        ]
    gap_limit = 1800.0
    estimated_missing = None
    if median_delta and len(positive):
        eligible = positive[(positive > 3 * median_delta) & (positive <= gap_limit)]
        estimated_missing = int(np.maximum(np.rint(eligible / median_delta).astype(int) - 1, 0).sum())
    return {
        "file": file_path.name,
        "bytes": file_path.stat().st_size,
        "row_count": row_count,
        "columns": header,
        "null_counts": dict(null_counts),
        "numeric_min": min_values,
        "numeric_max": max_values,
        "timestamp_column": timestamp_column,
        "timestamp_start_utc": first_timestamp.isoformat() if first_timestamp is not None else None,
        "timestamp_end_utc": last_timestamp.isoformat() if last_timestamp is not None else None,
        "source_utc_offsets": dict(offsets),
        "invalid_timestamp_count": invalid_timestamp_count,
        "duplicate_timestamp_count": duplicate_timestamp_count,
        "out_of_order_count": out_of_order_count,
        "positive_interval_count": int(len(positive)),
        "interval_seconds": {
            "median": median_delta,
            "mean": float(np.mean(positive)) if len(positive) else None,
            "p05": float(np.quantile(positive, 0.05)) if len(positive) else None,
            "p95": float(np.quantile(positive, 0.95)) if len(positive) else None,
            "min": float(np.min(positive)) if len(positive) else None,
            "max": float(np.max(positive)) if len(positive) else None,
            "common": common_intervals,
            "above_1_5x_median_count": int(np.count_nonzero(positive > 1.5 * median_delta)) if median_delta else 0,
            "above_3x_median_count": int(np.count_nonzero(positive > 3 * median_delta)) if median_delta else 0,
            "estimated_missing_records_on_gaps_at_most_30min": estimated_missing,
            "nominal_publication_seconds": expected_frequency_seconds,
        },
        "fault_value_counts": dict(label_counts),
    }


def load_electrical(path: str | Path, *, target: bool) -> pd.DataFrame:
    """Load the electrical source with compact numeric dtypes for modelling."""
    cols = ELECTRICAL_COLUMNS if target else [c for c in ELECTRICAL_COLUMNS if c != "Fault"]
    dtype = {c: "float32" for c in cols if c not in {"time"}}
    frame = pd.read_csv(path, usecols=cols, dtype=dtype, low_memory=False)
    frame["timestamp"] = pd.to_datetime(frame.pop("time"), utc=True, errors="coerce")
    if target:
        frame = frame.rename(columns={"Fault": "fault_label", "Pg": "target_power_w"})
        frame['fault_label'] = frame['fault_label'].map(canonical_fault_label)
    else:
        frame = frame.rename(columns={"Pg": "reference_power_w"})
    return frame


def exact_alignment_report(target: pd.DataFrame, reference: pd.DataFrame) -> dict[str, Any]:
    """Measure timestamp intersection before any modelling or resampling."""
    left = target["timestamp"].dropna()
    right = reference["timestamp"].dropna()
    left_unique = left.drop_duplicates()
    right_unique = right.drop_duplicates()
    common = left_unique[left_unique.isin(right_unique)]
    denominator = min(len(left_unique), len(right_unique))
    return {
        "target_rows": int(len(target)),
        "reference_rows": int(len(reference)),
        "target_unique_timestamps": int(len(left_unique)),
        "reference_unique_timestamps": int(len(right_unique)),
        "exact_common_timestamps": int(len(common)),
        "exact_coverage_of_smaller_stream": float(len(common) / denominator) if denominator else 0.0,
        "target_unmatched_unique": int(len(left_unique) - len(common)),
        "reference_unmatched_unique": int(len(right_unique) - len(common)),
        "exact_alignment_only": True,
    }


def load_weather_bins(
    path: str | Path,
    *,
    chunksize: int = 500_000,
    bin_minutes: int = 5,
    expected_seconds_per_bin: int | None = None,
) -> pd.DataFrame:
    """Stream the 1 Hz weather file into bounded five-minute summary rows."""
    file_path = Path(path)
    expected = expected_seconds_per_bin or bin_minutes * 60
    columns = list(pd.read_csv(file_path, nrows=0).columns)
    missing = sorted(set(WEATHER_COLUMNS).difference(columns))
    if missing:
        raise ValueError(f"Weather file is missing documented columns: {missing}; found {columns}")
    frames = []
    dtypes = {name: "float32" for name in WEATHER_COLUMNS if name != "time"}
    measurements = ["GTI", "DTI", "TA", "TPV"]
    for chunk in pd.read_csv(file_path, usecols=WEATHER_COLUMNS, dtype=dtypes, chunksize=chunksize, low_memory=False):
        chunk["timestamp"] = pd.to_datetime(chunk.pop("time"), utc=True, errors="coerce")
        chunk = chunk.dropna(subset=["timestamp"])
        chunk["bin_start"] = chunk["timestamp"].dt.floor(f"{bin_minutes}min")
        aggregations: dict[str, tuple[str, str]] = {"weather_count": ("timestamp", "size")}
        for name in measurements:
            aggregations[f"{name}_sum"] = (name, "sum")
            aggregations[f"{name}_valid_count"] = (name, "count")
        aggregate = chunk.groupby("bin_start", sort=True).agg(**aggregations).reset_index()
        frames.append(aggregate)
    if not frames:
        return pd.DataFrame(columns=["bin_start", "weather_count", "weather_coverage", *measurements, *(f"{name}_coverage" for name in measurements)])
    stacked = pd.concat(frames, ignore_index=True)
    # A bin can straddle two read chunks; recombine using a count-weighted mean.
    sum_cols = [f"{name}_sum" for name in measurements]
    count_cols = [f"{name}_valid_count" for name in measurements]
    weighted = stacked.groupby("bin_start", sort=True).agg(
        weather_count=("weather_count", "sum"),
        **{col: (col, "sum") for col in sum_cols + count_cols},
    ).reset_index()
    for name in measurements:
        count_col = f"{name}_valid_count"
        weighted[name] = weighted[f"{name}_sum"].div(weighted[count_col].replace(0, np.nan))
        weighted[f"{name}_coverage"] = np.minimum(weighted[count_col] / expected, 1.0)
    weighted["weather_coverage"] = np.minimum(weighted["weather_count"] / expected, 1.0)
    return weighted[["bin_start", "weather_count", "weather_coverage", *measurements, *(f"{name}_coverage" for name in measurements)]].sort_values("bin_start", kind="stable").reset_index(drop=True)


def weather_bin_alignment_report(electrical_bins: pd.DataFrame, weather_bins: pd.DataFrame) -> dict[str, Any]:
    """Compare weather coverage against actual electrical daylight bins by period."""
    merged = electrical_bins.merge(weather_bins, on="bin_start", how="left", validate="one_to_one")
    observed = merged.loc[merged["daylight"]]
    total = len(observed)
    covered = int(observed["weather_coverage"].ge(0.80).sum()) if total else 0
    feature_coverage_columns = [f"{name}_coverage" for name in ("GTI", "DTI", "TA")]
    all_features = observed[feature_coverage_columns].ge(0.80).all(axis=1) if total and set(feature_coverage_columns).issubset(observed.columns) else (observed[["GTI", "DTI", "TA"]].notna().all(axis=1) if total else pd.Series(dtype=bool))
    return {
        "electrical_daylight_bins": int(total),
        "weather_covered_bins_at_80pct_of_nominal_1hz": covered,
        "weather_bin_coverage": float(covered / total) if total else 0.0,
        "all_model_weather_features_present_bins": int(all_features.sum()) if total else 0,
        "all_feature_coverage": float(all_features.mean()) if total else 0.0,
        "weather_start_utc": weather_bins["bin_start"].min().isoformat() if len(weather_bins) else None,
        "weather_end_utc": weather_bins["bin_start"].max().isoformat() if len(weather_bins) else None,
        "method": "Weather rows streamed into five-minute bins; a bin and each model feature require at least 80% of the documented 1 Hz nominal cadence. Field means use each field's non-null samples. The model uses actual CSV fields GTI, DTI, and ambient temperature only. The record's metadata image calls the diffuse field DHI; the CSV header is DTI.",
    }


def merge_electrical(target: pd.DataFrame, reference: pd.DataFrame) -> pd.DataFrame:
    """Pair exact timestamps one-to-one; duplicate or missing rows are excluded."""
    left = target.dropna(subset=["timestamp"]).drop_duplicates("timestamp", keep=False)
    right = reference.dropna(subset=["timestamp"]).drop_duplicates("timestamp", keep=False)
    merged = left.merge(right, on="timestamp", how="inner", validate="one_to_one")
    return merged.sort_values("timestamp", kind="stable").reset_index(drop=True)


def as_json_file(value: Any, path: str | Path) -> Path:
    """Write compact, strict JSON (no NaN/Infinity tokens)."""
    def clean(item: Any) -> Any:
        if isinstance(item, dict):
            return {str(key): clean(child) for key, child in item.items()}
        if isinstance(item, (list, tuple)):
            return [clean(child) for child in item]
        if isinstance(item, (pd.Timestamp, datetime, date)):
            return item.isoformat()
        if isinstance(item, np.ndarray):
            return clean(item.tolist())
        if isinstance(item, np.generic):
            return clean(item.item())
        if isinstance(item, float) and not math.isfinite(item):
            return None
        if isinstance(item, Path):
            return str(item)
        return item

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(clean(value), indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return destination
