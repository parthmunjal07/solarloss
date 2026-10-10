"""Leakage-aware chronological modelling and effect summaries."""

from __future__ import annotations

from collections import Counter
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import HuberRegressor, LinearRegression
from sklearn.metrics import mean_absolute_error

from .dataset import LABEL_DESCRIPTIONS, canonical_fault_label

ANALYSIS_VERSION = "0.1.0"
BIN_MINUTES = 5
DAYLIGHT_REFERENCE_MIN_W = 100.0
CAPACITY_TABLE_TARGET_KWP = 2.10  # 12 x 175 W modules, if Table 1 line mapping is literal
CAPACITY_TABLE_REFERENCE_KWP = 2.04  # 12 x 170 W modules, if Table 1 line mapping is literal
CAPACITY_PROSE_TARGET_KWP = 2.04  # paper prose; conflicts with Table 1 arithmetic/mapping
CAPACITY_PROSE_REFERENCE_KWP = 2.09  # paper prose; does not exactly equal 12 x 175 W
VALIDATION_IMPROVEMENT_FLOOR = 0.05
EPISODE_GAP_SECONDS = 300.0
MAX_INTEGRATION_GAP_MULTIPLE = 3.0
MIN_EPISODES_FOR_INFERENCE = 3
MIN_TEST_HEALTHY_DAYS = 10
MIN_COVERAGE = 0.80
MAX_HELDOUT_NMAE = 0.20
MAX_HELDOUT_RELATIVE_BIAS = 0.10
REFERENCE_MONTHLY_RELATIVE_RANGE_LIMIT = 0.15


def make_bins(paired: pd.DataFrame, weather_bins: pd.DataFrame | None = None) -> pd.DataFrame:
    """Create nonoverlapping five-minute bins; never forward-fill across data gaps."""
    frame = paired.copy()
    frame["bin_start"] = frame["timestamp"].dt.floor(f"{BIN_MINUTES}min")
    frame["is_fault"] = frame["fault_label"].fillna(0).gt(0)
    frame["label_text"] = frame["fault_label"].map(LABEL_DESCRIPTIONS)
    grouped = frame.groupby("bin_start", sort=True).agg(
        target_power_w=("target_power_w", "mean"),
        reference_power_w=("reference_power_w", "mean"),
        fault_fraction=("is_fault", "mean"),
        label_known_fraction=("fault_label", lambda values: float(values.notna().mean())),
        row_count=("timestamp", "size"),
        target_time_first=("timestamp", "min"),
        target_time_last=("timestamp", "max"),
    )
    labels = frame.loc[frame["is_fault"]].groupby("bin_start")["fault_label"].agg(
        lambda values: ",".join(sorted({f"{float(x):g}" for x in values}))
    )
    grouped["fault_labels"] = labels
    grouped["fault_labels"] = grouped["fault_labels"].fillna("")
    grouped.index.name = "bin_start"
    result = grouped.reset_index()
    if weather_bins is not None:
        result = result.merge(weather_bins, on="bin_start", how="left", validate="one_to_one")
    result["local_day"] = result["bin_start"].dt.tz_convert("Indian/Reunion").dt.date
    result["daylight"] = result["reference_power_w"].ge(DAYLIGHT_REFERENCE_MIN_W)
    result["healthy"] = result["fault_fraction"].eq(0.0) & result["label_known_fraction"].eq(1.0)
    result["paired_valid"] = result[["target_power_w", "reference_power_w"]].notna().all(axis=1)
    if "weather_coverage" in result:
        feature_coverage = [f"{name}_coverage" for name in ("GTI", "DTI", "TA")]
        weather_features_covered = (
            result[feature_coverage].ge(0.80).all(axis=1)
            if set(feature_coverage).issubset(result.columns)
            else result[["GTI", "DTI", "TA"]].notna().all(axis=1)
        )
        result["weather_valid"] = result["weather_coverage"].ge(0.80) & weather_features_covered
    return result.sort_values("bin_start", kind="stable").reset_index(drop=True)


def chronological_splits(bins: pd.DataFrame) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    """Split by whole local calendar days in chronological order (60/20/20)."""
    days = sorted(pd.Series(bins["local_day"].dropna().unique()).tolist())
    if len(days) < 5:
        raise ValueError(f"Need at least five observed days for chronological splits; found {len(days)}")
    train_end_i = max(1, min(len(days) - 2, int(np.floor(0.60 * len(days)))))
    validation_end_i = max(train_end_i + 1, min(len(days) - 1, int(np.floor(0.80 * len(days)))))
    train_end_day = days[train_end_i]
    validation_end_day = days[validation_end_i]
    train = bins.loc[bins["local_day"].isin(days[:train_end_i])].copy()
    validation = bins.loc[bins["local_day"].isin(days[train_end_i:validation_end_i])].copy()
    test = bins.loc[bins["local_day"].isin(days[validation_end_i:])].copy()
    meta = {
        "method": "chronological whole-local-day split; 60% train / 20% validation / 20% held-out by observed day count",
        "train_start_day": str(days[0]),
        "train_end_day_inclusive": str(days[train_end_i - 1]),
        "validation_start_day": str(days[train_end_i]),
        "validation_end_day_inclusive": str(days[validation_end_i - 1]),
        "test_start_day": str(days[validation_end_i]),
        "test_end_day_inclusive": str(days[-1]),
        "train_days": int(train["local_day"].nunique()),
        "validation_days": int(validation["local_day"].nunique()),
        "test_days": int(test["local_day"].nunique()),
        "day_count": int(len(days)),
    }
    return {"train": train, "validation": validation, "test": test}, meta


def _score(observed: pd.Series, predicted: np.ndarray) -> dict[str, Any]:
    valid = observed.notna() & np.isfinite(predicted)
    y = observed.loc[valid].to_numpy(dtype=float)
    p = np.asarray(predicted, dtype=float)[valid.to_numpy()]
    if not len(y):
        return {"n": 0, "mae_w": None, "nmae": None, "bias_w": None, "rmse_w": None, "mean_observed_w": None}
    error = p - y
    mean_actual = float(np.mean(y))
    return {
        "n": int(len(y)),
        "mae_w": float(mean_absolute_error(y, p)),
        "nmae": float(mean_absolute_error(y, p) / mean_actual) if mean_actual else float("nan"),
        "bias_w": float(np.mean(error)),
        "rmse_w": float(np.sqrt(np.mean(error**2))),
        "mean_observed_w": mean_actual,
    }


