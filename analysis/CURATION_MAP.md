# Analysis file classification and curation map

Scope: the 57 tracked `analysis/` files present at `main` commit `b978940973ecbae6d516e6d49bc31800e3b7348a`, before this curation. No result values, protocol decisions, or scientific conclusions were changed.

Categories use the user's five classes. A generated artifact can be useful reproducibility material and also qualify for a future release bundle; its primary classification is stated below. Files that include a reviewer name, collaborator branch, or private-repository workflow are additionally flagged under category 5.

## Class 1 — essential implementation, tests, and executable workflow

- `analysis/.gitignore`
- `analysis/src/solarloss_research/__init__.py`
- `analysis/src/solarloss_research/dataset.py`
- `analysis/src/solarloss_research/evaluation_v2.py`
- `analysis/src/solarloss_research/model.py`
- `analysis/src/solarloss_research/pipeline.py`
- `analysis/src/solarloss_research/review.py`
- `analysis/tests/test_evaluation_v2.py`
- `analysis/tests/test_pipeline.py`
- `analysis/tools/verify_results_v2.py`
- `analysis/notebooks/solarloss_research.ipynb` (historical v1 executable notebook)
- `analysis/notebooks/solarloss_shading_evaluation_v2.ipynb` (current executable notebook; also flagged under class 5)
- `analysis/requirements.txt`, `analysis/requirements-v2.txt`, and `analysis/requirements-v2-lock.txt` (the last file records the historical run environment; current installs use the un-locked v2 requirements)

## Class 2 — essential public scientific evidence

- `analysis/DATA_PROVENANCE.md`
- `analysis/EXPERIMENT_PROTOCOL_V2.md`
- `analysis/EXECUTIVE_SUMMARY_V2.md`
- `analysis/EXPERIMENT_REPORT_V2.md`
- `analysis/ELECTRICAL_EVIDENCE_MATRIX.md`
- `analysis/results/data_quality_report.json` (v1 audit) and `analysis/results/data_quality_report_v2.json` (v2 audit)
- `analysis/results/model_comparison_results.json` (v1) and `analysis/results/model_comparison_v2.json` (v2)
- `analysis/results/shading_evaluation_v2.json`
- `analysis/results/frozen_parameters_v2.json`
- `analysis/results/feasibility_v2.json`
- `analysis/results/example_cases_v2.json`
- `analysis/results/episode_metrics_v2.csv`
- `analysis/results/monthly_stability_v2.csv`
- `analysis/results/demo_measured_series_v2.csv` (measured preview inputs; consumed by Vite)
- `analysis/results/independent_verification_v2.json`

These files preserve attribution, the frozen design, primary result summaries, measured examples, and limitations. They are retained in the working tree.

## Class 3 — useful detailed reproducibility material

