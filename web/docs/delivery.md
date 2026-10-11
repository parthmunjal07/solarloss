# SolarLoss frontend delivery

Baseline main SHA: `73a27ac636ea94547463fbb9562265bcf25caeb6`. The final pushed SHA is provided in the chat handoff and `git log -1`.

## Completed experience

- Landing: specified seven-section structure, illustrative SAMPLE visuals, real dataset citation and a direct experiment CTA.
- Explorer: actual API records only, source provenance from cached individual reviews, experiment-type filtering in Analyst mode, loading/error/empty states.
- Investigation: measured versus calibrated expected power, distinct raw reference, sourced shading/alert annotations, honest gaps, source metrics, Analyst brush/residual/context, original paged measurement drawer.
- Evidence report: three source-driven decisions and distinct unavailable research decision, plain explanation, checks, uncertainty/baseline/placebo/robustness, exclusions, limits, qualified and explicitly unapproved preview checks, real HTML-export route for API reviews.
- Method: committed research methodology, data source, calibration, false alarms, uncertainty, placebo and limitations.
- Reading mode: shareable query state, URL precedence, safe localStorage fallback and navigation/reload restoration.

## Integration and preview

The typed API client implements health, mixed-version listing, review and report URL handling. Production retains v0.1 provisional wording and supports artifact-approved v0.2 research evidence through the real API. It never substitutes preview or synthetic data on failure. The offline proposed-only adapter remains separate. See the Phase 5 capabilities and exact approval boundary in [backend-handoff.md](backend-handoff.md).

Development middleware projects only `analysis/results/example_cases_v2.json`, `shading_evaluation_v2.json` and `demo_measured_series_v2.csv`. Exact source hashes are available in the UI. shading_01 energy totals and coverage come from committed results, powers/residuals from the CSV, and E5 candidate wording from `analysis/INVESTIGATION_GUIDANCE_PROPOSAL.md`. The preview has no inferred review decision and cannot export.

A compatible API origin and private review store remain infrastructure responsibilities. Scientific field semantics are approved; artifact promotion and backend gate enforcement remain distinct from that approval. The interactive Solar Array is completed on investigation/method with three modes, camera/module controls and an accessible SVG fallback. The primary evidence chart remains above the diagram.

## Verification and deviations

See [verification.md](verification.md) for checks, screenshots and limitations. All available frontend checks pass; private AWS report delivery was not exercised. The external first-read reviewer remains a manual check.

Deliberate design decisions are documented in [design-decisions.md](design-decisions.md): source truth takes precedence over illustrative cards/metrics; unavailable fields stay unavailable; native disclosure and a focused Radix drawer keep the evidence accessible; controls remain at least 44px; essential hatching uses an accessible documented token. The 3D view explains the setup without diagnoses, physical simulations, recovered energy or commercial claims. [claims-audit.md](claims-audit.md) maps rendered facts to sources.

## Run locally

```powershell
cd web
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. Use `/experiments?preview=research&mode=summary` for the development research view. For real API reviews, run the configured existing backend at port 8000 or set `VITE_API_BASE_URL` to the API origin. `npm run build` creates `web/dist/`; `npm run preview` serves production with no research preview.

## Exact changed files

57 files, all within `web/`. No backend, schema, analysis or infrastructure file changed.

| Change   | File                                               |
| -------- | -------------------------------------------------- |
| Modified | `web/.gitignore`                                   |
| Modified | `web/README.md`                                    |
| Modified | `web/index.html`                                   |
| Modified | `web/package-lock.json`                            |
| Modified | `web/package.json`                                 |
| Modified | `web/public/favicon.svg`                           |
| Deleted  | `web/public/icons.svg`                             |
| Deleted  | `web/src/App.css`                                  |
| Deleted  | `web/src/App.tsx`                                  |
| Deleted  | `web/src/assets/react.svg`                         |
| Deleted  | `web/src/assets/vite.svg`                          |
| Deleted  | `web/src/index.css`                                |
| Modified | `web/src/main.tsx`                                 |
| Modified | `web/vite.config.ts`                               |
| Added    | `web/.env.example`                                 |
| Added    | `web/dev/proposed-v2.ts`                           |
| Added    | `web/docs/backend-handoff.md`                      |
| Added    | `web/docs/claims-audit.md`                         |
| Added    | `web/docs/delivery.md`                             |
| Added    | `web/docs/design-decisions.md`                     |
| Added    | `web/docs/verification.md`                         |
| Added    | `web/playwright.config.ts`                         |
| Added    | `web/scripts/check-production.mjs`                 |
| Added    | `web/scripts/fixture-guard.ts`                     |
| Added    | `web/scripts/research-preview.ts`                  |
| Added    | `web/src/app/App.tsx`                              |
| Added    | `web/src/app/Layout.tsx`                           |
| Added    | `web/src/app/Mode.tsx`                             |
| Added    | `web/src/app/queries.ts`                           |
| Added    | `web/src/components/charts/PowerChart.tsx`         |
| Added    | `web/src/components/decision/DecisionBanner.tsx`   |
| Added    | `web/src/components/ui/Common.tsx`                 |
| Added    | `web/src/components/ui/Measurements.tsx`           |
| Added    | `web/src/features/experiments/Experiments.tsx`     |
| Added    | `web/src/features/investigation/Investigation.tsx` |
| Added    | `web/src/features/landing/Landing.tsx`             |
| Added    | `web/src/features/method/Method.tsx`               |
| Added    | `web/src/features/report/Report.tsx`               |
| Added    | `web/src/lib/adapters.ts`                          |
| Added    | `web/src/lib/api.ts`                               |
| Added    | `web/src/lib/chart-data.ts`                        |
| Added    | `web/src/lib/formatters.ts`                        |
| Added    | `web/src/lib/research.ts`                          |
| Added    | `web/src/lib/schemas.ts`                           |
| Added    | `web/src/lib/types.ts`                             |
| Added    | `web/src/styles/font.css`                          |
| Added    | `web/src/styles/globals.css`                       |
| Added    | `web/src/styles/tokens.css`                        |
| Added    | `web/tests/browser/review.spec.ts`                 |
| Added    | `web/tests/fixtures.ts`                            |
| Added    | `web/tests/navigation.test.tsx`                    |
| Added    | `web/tests/proposed-v2-sample.json`                |
| Added    | `web/tests/proposed-v2.test.ts`                    |
| Added    | `web/tests/science.test.tsx`                       |
| Added    | `web/tests/setup.ts`                               |
| Added    | `web/tsconfig.tests.json`                          |
| Added    | `web/vitest.config.ts`                             |