def _capacity_prediction(reference_power: pd.Series, ratio: float) -> np.ndarray:
    return reference_power.to_numpy(dtype=float) * ratio


def _fit_linear(training: pd.DataFrame, model_name: str) -> dict[str, Any]:
    x = training[["reference_power_w"]].to_numpy(dtype=float)
    y = training["target_power_w"].to_numpy(dtype=float)
    estimator = LinearRegression().fit(x, y)
    return {
        "name": model_name,
        "estimator": estimator,
        "features": ["reference_power_w"],
        "training_rows": int(len(training)),
        "preprocessing": "Five-minute healthy daylight means; no scaling or imputation; exact paired target/reference observations only.",
    }


def _fit_huber(training: pd.DataFrame) -> dict[str, Any]:
    estimator = HuberRegressor(epsilon=1.35, alpha=0.0001, max_iter=500).fit(
        training[["reference_power_w"]].to_numpy(dtype=float),
        training["target_power_w"].to_numpy(dtype=float),
    )
    return {
        "name": "huber_reference",
        "estimator": estimator,
        "features": ["reference_power_w"],
        "training_rows": int(len(training)),
        "preprocessing": "Five-minute healthy daylight means; no scaling or imputation; exact paired target/reference observations only.",
    }


def _fit_weather(training: pd.DataFrame) -> dict[str, Any]:
    features = ["reference_power_w", "GTI", "DTI", "TA"]
    subset = _model_frame(training, {"name": "weather_assisted_linear", "features": features}).dropna(subset=["target_power_w"])
    estimator = LinearRegression().fit(subset[features].to_numpy(dtype=float), subset["target_power_w"].to_numpy(dtype=float))
    return {
        "name": "weather_assisted_linear",
        "estimator": estimator,
        "features": features,
        "training_rows": int(len(subset)),
        "preprocessing": "Five-minute healthy daylight means; rows with any selected feature missing are excluded; no scaling or imputation.",
    }


def _feature_valid(model: dict[str, Any], frame: pd.DataFrame) -> pd.Series:
    """Require usable predictors and, for weather, predeclared per-bin coverage."""
    valid = frame[model["features"]].notna().all(axis=1)
    if model.get("name") == "weather_assisted_linear":
        if "weather_coverage" in frame:
            valid &= frame["weather_coverage"].ge(0.80)
        for name in ("GTI", "DTI", "TA"):
            column = f"{name}_coverage"
            if column in frame:
                valid &= frame[column].ge(0.80)
            elif name in frame:
                valid &= frame[name].notna()
    return valid.fillna(False)


def _model_frame(frame: pd.DataFrame, model: dict[str, Any]) -> pd.DataFrame:
    return frame.loc[_feature_valid(model, frame)].copy()


def _predict(model: dict[str, Any], frame: pd.DataFrame) -> np.ndarray:
    if "fixed_capacity_ratio" in model:
        return _capacity_prediction(frame["reference_power_w"], float(model["fixed_capacity_ratio"]))
    return model["estimator"].predict(frame[model["features"]].to_numpy(dtype=float))


def _parameters(model: dict[str, Any]) -> dict[str, Any]:
    if "fixed_capacity_ratio" in model:
        ratio = float(model["fixed_capacity_ratio"])
        return {
            "name": model["name"],
            "features": model["features"],
            "parameters": {"target_to_reference_nameplate_capacity_ratio": ratio},
            "training_rows": 0,
            "preprocessing": "Fixed nameplate capacity ratio; no fitting; applied to exact paired reference power.",
            "intercept_w": 0.0,
            "coefficients": {"reference_power_w": ratio},
            "dependencies": ["numpy", "pandas"],
        }
    estimator = model["estimator"]
    return {
        "name": model["name"],
        "features": model["features"],
        "parameters": {"epsilon": 1.35, "alpha": 0.0001, "max_iter": 500} if model["name"] == "huber_reference" else {},
        "training_rows": model["training_rows"],
        "preprocessing": model["preprocessing"],
        "intercept_w": float(estimator.intercept_),
        "coefficients": {name: float(value) for name, value in zip(model["features"], estimator.coef_)},
        "dependencies": ["numpy", "pandas", "scipy", "scikit-learn"],
    }


def _day_block_bootstrap(
    observed: pd.Series,
    predicted: np.ndarray,
    days: pd.Series,
    *,
    seed: int,
    repeats: int = 2_000,
) -> dict[str, Any]:
    """Percentile intervals for held-out scores by resampling whole local days."""
    valid = observed.notna() & np.isfinite(predicted) & days.notna()
    actual = observed.loc[valid].to_numpy(dtype=float)
    estimate = np.asarray(predicted, dtype=float)[valid.to_numpy()]
    block_labels = days.loc[valid].astype(str).to_numpy()
    if len(actual) < 2 or len(np.unique(block_labels)) < 2:
        return {"status": "not_estimated", "reason": "Fewer than two held-out healthy local-day blocks."}
    error = estimate - actual
    grouped = pd.DataFrame({
        "day": block_labels,
        "n": 1,
        "absolute_error": np.abs(error),
        "signed_error": error,
        "squared_error": error**2,
        "observed": actual,
    }).groupby("day", sort=True).sum(numeric_only=True)
    totals = grouped[["n", "absolute_error", "signed_error", "squared_error", "observed"]].to_numpy(dtype=float)
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(totals), size=(repeats, len(totals)))
    sampled = totals[draws].sum(axis=1)
    count = sampled[:, 0]
    mae = sampled[:, 1] / count
    bias = sampled[:, 2] / count
    nmae = sampled[:, 1] / sampled[:, 4]
    rmse = np.sqrt(sampled[:, 3] / count)
    def interval(values: np.ndarray) -> list[float]:
        return [float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))]
    return {
        "status": "estimated",
        "method": "2,000 percentile bootstrap replicates resampling whole held-out local calendar days; raw bins are not resampled independently.",
        "independent_blocks": int(len(totals)),
        "block_unit": "local calendar day",
        "seed": int(seed),
        "intervals_95pct": {
            "mae_w": interval(mae),
            "nmae": interval(nmae),
            "bias_w": interval(bias),
            "rmse_w": interval(rmse),
        },
        "limitations": "Day blocks reduce within-day dependence but adjacent days may remain serially dependent; intervals are exploratory and are not population guarantees.",
    }