- `analysis/REVISION_LOG_V2.md`
- `analysis/SCHEMA_FEEDBACK_V2.md` (also flagged under class 5)
- `analysis/INVESTIGATION_GUIDANCE_PROPOSAL.md` (also flagged under class 5)
- `analysis/README.md` (current entry point) and `analysis/CURATION_MAP.md` (this inventory)
- Original `analysis/INITIAL_AUDIT_V2.md` (historical pre-evaluation record; its prior-main version remains accessible in Git history)
- Baseline v1 detailed notes `analysis/METHODOLOGY.md`, `analysis/MODEL_COMPARISON.md`, and `analysis/SCHEMA_FEEDBACK.md` (the last remains as a short pointer because the v1 notebook refers to it)
- `analysis/README_V2.md` (short pointer retained for the v2 notebook's existing reference)
- `analysis/contracts/review.schema.v0.1.0.json`
- `analysis/contracts/review.schema.v0.2.0.proposed.json`
- `analysis/results/execution_verification_v2.json`
- `analysis/results/runtime_versions_v2.json`
- `analysis/results/package_manifest_v2.json` (checksum record for the historical analysis package; its paths are from that package layout)
- `analysis/results/review_la-reunion_healthy-placebo-no-posttraining-shading_0.1.0.json` (historical v1 insufficient-evidence artifact; retain its documented identity limitation)
- `analysis/results/five_minute_evaluation_v2.csv` (large generated evaluation table; required by the verifier and a future release-bundle candidate)
- `analysis/notebooks/solarloss_shading_evaluation_v2.executed.ipynb` (generated execution record and a release-bundle candidate; also flagged under class 5)
- Baseline v1 setup document `analysis/README.md` (now replaced by the canonical index) and original v2 run guide `analysis/README_V2.md` (now a pointer).

The v1 notes describe a distinct historical evaluation and are not current v2 claims. The original content of consolidated notes remains available in earlier commits. The current protocol and report are authoritative for the v2 study.

## Class 4 — generated or presentation material

- `analysis/results/charts/demo_episode.png`
- `analysis/results/charts/electrical_observations.png`
- `analysis/results/charts/event_energy.png`
- `analysis/results/charts/model_comparison.png`
- `analysis/results/charts/timeline.png`

These charts are derived from committed measurements and are referenced by scientific documentation. They remain tracked. The original contents of `analysis/DATA_AUDIT_DELTA_V2.md`, `analysis/METHODOLOGY_V2.md`, and `analysis/MODEL_COMPARISON_V2.md` were repetitive audit/overview material; the original contents of `analysis/METHODOLOGY.md` and `analysis/MODEL_COMPARISON.md` were historical v1 notes. Those five documents were removed from the current tree after their references were checked. The 12.9 MB evaluation CSV and executed notebook are generated too, but are primarily class 3 because CI/reproducibility consumes them.

## Class 5 — potentially sensitive content for owner review

The bounded scan found no credential markers or personal home-directory paths in the tracked analysis files. It did find named reviewer/collaborator context or a private-repository workflow reference in:

- `analysis/INVESTIGATION_GUIDANCE_PROPOSAL.md`
- `analysis/SCHEMA_FEEDBACK_V2.md`
- `analysis/notebooks/solarloss_shading_evaluation_v2.ipynb`
- `analysis/notebooks/solarloss_shading_evaluation_v2.executed.ipynb`

Earlier versions of `analysis/README.md`, `analysis/README_V2.md`, and `analysis/SCHEMA_FEEDBACK.md` also contain a collaborator branch or private-repository workflow wording. Owner decision: confirm whether the named reviewer and private workflow notes in current notebooks and proposal docs, and those historical references, should remain when the repository ships publicly. This is a content review, not evidence of exposed credentials. No Git history was rewritten; removed text remains accessible through older commits.

## Dependency checks and release-bundle decision

- `.github/workflows/science.yml` runs `analysis/tests` and `analysis/tools/verify_results_v2.py`. The verifier reads `results/five_minute_evaluation_v2.csv`, `shading_evaluation_v2.json`, `frozen_parameters_v2.json`, `example_cases_v2.json`, and `demo_measured_series_v2.csv`; it also checks the exact protocol and evaluation-source SHA-256 values.
- `web/scripts/research-preview.ts` reads `results/example_cases_v2.json`, `results/shading_evaluation_v2.json`, and `results/demo_measured_series_v2.csv`. Moving the demo CSV would break the development preview unless its data-loading path changed.
- The root README, `docs/SCIENTIFIC_VALIDATION.md`, `docs/DEMO.md`, frontend research copy, and scientific documentation link to the current summaries and results. Updated links point to the canonical index, protocol, and report. Small pointers remain only where the v1/v2 notebooks still name the older `SCHEMA_FEEDBACK.md`, `README_V2.md`, and `INITIAL_AUDIT_V2.md` paths.
- The large CSV and executed notebook were added with the scientific run at source commit `e350c845b401e4926b4887219cdf453b03e746f3`. A checksum manifest for the package layout was added later at `62add4c3a51dd30c49c9cc9ae9c09bf475c2d490`; the executed notebook and output CSV checksums are recorded in `results/package_manifest_v2.json`.
- A versioned GitHub Release bundle is a better home for the 12.9 MB full evaluation table and the executed notebook once CI can download and checksum that exact asset. The bundle should include a manifest with the release tag, full source commit SHA, protocol and evaluation-source SHA-256, each asset SHA-256, and reproduction instructions. The notebook and compact preview files can remain in Git.
- These large files remain tracked because no release asset or checksum-verifying CI download has been established, and CI currently consumes the large CSV directly. No tracked results or notebooks were deleted or relocated in this pass.

## Before/after file map

| Before | After |
| --- | --- |
| `analysis/README.md` held legacy v1 setup notes; `README_V2.md` held the current workflow. | `analysis/README.md` is the single current index and v2 reproduction guide. V1 setup information is summarized there; `README_V2.md` remains a short notebook-compatible pointer. |
| V1 and v2 audit/methodology/comparison documents were mixed into the analysis root. | Duplicate v2 overviews and unreferenced legacy documents are removed from the current tree after dependency checks. The old schema/revision/notebook paths still referenced internally have concise pointers; other links now target canonical sources. |
| Source, notebooks, generated results, and dependency-sensitive data shared one directory listing. | All source, tests, notebooks, protocols, primary evidence, and results remain at their existing paths. The preview and CI inputs are unchanged. |

This pass does not change repository visibility or select a source-code license. Consolidated/deleted file contents remain available through earlier commits if the repository is made public; no history rewrite was performed.
