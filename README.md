# SolarLoss

SolarLoss is a research evidence viewer for comparing measured solar PV output with an expected-output estimate and showing how much confidence the available evidence supports.

## The problem and intended use

When an inverter produces less than expected, an operator needs context before deciding what to inspect: a comparison stream, weather conditions, data quality, uncertainty, and the limits of the inference. SolarLoss is a research prototype for PV operations teams and solar-energy researchers reviewing those measurements. It does not diagnose a fault or prescribe a repair.

## What it does

1. Loads aligned measurements from two inverter lines and, for the v2 experiment, irradiance and temperature observations.
2. Fits an expected-output model on earlier healthy observations and compares the target line's measured output with that estimate.
3. Evaluates retrospective, documented shading episodes and reports healthy-period false alarms, coverage, uncertainty, and limitations.
4. Stores the research outputs as versioned files. A separate review API validates and serves v0.1 review JSON; it does not run the model or make a scientific decision.
5. Presents API reviews in a React application. A clearly marked, development-only research preview reads committed v2 results; production builds do not include that preview data.

The offline pipeline, backend, and frontend ownership boundaries are described in [Architecture](docs/ARCHITECTURE.md).

## Why two inverter streams?

The experiment has a target inverter line where shading interventions were documented and a second line used as a comparison stream. Earlier healthy periods calibrate how the target relates to that stream. The lines are not identical and are not independent experimental replicates, so the comparison stream is not ground truth. The analysis also uses weather fields in its selected model to account for changing operating conditions.

## Model and evidence

The v2 retrospective analysis selected a five-minute weather-assisted linear regression model (`sklearn.linear_model.LinearRegression`). It predicts target-line power from reference-line power, global tilted irradiance (GTI), diffuse tilted irradiance (DTI), and ambient temperature (TA), using pre-event healthy data. The `Fault` labels are held out from prediction and used for evaluation only. This is offline research, not live inference.

The experimental measurements come from the version 2 record of the [La Réunion rooftop PV shading dataset](https://zenodo.org/records/7291380), published by Graillet et al. in [Data in Brief](https://doi.org/10.1016/j.dib.2022.108723). The dataset is attributed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); see [data provenance](analysis/DATA_PROVENANCE.md) for file checksums and attribution details. The system context is described by Lebreton et al. in [Entropy](https://doi.org/10.3390/e24091311). Raw dataset files are not stored in this repository.

The current v2 report records 23 of 23 documented physical shading episodes detected retrospectively on this one installation. Simple baselines also detected all 23. The selected detector produced 153 healthy alert runs over 1,794.5067 supported healthy hours: **0.08526 runs/hour**, above the frozen limit of 0.05/hour. Its research verdict is therefore **LIMIT**. This is not a general fault-detection rate or a prospective guarantee.

For `shading_01`, the signed modelled generation deviation is about **0.39705 kWh**. It is an expected-minus-measured model estimate, not verified recoverable energy, causal shading loss, or revenue. Voltage and current observations provide operating context, not a diagnosis. Technician checks remain proposed and unapproved; long-term degradation and panel ageing are not validated. See [Scientific validation](docs/SCIENTIFIC_VALIDATION.md) and the committed [v2 experiment report](analysis/EXPERIMENT_REPORT_V2.md).

## Application status

No verified live deployment or video URL is available in this checkout. The repository contains a decorative hero image, but no verified screenshot of a deployed application, so this README does not present it as one. The Vite research preview is development-only and is not a live AWS review service. See the [demo playbook](docs/DEMO.md) for the available and blocked steps.

## Local setup

Commands below use PowerShell from the repository root.

### Frontend

```powershell
cd web
npm ci
npm run dev
```

Open the printed Vite URL, normally `http://127.0.0.1:5173`. The API proxy expects the backend local server on port 8000. The research preview is available at `/experiments?preview=research&mode=summary`; it reads committed v2 outputs and is not served by production builds.

### Backend

Use Python 3.12 and a private review bucket for the local API:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements-dev.txt
$env:AWS_PROFILE = "your-aws-profile"
$env:AWS_REGION = "your-aws-region"
$env:REVIEW_BUCKET = "your-private-review-bucket"
$env:ALLOWED_ORIGINS = "http://127.0.0.1:5173"
python -m backend.local_server
```

The local server has no sample-data fallback. For offline artifact validation without AWS, see [backend setup](backend/README.md).

### Scientific notebook

Install the documented scientific dependencies, then open the v2 notebook:

```powershell
python -m pip install -r analysis/requirements-v2.txt
python -m pip install jupyterlab
jupyter lab analysis/notebooks/solarloss_shading_evaluation_v2.ipynb
```

The full experiment downloads about 1.8 GB of checksum-verified source data into the ignored `data/` directory and needs several GB of memory. It is not run in CI. See [analysis setup](analysis/README_V2.md) before running it; historical published results are kept under `analysis/results/`.

## Checks and CI

GitHub Actions runs separate backend, frontend, and scientific workflows on pushes and pull requests to `main`. The scientific workflow runs unit tests and checks committed result consistency without downloading the raw dataset or rerunning the experiment.

```powershell
# Backend
python -m pip install -r backend/requirements-dev.txt
python -m ruff check backend
python -m ruff format --check backend
python -m pytest backend/tests -q
python -m compileall -q backend
python -m backend.build_lambda --output backend/build/solarloss-lambda.zip
python -m backend.validate_lambda_package backend/build/solarloss-lambda.zip

# Scientific unit tests and committed-result arithmetic checks
python -m pip install -r analysis/requirements-v2.txt
python -m pytest analysis/tests -q
python analysis/tools/verify_results_v2.py

# Frontend
cd web
npm ci
npm run lint
npm run typecheck
npm test
npm run build
npx playwright install chromium
$env:PLAYWRIGHT_CHANNEL = "chromium"
npm run test:e2e
```

The result verifier checks the committed CSV/JSON values and protocol/code identities; passing it does **not** reproduce the full experiment.

## Deployment and documentation

The current backend contract is review schema v0.1.0. Schema v0.2.0 remains proposed and is not served by the production API. AWS infrastructure is not included or verified in this repository. Read the [deployment guide](docs/DEPLOYMENT.md) before configuring S3, CloudFront, API Gateway, or Lambda.

- [Architecture](docs/ARCHITECTURE.md)
- [Scientific validation](docs/SCIENTIFIC_VALIDATION.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Demo playbook](docs/DEMO.md)
- [Contributing](CONTRIBUTING.md)
- [Public release checklist](PUBLIC_RELEASE_CHECKLIST.md)
- [Backend API documentation](backend/README.md)
- [Frontend documentation](web/README.md)
- [Scientific analysis documentation](analysis/README_V2.md)
