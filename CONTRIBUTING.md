# Contributing

SolarLoss contains an offline research pipeline, a schema-validated review API, and a React evidence viewer. Keep these responsibilities separate when proposing changes. Start with the root [README](README.md), [Architecture](docs/ARCHITECTURE.md), and the area-specific guides.

## Before changing scientific behavior

- Read the frozen protocol and current result report under `analysis/`.
- Keep evaluation labels out of predictors, preserve chronological split boundaries, and do not select thresholds or models using protected test results.
- Do not regenerate committed outputs as a cleanup step. A research rerun must follow the documented protocol, verify source checksums, record runtime/provenance, and explain any output change in the revision log.
- Keep measured observations, model estimates, event decisions, and experiment-level verdicts clearly distinct.
- Do not present the one-installation retrospective result as general accuracy, recovered energy, verified savings, or a diagnosis.

## Schema and integration changes

The backend serves review schema v0.1.0. Schema v0.2.0 remains proposed. A schema change must update the scientific producer, versioned contract copies, backend validation and tests, frontend runtime schema/adapter, and integration documentation together. Do not mark v0.2 as approved or enable production serving without explicit science-owner approval and a documented handoff.

Use real analysis output for product artifacts. Synthetic values belong in tests and must remain visibly labeled as synthetic. Never add AWS credentials, private bucket names, raw downloaded datasets, or local machine paths to commits.

## Local checks

Run the checks for each changed area from the repository root:

```powershell
# Backend
python -m pip install -r backend/requirements-dev.txt
python -m ruff check backend
python -m ruff format --check backend
python -m pytest backend/tests -q
python -m compileall -q backend

# Scientific mechanics and committed result consistency
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

The result verifier checks committed values; it does not rerun the experiment or download the raw dataset. Full data reruns are described in [`analysis/README.md`](analysis/README.md).

GitHub Actions runs the backend, frontend, and scientific checks independently. Keep changes focused and do not force-push. Follow the repository owner's branch/review policy; a maintainer may update `main` directly only when explicitly authorized.

## License status

No project source-code license has been approved yet. Do not add a license declaration on behalf of the repository owner. The research dataset has separate CC BY 4.0 attribution requirements documented in [`analysis/DATA_PROVENANCE.md`](analysis/DATA_PROVENANCE.md).