def fit_and_compare(bins: pd.DataFrame) -> dict[str, Any]:
    """Fit only on healthy training days, select using healthy validation days."""
    splits, split_meta = chronological_splits(bins)
    training = splits["train"].query("healthy and daylight and paired_valid").copy()
    validation = splits["validation"].query("healthy and daylight and paired_valid").copy()
    test = splits["test"].query("healthy and daylight and paired_valid").copy()
    if len(training) < 100 or len(validation) < 30:
        raise ValueError(f"Insufficient healthy calibration bins: train={len(training)}, validation={len(validation)}")

    calibrated_linear = _fit_linear(training, "calibrated_linear")
    candidates: dict[str, dict[str, Any]] = {"calibrated_linear": calibrated_linear}
    train_residual = _predict(calibrated_linear, training) - training["target_power_w"].to_numpy(dtype=float)
    residual_median = float(np.median(train_residual))
    residual_mad = float(np.median(np.abs(train_residual - residual_median)))
    robust_scale = 1.4826 * residual_mad
    robust_outlier_fraction = float(np.mean(np.abs(train_residual - residual_median) > 4 * robust_scale)) if robust_scale > 0 else 0.0
    huber_appropriate = len(training) >= 500 and robust_outlier_fraction >= 0.01
    if huber_appropriate:
        candidates["huber_reference"] = _fit_huber(training)
    weather_coverage = float(validation.get("weather_valid", pd.Series(False, index=validation.index)).mean()) if len(validation) else 0.0
    feature_coverage = [f"{name}_coverage" for name in ("GTI", "DTI", "TA")]
    weather_feature_coverage = (
        float(validation[feature_coverage].ge(0.80).all(axis=1).mean())
        if set(feature_coverage).issubset(validation.columns)
        else (float(validation[["GTI", "DTI", "TA"]].notna().all(axis=1).mean()) if {"GTI", "DTI", "TA"}.issubset(validation.columns) else 0.0)
    )
    weather_candidate_evaluated = weather_coverage >= 0.90 and weather_feature_coverage >= 0.90 and len(training) >= 100
    if weather_candidate_evaluated:
        candidates["weather_assisted_linear"] = _fit_weather(training)

    ratios = {
        "capacity_table_arithmetic": CAPACITY_TABLE_TARGET_KWP / CAPACITY_TABLE_REFERENCE_KWP,
        "capacity_paper_prose": CAPACITY_PROSE_TARGET_KWP / CAPACITY_PROSE_REFERENCE_KWP,
    }
    baseline_models = {
        name: {
            "name": name,
            "features": ["reference_power_w"],
            "fixed_capacity_ratio": float(ratio),
            "preprocessing": "Fixed nameplate capacity ratio; no fitting; exact paired reference power.",
        }
        for name, ratio in ratios.items()
    }
    all_models = {**candidates, **baseline_models}
    validation_scores: dict[str, dict[str, float]] = {}
    heldout_scores: dict[str, dict[str, float]] = {}
    heldout_candidate_coverage: dict[str, float] = {}
    heldout_block_uncertainty: dict[str, dict[str, Any]] = {}
    for model_index, (candidate_name, model) in enumerate(all_models.items()):
        v = _model_frame(validation, model)
        t = _model_frame(test, model)
        validation_prediction = _predict(model, v)
        heldout_prediction = _predict(model, t)
        validation_scores[candidate_name] = _score(v["target_power_w"], validation_prediction)
        heldout_scores[candidate_name] = _score(t["target_power_w"], heldout_prediction)
        heldout_candidate_coverage[candidate_name] = float(len(t) / len(test)) if len(test) else 0.0
        heldout_block_uncertainty[candidate_name] = _day_block_bootstrap(
            t["target_power_w"],
            heldout_prediction,
            t["local_day"],
            seed=20261009 + model_index,
        )

    selected_name = "capacity_table_arithmetic"
    selection_comparisons: dict[str, dict[str, Any]] = {}
    for name in ("calibrated_linear", "huber_reference", "weather_assisted_linear"):
        if name in all_models:
            coverage_ok = name != "weather_assisted_linear" or (weather_coverage >= 0.90 and weather_feature_coverage >= 0.90)
            simpler_model = all_models[selected_name]
            candidate_frame = _model_frame(validation, all_models[name])
            simpler_frame = _model_frame(validation, simpler_model)
            common_bins = pd.Index(candidate_frame["bin_start"]).intersection(pd.Index(simpler_frame["bin_start"]))
            candidate_common = candidate_frame.set_index("bin_start").loc[common_bins]
            simpler_common = simpler_frame.set_index("bin_start").loc[common_bins]
            candidate_mae = (
                _score(candidate_common["target_power_w"], _predict(all_models[name], candidate_common))["mae_w"]
                if len(common_bins) else None
            )
            simpler_mae = (
                _score(simpler_common["target_power_w"], _predict(simpler_model, simpler_common))["mae_w"]
                if len(common_bins) else None
            )
            improvement = (
                float(1 - candidate_mae / simpler_mae)
                if candidate_mae is not None and simpler_mae not in (None, 0) else None
            )
            passes = bool(
                coverage_ok
                and candidate_mae is not None
                and simpler_mae is not None
                and np.isfinite(candidate_mae)
                and np.isfinite(simpler_mae)
                and candidate_mae <= simpler_mae * (1 - VALIDATION_IMPROVEMENT_FLOOR)
            )
            selection_comparisons[name] = {
                "compared_with": selected_name,
                "common_validation_bins": int(len(common_bins)),
                "candidate_mae_w": candidate_mae,
                "simpler_candidate_mae_w": simpler_mae,
                "relative_mae_improvement": improvement,
                "minimum_improvement": VALIDATION_IMPROVEMENT_FLOOR,
                "coverage_gate_passed": bool(coverage_ok),
                "selected": passes,
            }
            if passes:
                selected_name = name
    selected_model = all_models[selected_name]
    validation_selected = _model_frame(validation, selected_model)
    val_residual = _predict(selected_model, validation_selected) - validation_selected["target_power_w"].to_numpy(dtype=float)
    val_eval = validation_selected.copy()
    val_eval["residual_w"] = val_residual
    val_eval["hour_block"] = val_eval["bin_start"].dt.floor("1h")
    validation_hourly = val_eval.groupby("hour_block").agg(
        residual_w=("residual_w", "mean"),
        bin_count=("residual_w", "size"),
    )
    validation_hourly = validation_hourly.loc[validation_hourly["bin_count"] >= 6]
    threshold = float(validation_hourly["residual_w"].clip(lower=0).quantile(0.95)) if len(validation_hourly) >= 10 else None
    parameters = {name: _parameters(model) for name, model in all_models.items()}
    return {
        "splits": splits,
        "split_metadata": split_meta,
        "train_healthy_bins": int(len(training)),
        "validation_healthy_bins": int(len(validation)),
        "heldout_healthy_bins": int(len(test)),
        "models": all_models,
        "selected_model_name": selected_name,
        "selected_model": selected_model,
        "model_parameters": parameters,
        "validation_scores": validation_scores,
        "selection_comparisons": selection_comparisons,
        "heldout_healthy_scores": heldout_scores,
        "heldout_candidate_coverage": heldout_candidate_coverage,
        "heldout_healthy_block_bootstrap_95pct": heldout_block_uncertainty,
        "validation_improvement_floor": VALIDATION_IMPROVEMENT_FLOOR,
        "selection_rule": "Start from the fixed Table 1 capacity-ratio baseline. Move in order to calibrated linear, Huber, and weather-assisted linear only when healthy validation MAE improves at least 5% over the current simpler selected candidate. Consider Huber only when at least 500 training bins exist and more than 1% of healthy training OLS residuals exceed four robust MAD scales. Consider weather-assisted linear only with at least 90% validation weather-bin and feature coverage (reference AC power, GTI, DTI, ambient temperature). Held-out scores do not select the model.",
        "weather_candidate_evaluated": weather_candidate_evaluated,
        "robust_outlier_fraction_train": robust_outlier_fraction,
        "huber_appropriate": huber_appropriate,
        "validation_weather_bin_coverage": weather_coverage,
        "validation_weather_feature_coverage": weather_feature_coverage,
        "capacity_ratios": ratios,
        "detection_threshold_w": threshold,
        "threshold_method": "95th percentile of positive hourly mean residual on nonoverlapping healthy validation hours with at least six 5-minute bins; fixed before held-out evaluation.",
    }


