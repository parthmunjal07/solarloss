# SolarLoss frontend

React + TypeScript + Vite evidence-review application. Production supports v0.1.0 and artifact-approved v0.2.0 responses from the actual backend API. Proposed research files are never treated as production API reviews.

From the repository root:

```powershell
cd web
npm ci
npm run dev
```

Open `http://127.0.0.1:5173` (or the printed URL). `/api/*` proxies to the existing backend local server at port 8000, which requires a configured real private S3 review store. See `../backend/README.md`. For another API origin, copy `.env.example` to `.env.local`, set `VITE_API_BASE_URL` to the origin without `/api/v1`, then restart Vite.

For development preview, open `/experiments?preview=research&mode=summary`. Middleware reads committed `analysis/results/example_cases_v2.json`, `shading_evaluation_v2.json` and `demo_measured_series_v2.csv` on demand. Only the real shading_01 example is displayed, with an unapproved research-preview banner. There is no three-state review decision; export is disabled and E5 next checks stay proposed/unapproved.

Production builds import no measured preview files or synthetic fixtures. `npm run preview` serves the production build and has no research-preview middleware. The import guard rejects fixtures/test modules/research data in production.

The offline `dev/proposed-v2.ts` adapter validates against the unchanged candidate JSON Schema and retains typed event context, provenance, metric availability/coverage/ratios/uncertainty, electrical evidence and proposed checks. Its tests read both genuine committed V3 reviews directly; the obsolete synthetic V2 sample has been removed. Research LIMIT remains separate from the unavailable event review, owner approval stays null, and source intervention bounds remain separate from detector confirmations. The production parser is separate: it accepts only `owner_approved` API artifacts carrying the exact semantics-approved schema hash and a matching protocol hash in the backend-supplied approval record. Field-semantics approval was recorded in `../docs/phase-4-scientific-decision-sheet.md`; artifact promotion, backend gate activation and deployment remain separate responsibilities.

## Interactive Solar Array

On `/experiments/shading_01`, follow **Explore the two-inverter setup** beside the primary evidence chart. The same explanatory component appears on `/method`. Switch between Normal setup, Documented shading and Reference comparison. Drag the scene to orbit, pinch or use the zoom buttons, and reset the camera. Camera rotation also has keyboard-accessible buttons. Select a 3D module or focus/activate one of the 24 HTML module buttons to read its role in the information panel. **Use 2D view** switches to an equivalent SVG diagram while retaining every explanation and module selector.

The configuration comes from [Lebreton et al. (2022), §3](https://pmc.ncbi.nlm.nih.gov/articles/PMC9497466/#sec3-entropy-24-01311), checked against `analysis/DATA_PROVENANCE.md`: two inverter lines, each with 12 modules arranged electrically as two parallel strings of six. Graillet et al.'s [pinned Zenodo record](https://zenodo.org/records/7291380) documents the one-entire-module intervention. The depicted module numbering, physical arrangement, mounts and cover are illustrative. The component does not reconstruct the rooftop, assign per-module production, diagnose a cause, move a measured shadow, fill missing data or estimate recoverable energy. The evidence chart remains the scientific source of comparison.

Three.js and React Three Fiber 9 (React 19 compatible) load only when this section approaches the viewport. The landing and report routes do not request the 3D runtime. Rendering uses a demand frame loop, DPR capped at 1.5, instanced module geometry, local procedural cell texture and no external models/HDR assets. Orbit controls, shared GPU resources and context listeners are disposed on unmount; reduced motion disables camera damping. WebGL initialization failures, lost contexts and lazy-chunk failures leave the SVG schematic and accessible HTML explanations usable. No energy or science values drive scene animation.

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
