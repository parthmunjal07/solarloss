# Demo playbook

This playbook separates the dataset-backed local research preview from a deployed review workflow. It does not supply a live demo or video URL because none is verified in this checkout.

## Local experiment walkthrough

The Vite preview reads the committed, dataset-backed v2 results. It is a development preview, not the production API. From the repository root:

```powershell
cd web
npm ci
npm run dev
```

Open the printed local URL, then visit `/experiments?preview=research&mode=summary` and open the `shading_01` experiment. Keep the research-preview banner visible so the audience can see that this is an offline result.

1. Show the target and comparison inverter streams, then explain that the comparison stream is nonidentical and not ground truth.
2. On `shading_01`, compare measured target power with calibrated, model-expected power. Describe the approximately **0.39705 kWh signed modelled generation deviation** as an estimate relative to the model, not recovered electricity or proven causal loss.
3. Show observed coverage and uncertainty. State that only 10 of 23 episodes have adequate matched-placebo support, and that the demo event's empirical model-error band is not a counterfactual-loss confidence interval.
4. Show the research limitation alongside the **LIMIT** result: the detector's false-alarm rate was 0.08526 runs/hour against a frozen limit of 0.05/hour. All 23 documented episodes were detected retrospectively on one installation; simple baselines also detected all 23.
5. Explain that PV voltage/current offer operating context. Proposed technician checks are unapproved; no diagnosis, repair, or revenue claim is supported.
6. Open the method page and cite the pinned [Zenodo record](https://zenodo.org/records/7291380), the [Data in Brief article](https://doi.org/10.1016/j.dib.2022.108723), and the committed [experiment report](../analysis/EXPERIMENT_REPORT_V2.md).

The “Analyst” mode and measurement drawer can show original measurements and exact units. Avoid presenting the Vite preview as a live AWS review or saying that its page itself computed the verdict.

## Insufficient-evidence example: BLOCKED for the review UI

The v2 examples include an actual insufficient-data interval in [`analysis/results/example_cases_v2.json`](../analysis/results/example_cases_v2.json): a measured source outage from 22 December 2021 to 24 January 2022 (2,848,806 seconds), with no interpolation and `energy_kwh: null`. This is a supported example of withholding an estimate when measurements are absent. The current Vite preview does not render it, so it is available to cite from the committed result file, not as a UI route.

There is also a committed v0.1 result at [`analysis/results/review_la-reunion_healthy-placebo-no-posttraining-shading_0.1.0.json`](../analysis/results/review_la-reunion_healthy-placebo-no-posttraining-shading_0.1.0.json) whose stored decision is `insufficient_evidence`. It records a held-out healthy placebo with zero labelled shading episodes in the final-test split. It is not a shading-loss result.

The file currently fails the backend identity contract: its filename encodes a different experiment ID from `experiment.identifier` and `review_id`. `python -m backend.validate_artifact` reports those mismatches. It must not be renamed, edited, or represented as a served example during this pass because it is a committed scientific output. **Showing this artifact through the frontend/API is blocked until the science owner supplies a correctly versioned artifact or approves a provenance-preserving correction.** Do not create a synthetic substitute for the demo.

## AWS review and downloaded report: BLOCKED

No AWS account, deployed API origin, CloudFront site, private review artifact, or production report download is verified. The review UI can display v0.1 artifacts from the API, and the backend can generate an HTML report and redirect to a short-lived S3 URL, but this integration cannot be demonstrated as live from the current checkout. Do not present the development preview as that service.

After the infrastructure owner deploys the documented stack and validates a real, approved artifact, use [`DEPLOYMENT.md`](DEPLOYMENT.md) to verify `/api/v1/health`, the review listing, an artifact response, and the report download redirect. Record the verified URLs and access date in the submission materials before linking them.

## Reproducibility and submission

- Link to the [repository](https://github.com/parthmunjal07/solarloss) and this experiment's protocol, result report, and provenance files.
- The fast scientific tests and `python analysis/tools/verify_results_v2.py` check mechanics and consistency of committed outputs. They do not reproduce the full experiment.
- Full rerun requires the pinned source files (about 1.8 GB), the documented Python dependencies, and the notebook/CLI workflow in [`analysis/README.md`](../analysis/README.md).
- A video, live-demo link, deployed screenshot, and AWS report walkthrough remain **BLOCKED** until verified. No demo media should be fabricated to fill those gaps.