def find_fault_episodes(target: pd.DataFrame, *, gap_seconds: float = EPISODE_GAP_SECONDS) -> list[dict[str, Any]]:
    """Group nonzero-label runs into intervention episodes, preserving zero-label pauses."""
    fault = target.dropna(subset=["timestamp"]).loc[target["fault_label"].fillna(0).gt(0)].copy()
    fault = fault.sort_values("timestamp", kind="stable")
    if fault.empty:
        return []
    fault["gap_s"] = fault["timestamp"].diff().dt.total_seconds()
    fault["group"] = fault["gap_s"].gt(gap_seconds).cumsum()
    episodes = []
    for group_id, rows in fault.groupby("group", sort=True):
        labels = Counter(canonical_fault_label(x) for x in rows["fault_label"].dropna().tolist())
        start = rows["timestamp"].iloc[0]
        end = rows["timestamp"].iloc[-1]
        episodes.append({
            "group_id": int(group_id),
            "start": start,
            "end": end,
            "duration_seconds": float((end - start).total_seconds()),
            "labeled_sample_count": int(len(rows)),
            "label_counts": {f"{key:g}": int(value) for key, value in sorted(labels.items())},
            "labels": [f"{key:g}" for key in sorted(labels)],
            "label_descriptions": [LABEL_DESCRIPTIONS.get(key, "Unmapped numeric label") for key in sorted(labels)],
        })
    return episodes


def _trapezoid_seconds(values: np.ndarray, time_seconds: np.ndarray) -> float:
    if len(values) < 2:
        return 0.0
    return float(np.sum((values[:-1] + values[1:]) * 0.5 * np.diff(time_seconds)))


