# SolarLoss frontend

React + TypeScript + Vite evidence-review application. Production accepts review schema v0.1.0 only. Proposed v0.2 is never treated as an API review.

From the repository root:

```powershell
cd web
npm ci
npm run dev
```

Open `http://127.0.0.1:5173` (or the printed URL). `/api/*` proxies to the existing backend local server at port 8000, which requires a configured real private S3 review store. See `../backend/README.md`. For another API origin, copy `.env.example` to `.env.local`, set `VITE_API_BASE_URL` to the origin without `/api/v1`, then restart Vite.

For development preview, open `/experiments?preview=research&mode=summary`. Middleware reads committed `analysis/results/example_cases_v2.json`, `shading_evaluation_v2.json` and `demo_measured_series_v2.csv` on demand. Only the real shading_01 example is displayed, with an unapproved research-preview banner. There is no three-state review decision; export is disabled and E5 next checks stay proposed/unapproved.

Production builds import no measured preview files or synthetic fixtures. `npm run preview` serves the production build and has no research-preview middleware. The import guard rejects fixtures/test modules/research data in production.

```powershell
npm run lint
npm run typecheck
npm test
npm run build
npm run test:e2e
```

Playwright uses installed Chrome; `PLAYWRIGHT_CHANNEL` can select another supported installation. Screenshots and traces remain in ignored `qa-screenshots/` and `test-results/`. Unit tests use SAMPLE fixtures confined to `tests/`.

Summary/Analyst is stored in `?mode=summary` / `?mode=analyst`, with URL precedence and safely accessed localStorage fallback. Navigation retains mode. Charts keep exclusions/event boundaries within 1,500 displayed points; an original paged measurement table is always reachable. Scientific totals come only from source artifacts.

See `docs/backend-handoff.md` for missing fields, approval and AWS hosting; `docs/design-decisions.md` and `docs/claims-audit.md` for design/source decisions; `docs/verification.md` for completed checks.
