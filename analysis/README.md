# SolarLoss scientific analysis

This directory contains a reproducible audit and evaluation pipeline for the pinned La Réunion rooftop PV dataset. The notebook is intended for Google Colab and local Jupyter. It downloads the two electrical streams first, verifies the pinned Zenodo v2 byte counts and MD5 checksums, and downloads weather only when enabled.

## Colab

1. Download and extract the accompanying `solarloss_analysis_colab.zip` bundle into Colab or Google Drive.
2. Open `analysis/notebooks/solarloss_research.ipynb`.
3. Run the cells in order. The notebook installs the exact versions from `requirements.txt`, mounts Drive when used in Colab, and defaults to persistent storage under `MyDrive/solarloss_research`.
4. The weather CSV is 1.54 GB. Set `INCLUDE_WEATHER = False` to skip it and evaluate the electrical reference models only. If running both files and weather, choose a high-RAM Colab runtime; weather audit and binning are streamed, but the compact electrical modeling tables remain in memory.
5. By default, the notebook keeps raw data and JSON outputs in the persistent Drive folder `/content/drive/MyDrive/solarloss_research/data` and `/content/drive/MyDrive/solarloss_research/results`. Locally, both are under the analysis directory. Set `SOLARLOSS_DATA_DIR` or `SOLARLOSS_RESULTS_DIR` to override either location. Raw downloaded data are excluded from source control.

## Local run

From this directory, install `requirements.txt`, download the two electrical files with `download_file`, optionally download the weather file, then call `audit_and_model(data_dir, include_weather=..., produced_at=...)` and `export_results(...)`. The notebook contains the full executable sequence.

Raw CSV audits are chunked. Weather is streamed into five-minute sufficient summaries. Electrical modeling uses only timestamp, fault label, and compact numeric columns from the two exact streams. Full raw files are never embedded in the repository or review JSON.

## Files

- `notebooks/solarloss_research.ipynb`: end-to-end Colab/Jupyter workflow.
- `src/solarloss_research/`: data ingestion, audit, model evaluation, decision rules, and JSON exporters.
- `tests/`: deterministic synthetic unit tests of pipeline mechanics; they are not study results.
- `DATA_PROVENANCE.md`: pinned record, licence, source fields, checksums, and source-document notes.
- `METHODOLOGY.md`: estimand, split, model selection, metrics, uncertainty, and limitations.
- `SCHEMA_FEEDBACK.md`: review of the provisional backend contract and v0.1 compatibility mapping.
- `contracts/review.schema.v0.1.0.json`: unchanged snapshot copied from the backend worker's `rachit/backend-api` branch.
- `results/`: reproducibly generated data-quality, model-comparison, and review JSON artifacts.

See `METHODOLOGY.md` for the predeclared decision gates. An inconclusive or insufficient-evidence result is preserved as such; the chronological evaluation boundary is not moved to capture experimental labels.