def evaluate_fault_episodes(
    target: pd.DataFrame,
    paired: pd.DataFrame,
    model_info: dict[str, Any],
    *,
    evaluation_start_day: str,
    test_start_day: str,
    expected_frequency_seconds: float,
    weather_bins: pd.DataFrame | None = None,
    gap_seconds: float = EPISODE_GAP_SECONDS,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Evaluate only complete episodes in the held-out period using elapsed-time integration."""
    evaluation_day = pd.Timestamp(evaluation_start_day).tz_localize("Indian/Reunion")
    split_day = pd.Timestamp(test_start_day).tz_localize("Indian/Reunion")
    episodes = find_fault_episodes(target, gap_seconds=gap_seconds)
    model = model_info["selected_model"]
    paired_fault = paired.loc[paired["fault_label"].fillna(0).gt(0)].copy()
    if weather_bins is not None and "GTI" in model["features"]:
        paired_fault["bin_start"] = paired_fault["timestamp"].dt.floor(f"{BIN_MINUTES}min")
        paired_fault = paired_fault.merge(weather_bins, on="bin_start", how="left", validate="many_to_one")
    paired_fault = _model_frame(paired_fault, model)
    paired_fault["expected_power_w"] = _predict(model, paired_fault)
    paired_fault["signed_shortfall_w"] = paired_fault["expected_power_w"] - paired_fault["target_power_w"]
    evaluated: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    max_dt = MAX_INTEGRATION_GAP_MULTIPLE * expected_frequency_seconds
    for episode in episodes:
        if episode["start"] < evaluation_day:
            exclusions.append({**episode, "reason": "Episode begins before the frozen model's post-training evaluation window; excluded from the primary post-training estimate."})
            continue
        rows = paired_fault.loc[paired_fault["timestamp"].between(episode["start"], episode["end"], inclusive="both")].copy()
        rows = rows.sort_values("timestamp", kind="stable").reset_index(drop=True)
        target_count = episode["labeled_sample_count"]
        paired_count = int(len(rows))
        if paired_count < 2:
            exclusions.append({**episode, "reason": "Fewer than two exact paired shading samples."})
            continue
        times = rows["timestamp"].astype("int64").to_numpy(dtype=np.float64) / 1e9
        dt = np.diff(times)
        adjacent_labeled = rows["fault_label"].to_numpy(dtype=float)[:-1].__gt__(0) & rows["fault_label"].to_numpy(dtype=float)[1:].__gt__(0)
        within_episode_gap = (dt > 0) & (dt <= gap_seconds)
        residual = rows["signed_shortfall_w"].to_numpy(dtype=float)
        expected = rows["expected_power_w"].to_numpy(dtype=float)
        finite_interval = np.isfinite(residual[:-1]) & np.isfinite(residual[1:]) & np.isfinite(expected[:-1]) & np.isfinite(expected[1:])
        valid_interval = adjacent_labeled & within_episode_gap & (dt <= max_dt) & finite_interval
        evaluated_seconds = float(np.sum(dt[adjacent_labeled & within_episode_gap]))
        valid_seconds = float(np.sum(dt[valid_interval]))
        start_ids = np.flatnonzero(valid_interval)
        signed_ws = 0.0
        positive_ws = 0.0
        expected_ws = 0.0
        for idx in start_ids:
            seconds = dt[idx]
            signed_ws += 0.5 * (residual[idx] + residual[idx + 1]) * seconds
            positive_ws += 0.5 * (max(residual[idx], 0.0) + max(residual[idx + 1], 0.0)) * seconds
            expected_ws += 0.5 * (rows["expected_power_w"].iloc[idx] + rows["expected_power_w"].iloc[idx + 1]) * seconds
        confidence = valid_seconds / evaluated_seconds if evaluated_seconds > 0 else 0.0
        record = {
            **episode,
            "evaluation_period": "heldout_test" if episode["start"] >= split_day else "validation_unseen_labels",
            "label_use": "Fault labels in this interval were not used for fitting, model selection, or threshold selection.",
            "paired_sample_count": paired_count,
            "sample_coverage": float(paired_count / target_count) if target_count else 0.0,
            "labeled_elapsed_seconds": evaluated_seconds,
            "integrated_elapsed_seconds": valid_seconds,
            "interval_coverage": float(confidence),
            "eligible_labeled_interval_count": int(np.count_nonzero(adjacent_labeled & within_episode_gap)),
            "valid_interval_count": int(len(start_ids)),
            "signed_energy_deviation_kwh": float(signed_ws / 3_600_000.0),
            "positive_only_shortfall_kwh": float(positive_ws / 3_600_000.0),
            "expected_energy_kwh": float(expected_ws / 3_600_000.0),
            "mean_signed_shortfall_w": float(signed_ws / valid_seconds) if valid_seconds else None,
            "mean_positive_only_shortfall_w": float(positive_ws / valid_seconds) if valid_seconds else None,
            "effect_fraction": float(positive_ws / expected_ws) if expected_ws > 0 else None,
            "integration_method": "Trapezoidal power integration over actual UTC seconds; only adjacent fault-labelled exact pairs; intervals longer than three nominal sample periods are excluded; no interpolation over gaps.",
        }
        if record["sample_coverage"] < MIN_COVERAGE or record["interval_coverage"] < MIN_COVERAGE:
            exclusions.append({**episode, "reason": "Episode retained for audit but not included in pooled estimate because exact-pair or elapsed-time coverage is below the predeclared 80% minimum."})
        else:
            evaluated.append(record)
    return evaluated, exclusions


def _reference_stability(healthy_training: pd.DataFrame, healthy_test: pd.DataFrame) -> dict[str, Any]:
    combined = pd.concat([healthy_training, healthy_test], ignore_index=True)
    combined = combined.loc[combined["reference_power_w"].ge(DAYLIGHT_REFERENCE_MIN_W)].copy()
    combined["normalized_ratio"] = (
        combined["target_power_w"] / CAPACITY_TABLE_TARGET_KWP
    ) / (combined["reference_power_w"] / CAPACITY_TABLE_REFERENCE_KWP)
    combined["month"] = combined["bin_start"].dt.tz_convert("Indian/Reunion").dt.strftime("%Y-%m")
    monthly = combined.groupby("month")["normalized_ratio"].median().dropna()
    ratio_span = float((monthly.max() - monthly.min()) / monthly.median()) if len(monthly) >= 2 and monthly.median() else None
    train_ratio = (healthy_training["target_power_w"] / CAPACITY_TABLE_TARGET_KWP) / (healthy_training["reference_power_w"] / CAPACITY_TABLE_REFERENCE_KWP)
    test_ratio = (healthy_test["target_power_w"] / CAPACITY_TABLE_TARGET_KWP) / (healthy_test["reference_power_w"] / CAPACITY_TABLE_REFERENCE_KWP)
    train_med = float(train_ratio.loc[healthy_training["daylight"]].median()) if len(train_ratio) else None
    test_med = float(test_ratio.loc[healthy_test["daylight"]].median()) if len(test_ratio) else None
    stable = ratio_span is not None and ratio_span <= REFERENCE_MONTHLY_RELATIVE_RANGE_LIMIT
    return {
        "monthly_normalized_ratio_medians": {str(k): float(v) for k, v in monthly.items()},
        "monthly_relative_range": ratio_span,
        "relative_range_limit": REFERENCE_MONTHLY_RELATIVE_RANGE_LIMIT,
        "training_median_ratio": train_med,
        "heldout_median_ratio": test_med,
        "status": "stable_by_predeclared_screen" if stable else "unstable_or_insufficient_months",
        "screen": "Across healthy daylight bins, monthly medians of the capacity-normalized target/reference ratio; stable when relative max-minus-min range is at most 15%. This is a screening rule, not proof of reference-system health.",
    }


def _heldout_hourly_placebo(model_info: dict[str, Any]) -> dict[str, Any]:
    test = model_info["splits"]["test"].query("healthy and daylight and paired_valid").copy()
    validation = model_info["splits"]["validation"].query("healthy and daylight and paired_valid").copy()
    model = model_info["selected_model"]
    test = _model_frame(test, model)
    validation = _model_frame(validation, model)
    if len(test) == 0 or model_info["detection_threshold_w"] is None:
        return {"status": "not_evaluated", "reason": "Insufficient held-out healthy hours or validation threshold could not be estimated."}
    test["residual_w"] = _predict(model, test) - test["target_power_w"].to_numpy(dtype=float)
    test["hour_block"] = test["bin_start"].dt.floor("1h")
    hourly = test.groupby("hour_block").agg(residual_w=("residual_w", "mean"), bin_count=("residual_w", "size"))
    hourly = hourly.loc[hourly["bin_count"] >= 6]
    threshold = model_info["detection_threshold_w"]
    flagged = int(hourly["residual_w"].gt(threshold).sum())
    return {
        "status": "evaluated" if len(hourly) else "not_evaluated",
        "population": "held-out healthy nonoverlapping 1-hour blocks; at least six complete 5-minute daylight bins",
        "threshold_w": float(threshold),
        "valid_placebo_blocks": int(len(hourly)),
        "false_shortfall_blocks": flagged,
        "false_shortfall_rate": float(flagged / len(hourly)) if len(hourly) else None,
        "mean_signed_residual_w": float(hourly["residual_w"].mean()) if len(hourly) else None,
        "limitations": "Placebo blocks are serially dependent and are not independent Bernoulli trials; the rate is descriptive and uses a threshold fixed on healthy validation blocks.",
    }


def _missingness_sensitivity(
    test: pd.DataFrame,
    model_info: dict[str, Any],
    *,
    repeats: int = 20,
    seed: int = 20261009,
) -> dict[str, Any]:
    selected_model = model_info["selected_model"]
    valid = _model_frame(test.query("healthy and daylight and paired_valid"), selected_model)
    valid = valid.sort_values("bin_start", kind="stable").reset_index(drop=True)
    if len(valid) < 100:
        return {"status": "not_evaluated", "reason": "Too few held-out healthy bins for block-missingness sensitivity."}
    rng = np.random.default_rng(seed)
    base_n = len(valid)
    timestamps = valid["bin_start"].astype("int64").to_numpy(dtype=np.int64)
    five_minutes_ns = int(pd.Timedelta(minutes=BIN_MINUTES).value)
    block_starts = [
        start for start in range(max(0, base_n - 5))
        if np.all(np.diff(timestamps[start:start + 6]) == five_minutes_ns)
    ]
    if not block_starts:
        return {"status": "not_evaluated", "reason": "No contiguous six-bin held-out healthy blocks are available."}
    results = []
    for fraction in (0.10, 0.25):
        capacity_maes = []
        selected_maes = []
        coverages = []
        for _ in range(repeats):
            keep = np.ones(base_n, dtype=bool)
            target_missing = int(round(fraction * base_n))
            removed = 0
            # Drop only six adjacent 5-minute bins with no intervening timestamp gap.
            attempts = 0
            while removed < target_missing and attempts < 20 * base_n:
                start = int(rng.choice(block_starts))
                end = start + 6
                before = int((~keep).sum())
                keep[start:end] = False
                removed += int((~keep).sum()) - before
                attempts += 1
            subset = valid.iloc[keep]
            coverages.append(float(len(subset) / base_n))
            ratio = CAPACITY_TABLE_TARGET_KWP / CAPACITY_TABLE_REFERENCE_KWP
            capacity_pred = _capacity_prediction(subset["reference_power_w"], ratio)
            capacity_maes.append(float(mean_absolute_error(subset["target_power_w"], capacity_pred)) if len(subset) else float("nan"))
            selected_pred = _predict(selected_model, subset)
            selected_maes.append(float(mean_absolute_error(subset["target_power_w"], selected_pred)) if len(subset) else float("nan"))
        ratio = CAPACITY_TABLE_TARGET_KWP / CAPACITY_TABLE_REFERENCE_KWP
        complete_capacity_mae = float(mean_absolute_error(valid["target_power_w"], _capacity_prediction(valid["reference_power_w"], ratio)))
        complete_selected_mae = float(mean_absolute_error(valid["target_power_w"], _predict(selected_model, valid)))
        results.append({
            "synthetic_missing_fraction_requested": fraction,
            "repeats": repeats,
            "mean_retained_coverage": float(np.mean(coverages)),
            "complete_capacity_baseline_mae_w": complete_capacity_mae,
            "mean_capacity_baseline_mae_w": float(np.nanmean(capacity_maes)),
            "capacity_baseline_change_from_complete_mae_w": float(np.nanmean(capacity_maes) - complete_capacity_mae),
            "complete_selected_model_mae_w": complete_selected_mae,
            "mean_selected_model_mae_w": float(np.nanmean(selected_maes)),
            "selected_model_change_from_complete_mae_w": float(np.nanmean(selected_maes) - complete_selected_mae),
        })
    return {
        "status": "evaluated",
        "synthetic": True,
        "method": "Deterministic-seed simulation deleting six consecutive observed 5-minute held-out healthy bins only where timestamps are exactly 300 seconds apart; the capacity-normalized baseline and frozen selected model are rescored on identical retained bins without refitting.",
        "findings": results,
        "note": "This sensitivity experiment is synthetic and does not represent the measured missingness process.",
    }


def summarize_analysis(
    bins: pd.DataFrame,
    target: pd.DataFrame,
    paired: pd.DataFrame,
    model_info: dict[str, Any],
    episodes: list[dict[str, Any]],
    exclusions: list[dict[str, Any]],
    *,
    expected_frequency_seconds: float,
) -> dict[str, Any]:
    splits = model_info["splits"]
    healthy_train = splits["train"].query("healthy and daylight and paired_valid").copy()
    healthy_test = splits["test"].query("healthy and daylight and paired_valid").copy()
    stability = _reference_stability(healthy_train, healthy_test)
    placebo = _heldout_hourly_placebo(model_info)
    missingness = _missingness_sensitivity(splits["test"], model_info)
    total_labeled = int(target["fault_label"].fillna(0).gt(0).sum())
    total_paired_fault = int(paired["fault_label"].fillna(0).gt(0).sum())
    selected = model_info["selected_model"]
    selected_test = _model_frame(healthy_test, selected)
    health_days = int(selected_test["local_day"].nunique())
    selected_coverage = float(len(selected_test) / len(healthy_test)) if len(healthy_test) else 0.0
    score = model_info["heldout_healthy_scores"].get(model_info["selected_model_name"], {})
    target_mean = float(selected_test["target_power_w"].mean()) if len(selected_test) else None
    calibration_valid = (
        health_days >= MIN_TEST_HEALTHY_DAYS
        and selected_coverage >= MIN_COVERAGE
        and score.get("nmae") is not None
        and score.get("nmae", np.inf) <= MAX_HELDOUT_NMAE
        and target_mean is not None
        and score.get("bias_w") is not None
        and abs(score.get("bias_w", np.inf)) <= MAX_HELDOUT_RELATIVE_BIAS * target_mean
    )
    valid_episodes = [ep for ep in episodes if ep.get("interval_coverage", 0) >= MIN_COVERAGE]
    heldout_episodes = [ep for ep in valid_episodes if ep.get("evaluation_period") == "heldout_test"]
    # The uncertainty unit is the separated experimental episode, never a raw sample.
    if len(valid_episodes) >= 2:
        rng = np.random.default_rng(20261009)
        values = np.array([ep["positive_only_shortfall_kwh"] for ep in valid_episodes], dtype=float)
        n = len(values)
        bootstrap_totals = np.empty(5000, dtype=float)
        for i in range(len(bootstrap_totals)):
            bootstrap_totals[i] = rng.choice(values, size=n, replace=True).sum()
        ci = [float(np.quantile(bootstrap_totals, 0.025)), float(np.quantile(bootstrap_totals, 0.975))]
    else:
        ci = None
    if len(heldout_episodes) >= 2:
        rng_test = np.random.default_rng(20261010)
        test_values = np.array([ep["positive_only_shortfall_kwh"] for ep in heldout_episodes], dtype=float)
        test_bootstrap = np.empty(5000, dtype=float)
        for i in range(len(test_bootstrap)):
            test_bootstrap[i] = rng_test.choice(test_values, size=len(test_values), replace=True).sum()
        heldout_ci = [float(np.quantile(test_bootstrap, 0.025)), float(np.quantile(test_bootstrap, 0.975))]
    else:
        heldout_ci = None
    if valid_episodes:
        signed_energy = float(sum(ep["signed_energy_deviation_kwh"] for ep in valid_episodes))
        positive_energy = float(sum(ep["positive_only_shortfall_kwh"] for ep in valid_episodes))
        expected_energy = float(sum(ep["expected_energy_kwh"] for ep in valid_episodes))
        valid_intervals = int(sum(ep["valid_interval_count"] for ep in valid_episodes))
        total_intervals = int(sum(ep["eligible_labeled_interval_count"] for ep in valid_episodes))
        valid_elapsed_seconds = float(sum(ep["integrated_elapsed_seconds"] for ep in valid_episodes))
        labeled_elapsed_seconds = float(sum(ep["labeled_elapsed_seconds"] for ep in valid_episodes))
        event_coverage = float(np.average([ep["interval_coverage"] for ep in valid_episodes], weights=[max(ep["labeled_elapsed_seconds"], 1) for ep in valid_episodes]))
        mean_positive_episode_w = float(np.mean([ep["mean_positive_only_shortfall_w"] for ep in valid_episodes if ep["mean_positive_only_shortfall_w"] is not None]))
    else:
        signed_energy = positive_energy = expected_energy = None
        valid_intervals = 0
        total_intervals = 0
        valid_elapsed_seconds = 0.0
        labeled_elapsed_seconds = 0.0
        event_coverage = 0.0
        mean_positive_episode_w = None

    threshold = model_info["detection_threshold_w"]
    if heldout_episodes:
        heldout_event_coverage = float(np.average(
            [ep["interval_coverage"] for ep in heldout_episodes],
            weights=[max(ep["labeled_elapsed_seconds"], 1) for ep in heldout_episodes],
        ))
        heldout_mean_positive_episode_w = float(np.mean([
            ep["mean_positive_only_shortfall_w"] for ep in heldout_episodes
            if ep["mean_positive_only_shortfall_w"] is not None
        ]))
        heldout_signed_energy = float(sum(ep["signed_energy_deviation_kwh"] for ep in heldout_episodes))
        heldout_positive_energy = float(sum(ep["positive_only_shortfall_kwh"] for ep in heldout_episodes))
        heldout_expected_energy = float(sum(ep["expected_energy_kwh"] for ep in heldout_episodes))
    else:
        heldout_event_coverage = 0.0
        heldout_mean_positive_episode_w = None
        heldout_signed_energy = heldout_positive_energy = heldout_expected_energy = None
    reference_reliable = stability["status"] == "stable_by_predeclared_screen"
    fallback = None
    if not reference_reliable:
        if model_info["selected_model_name"] == "weather_assisted_linear" and model_info["weather_candidate_evaluated"]:
            fallback = "weather_assisted_linear"
        else:
            fallback = "capacity_ratio_only; insufficient as a weather-adjusted reference"
    if health_days < MIN_TEST_HEALTHY_DAYS or not calibration_valid:
        state = "insufficient_evidence"
    elif not reference_reliable and fallback != "weather_assisted_linear":
        state = "insufficient_evidence"
    elif not heldout_episodes or heldout_event_coverage < MIN_COVERAGE:
        state = "insufficient_evidence"
    elif (
        len(heldout_episodes) >= MIN_EPISODES_FOR_INFERENCE
        and heldout_ci is not None
        and threshold is not None
        and heldout_ci[0] > 0
        and heldout_mean_positive_episode_w is not None
        and heldout_mean_positive_episode_w > threshold
    ):
        state = "supported_change"
    else:
        state = "inconclusive"
    if state == "supported_change":
        reasons = [
            "The held-out shaded-episode positive-only shortfall exceeds the healthy-validation detection floor and the episode-cluster bootstrap interval excludes zero.",
            "The selected reference model passes the predeclared held-out healthy calibration and coverage screens.",
            "This supports a measured output deviation during documented experimental intervals; it does not establish cause or commercial recovery.",
        ]
    elif state == "inconclusive":
        reasons = [
            "Data quality permits an estimate, but the predeclared independent-episode, detection-floor, or uncertainty criterion for supported_change was not met.",
            "The estimate describes measured shortfall relative to a healthy-period reference and is not causal attribution.",
        ]
    else:
        reasons = []
        if health_days < MIN_TEST_HEALTHY_DAYS:
            reasons.append(f"Only {health_days} held-out healthy daylight days are available; at least {MIN_TEST_HEALTHY_DAYS} are required.")
        if not calibration_valid:
            reasons.append(
                f"Held-out healthy calibration failed a predeclared coverage/nMAE/bias/day-count check: selected-model coverage={selected_coverage:.3%}, nMAE={score.get('nmae')}, signed bias W={score.get('bias_w')}, mean target W={target_mean}."
            )
        if not reference_reliable and fallback != "weather_assisted_linear":
            reasons.append("The potential reference failed the predeclared monthly stability screen and no valid weather-assisted fallback was selected.")
        if not episodes:
            reasons.append(
                f"No evaluable post-training labelled shading episode is present; {len(exclusions)} grouped episode(s) were excluded before the frozen evaluation window."
            )
        elif not heldout_episodes:
            reasons.append(
                f"The final held-out period contains no evaluable shading episodes; {len(episodes)} post-training episode(s) are reported descriptively, including exploratory validation-period events."
            )
        elif heldout_event_coverage < MIN_COVERAGE:
            reasons.append(f"Final held-out shading elapsed-time coverage is {heldout_event_coverage:.3%}, below the {MIN_COVERAGE:.0%} minimum.")
        reasons.extend([
            "Post-training validation-period episodes, when present, do not establish held-out shading performance.",
            f"Fallback considered: {fallback or 'none'}.",
        ])
    return {
        "analysis_version": ANALYSIS_VERSION,
        "decision": {
            "state": state,
            "reasons": reasons,
            "rules_version": "solarloss-decision-rules-0.1.0",
            "predeclared_thresholds": {
                "min_test_healthy_days": MIN_TEST_HEALTHY_DAYS,
                "minimum_coverage": MIN_COVERAGE,
                "max_heldout_nmae": MAX_HELDOUT_NMAE,
                "max_heldout_relative_bias": MAX_HELDOUT_RELATIVE_BIAS,
                "min_independent_episodes": MIN_EPISODES_FOR_INFERENCE,
                "heldout_validation_detection_floor_w": threshold,
            },
        },
        "split_metadata": model_info["split_metadata"],
        "selected_model": model_info["model_parameters"][model_info["selected_model_name"]],
        "model_selection": {
            "selected": model_info["selected_model_name"],
            "candidate_model_parameters": model_info["model_parameters"],
            "validation_scores": model_info["validation_scores"],
            "progressive_selection_comparisons": model_info["selection_comparisons"],
            "heldout_healthy_scores": model_info["heldout_healthy_scores"],
            "heldout_candidate_coverage": model_info["heldout_candidate_coverage"],
            "heldout_healthy_block_bootstrap_95pct": model_info["heldout_healthy_block_bootstrap_95pct"],
            "selection_rule": model_info["selection_rule"],
            "train_healthy_bins": model_info["train_healthy_bins"],
            "validation_healthy_bins": model_info["validation_healthy_bins"],
            "heldout_healthy_bins": model_info["heldout_healthy_bins"],
            "weather_candidate_evaluated": model_info["weather_candidate_evaluated"],
            "robust_outlier_fraction_train": model_info["robust_outlier_fraction_train"],
            "huber_appropriate": model_info["huber_appropriate"],
            "validation_weather_bin_coverage": model_info["validation_weather_bin_coverage"],
            "validation_weather_feature_coverage": model_info["validation_weather_feature_coverage"],
        },
        "heldout_healthy": {
            "days": health_days,
            "selected_model_coverage": selected_coverage,
            "score": score,
            "calibration_valid": bool(calibration_valid),
            "normalized_error_denominator": "mean held-out healthy target AC power (W)",
        },
        "shortfall": {
            "signed_energy_deviation_kwh": signed_energy,
            "positive_only_shortfall_kwh": positive_energy,
            "expected_energy_kwh": expected_energy,
            "positive_shortfall_fraction": positive_energy / expected_energy if expected_energy and positive_energy is not None else None,
            "mean_positive_shortfall_per_episode_w": mean_positive_episode_w,
            "episode_cluster_bootstrap_95pct_interval_kwh": ci,
            "independent_episode_count": int(len(valid_episodes)),
            "uncertainty_method": "Percentile bootstrap resampling separated intervention episodes (5,000 replicates; fixed seed 20261009); raw rows are not treated as independent.",
            "uncertainty_exploratory": bool(len(valid_episodes) < 10),
            "uncertainty_not_estimated_reason": "Fewer than two valid, separate episodes." if ci is None else None,
            "coverage": event_coverage,
            "valid_elapsed_seconds": valid_elapsed_seconds,
            "labelled_elapsed_seconds": labeled_elapsed_seconds,
            "valid_interval_count": valid_intervals,
            "total_interval_count": total_intervals,
            "total_labelled_sample_count": int(sum(ep["labeled_sample_count"] for ep in valid_episodes)),
            "energy_method": "Trapezoidal power integration over observed elapsed seconds; no interpolation across gaps; only fault-labelled adjacent exact pairs; signed and positive-only integrals reported separately.",
        },
        "heldout_test_shading": {
            "evaluation_period": "final chronological held-out test period only",
            "episode_count": int(len(heldout_episodes)),
            "coverage": heldout_event_coverage,
            "signed_energy_deviation_kwh": heldout_signed_energy,
            "positive_only_shortfall_kwh": heldout_positive_energy,
            "expected_energy_kwh": heldout_expected_energy,
            "mean_positive_shortfall_per_episode_w": heldout_mean_positive_episode_w,
            "episode_cluster_bootstrap_95pct_interval_kwh": heldout_ci,
            "independent_episode_count": int(len(heldout_episodes)),
        },
        "episodes": episodes,
        "episode_exclusions": exclusions,
        "reference_stability": stability,
        "fallback": fallback,
        "placebo": placebo,
        "missingness_sensitivity": missingness,
        "sample_audit": {
            "fault_labelled_target_samples": total_labeled,
            "exact_paired_fault_samples": total_paired_fault,
            "nominal_sampling_interval_seconds": float(expected_frequency_seconds),
            "episode_gap_seconds": float(EPISODE_GAP_SECONDS),
        },
    }
