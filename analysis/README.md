# Scientific analysis

This directory contains the SolarLoss research code and the reproducible v2 retrospective shading evaluation. Start with the [executive summary](EXECUTIVE_SUMMARY_V2.md), then read the [frozen protocol](EXPERIMENT_PROTOCOL_V2.md), [full report](EXPERIMENT_REPORT_V2.md), and [dataset provenance](DATA_PROVENANCE.md).

## Reproduce the v2 study

Use Python 3.12. The pinned source data are downloaded from the immutable [Zenodo v2 record](https://zenodo.org/records/7291380), verified against published file sizes and MD5 values, and kept outside Git. A full weather-enabled rerun needs about 1.8 GB of source data and several GB of memory.

From the repository root in PowerShell:

```powershell
python -m pip install -r analysis/requirements-v2.txt
python -m pip install jupyterlab
python -m pytest analysis/tests -q
python analysis/tools/verify_results_v2.py
jupyter lab analysis/notebooks/solarloss_shading_evaluation_v2.ipynb
```

For the full command-line run, set the module path and use a separate output directory for each protocol variant:

```powershell
$env:PYTHONPATH = (Resolve-Path analysis/src).Path
python -m solarloss_research.evaluation_v2 `
  --data-dir data/solarloss-7291380 `
  --output-dir analysis/results `
  --protocol analysis/EXPERIMENT_PROTOCOL_V2.md
```

`--no-weather` is a different evaluation and must use a distinct output directory. Do not use it to describe the weather-enabled published result. The verifier checks selected arithmetic and code/protocol identities from committed outputs; it does not download the dataset or rerun the experiment. The executed notebook records a local CPU run; Google Colab's Drive and upload branches were not executed.

## Navigate the research files

- [Evaluation source](src/solarloss_research/), [unit tests](tests/), [scientific requirements](requirements-v2.txt), and [executable v2 notebook](notebooks/solarloss_shading_evaluation_v2.ipynb).
- [Primary v2 result JSONs and tables](results/) include frozen parameters, model comparison, event-level evaluation, examples, and measured demo samples. The development-only Vite preview reads `example_cases_v2.json`, `shading_evaluation_v2.json`, and `demo_measured_series_v2.csv`.
- [Revision log](REVISION_LOG_V2.md), [electrical evidence matrix](ELECTRICAL_EVIDENCE_MATRIX.md), [proposed investigation guidance](INVESTIGATION_GUIDANCE_PROPOSAL.md), and [proposed schema handoff](SCHEMA_FEEDBACK_V2.md) provide detailed context and limits.
- [Curated file map](CURATION_MAP.md) classifies every analysis artifact, records checked dependencies, and explains the generated-output release assessment.
- The original v1 notebook, implementation, tests, requirements, and outputs remain available at their existing paths. Older setup, audit, and comparison notes were removed from the current tree after their dependencies were checked; earlier commits retain those versions.

## Phase 3 provisional handoff

The Phase 3 exporter creates a source-reconciled shading review, a zero-labelled calibration example, and a separate explicit record for the long data gap. Read the [scientific contract decisions](SCIENTIFIC_CONTRACT_DECISIONS_V3.md) and [exporter integration handoff](EXPORTER_INTEGRATION_HANDOFF_V3.md) before treating a generated review as application-approved. No owner approval is recorded and production continues to serve v0.1.

From the repository root:

    python analysis/tools/export_reviews_v3.py export
    python analysis/tools/export_reviews_v3.py validate
    python backend/validate_artifact.py analysis/results/reviews_v3/review_shading_01.json --experimental-v2 --report-output analysis/results/reviews_v3/preview_shading_01.html
    python backend/validate_artifact.py analysis/results/reviews_v3/review_healthy_20220126_0300.json --experimental-v2 --report-output analysis/results/reviews_v3/preview_healthy_20220126_0300.html

The experimental validation commands render local HTML only. They do not exercise production APIs or storage. The data-gap record intentionally is not submitted to the v0.2 review validator.

The detector work is documented in [error analysis](DETECTOR_ERROR_ANALYSIS_V3.md) and [exploratory comparison](DETECTOR_EXPLORATORY_COMPARISON_V3.md). Its source-backed tables and plots are generated with:

    python analysis/tools/run_detector_diagnostics_v3.py

The new diagnostics are retrospective and exploratory because V2 protected outcomes were inspected. The [degradation research plan](DEGRADATION_RESEARCH_PLAN.md), [technician guidance review](TECHNICIAN_GUIDANCE_REVIEW_V3.md), and [public research layout proposal](PUBLIC_RESEARCH_LAYOUT_PROPOSAL_V3.md) are future-work proposals and do not assert approved causes or an ageing rate.

## Generated output and release-bundle assessment

The 12.9 MB `results/five_minute_evaluation_v2.csv` is read by scientific CI, while `results/demo_measured_series_v2.csv` is read by the Vite research preview. The 539 KB executed notebook and generated result CSVs are candidates for a versioned GitHub Release bundle. They remain tracked until a release asset, checksum-verifying CI download, and local preview access path are available together. See [CURATION_MAP.md](CURATION_MAP.md) for the dependency trace, source revision, and bundle requirements.

No source-code license is selected here. Dataset attribution and its CC BY 4.0 terms are documented in [DATA_PROVENANCE.md](DATA_PROVENANCE.md).
