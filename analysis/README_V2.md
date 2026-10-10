# SolarLoss Phase 2 — reproducible CPU evaluation

Read INITIAL_AUDIT_V2.md, EXPERIMENT_PROTOCOL_V2.md and EXECUTIVE_SUMMARY_V2.md first. V1 notebook/results are historical and preserved. The v2 protocol is retrospective and dataset-aware. Do not transfer historical model accuracy to it.

## Local run

Use Python 3.12 and create an environment. Install requirements-v2.txt from this analysis directory. From the repository root:

```text
python -m pip install -r analysis/requirements-v2.txt
python -m pytest analysis/tests -q
```

Set PYTHONPATH to analysis/src using your shell, then run:

```text
python -m solarloss_research.evaluation_v2 --data-dir data/solarloss-7291380 --output-dir analysis/results --protocol analysis/EXPERIMENT_PROTOCOL_V2.md
```

The downloader reuses files only after the pinned published size/MD5 passes. It streams missing files; allow ~1.8 GB disk for source files and several GB memory for electrical frames. Full weather audit is slower than fitting the linear models. No GPU is needed. Raw files are excluded from the integration ZIP and Git. data_quality_report_v2.json records exact MD5 and SHA256 hashes, row counts, offsets, cadence and ranges; runtime_versions_v2.json records the executed runtime. requirements-v2-lock.txt records all installed dependency versions on the execution host; use requirements-v2.txt for cross-platform Colab installation because the local lock includes Windows-specific packages.

`--no-weather` is an executable fallback that downloads/uses just electrical measurements and metadata. It produces its own selection/calibration/evaluation. Use a distinct output directory; never overwrite weather-enabled results or claim weather-model performance from this fallback. The delivered primary experiment includes weather.

## Colab

Open notebooks/solarloss_shading_evaluation_v2.ipynb. Run all cells, upload the complete integration ZIP when prompted, and mount Drive for persistent verified sources. The private GitHub repository is not assumed accessible from Colab. Environment overrides SOLARLOSS_ANALYSIS_DIR, SOLARLOSS_DATA_DIR and SOLARLOSS_RESULTS_DIR support local execution. The notebook installs pinned direct dependencies, invokes the same evaluation source, runs scientific tests and reads generated numbers/charts.

The notebook's full analysis cells have been executed locally on real source measurements. Google Drive mounting and interactive ZIP upload are environment-specific branches; they are not claimed as locally executed Colab actions. See results/execution_verification_v2.json for verified execution status. No remote Google Colab service run is claimed.

## Outputs and scope

shading_evaluation_v2.json contains event detection, calibrated healthy alarms, latency, confusion units, signed/positive energy, matched healthy-model-error comparisons, electrical measurements and verdicts. model_comparison_v2.json contains all baseline scores on selection/later healthy and common weather populations. frozen_parameters_v2.json precedes protected scoring and records the protocol hash and thresholds. CSV files supply reproducible chart numbers. charts/ uses those computed quantities. example_cases_v2.json includes healthy, real shading and measured missing-data examples.

Do not equate positive-only deviation with causal loss, recovered generation or financial savings. Va is PV operating voltage; Vg is grid voltage. No fault classifier or maintenance interventions are validated. The proposed v0.2 schema is pending owner approval. Only analysis/ changes are integration-ready; backend/frontend/infra are intentionally outside this package.

Independent real-result checks: run python analysis/tools/verify_results_v2.py from the repository root after evaluation.
