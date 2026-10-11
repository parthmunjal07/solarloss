# Frontend verification

## Product refinement — 11 October 2026

Local lint, TypeScript, all 58 unit tests and the production build pass. Initial JavaScript including preloads is 126.8 KiB gzip; the 3D scene remains separately loaded. All 23 browser checks pass on installed Chromium: 17 route/accessibility/interaction checks plus six 3D/fallback checks at 375, 768 and 1280px. Browser configuration accepts explicit local executable/port overrides while retaining CI defaults.

Before captures: `qa-screenshots/before/<width>-{landing,investigation,evidence,html}.png`. Product captures: `qa-screenshots/product/<width>-{landing,investigation,evidence}.png`. Desktop landing and mobile evidence were visually reviewed; genuine API captures retain the approved artifact and no editor/desktop character overlay.

The sections below record the historical Phase 5 checks and should not be read as the current information architecture.

Phase 5 verified locally on Windows with Node 24 and installed Chrome, 11 October 2026. Frontend CI repair: `604f79cf5dde6d46c5e39e0a2c460ed63e863473`; reconciled scientific-definition approval baseline: `9d87bf2d9d9fba5e531fe5cc2f5e24969a701722`.

All checks below passed after a clean installation.

| Check               | Result                                                                     |
| ------------------- | -------------------------------------------------------------------------- |
| Dependency install  | Passed; zero audit vulnerabilities                                         |
| `npm run lint`      | Passed                                                                     |
| `npm test`          | 58 tests passed across four files                                          |
| `npm run typecheck` | Passed for application, test and development code; also required by build  |
| `npm run build`     | Passed, including production import/content guards                         |
| `npm run test:e2e`  | 23 browser tests passed using installed Chrome; real WebGL via SwiftShader |

The production JavaScript is 125.8 KiB gzipped initially **including module preloads**, below the 250 KiB budget. Investigation charts load separately at 123.9 KiB gzip; the report chunk is 3.9 KiB. The Three.js/Fiber scene is a separate 239.2 KiB gzip chunk, requested only when the setup approaches the viewport. Its 935 kB minified size produces Vite's large-chunk warning; it does not enter the initial bundle or the landing/report routes. The production v0.2 schema validator is separately loaded at 44.3 KiB gzip only for an actual v0.2 API response. These are build measurements, not deployed-network or hardware-GPU performance claims.

## Browser and visual checks

Playwright covers all five routes in Summary and Analyst at 375, 768 and 1280 pixels: 30 route/mode/width combinations, each with exactly one H1, no horizontal page overflow and no browser runtime error. The research preview uses the real committed shading_01 measurements. Screenshots are retained locally in ignored `web/qa-screenshots/`, named `<width>-<mode>-<route>.png`.

Screenshots of every route were visually inspected at 375, 768 and 1280 pixels, including contact sheets retained locally alongside the original captures. Analyst screenshots were also reviewed for the investigation and evidence report. Visual corrections included separating the shading/alert chart annotations, increasing the contrast of essential hatching and raw-reference lines, preserving mobile stacking, and allowing action/progress sections to wrap at 200% CSS zoom.

The browser suite additionally verifies mode switching, explicit URL precedence, reload/navigation persistence, keyboard drawer opening/closing, focus return, 20-row pagination, all three source-driven v0.1 API decisions, actual report-route navigation followed by a local HTTP 302, empty/malformed/503 states, one-record listings, production preview rejection, and reduced motion/200% zoom. Six additional tests exercise the actual Three.js renderer at all three widths, mode switching, module keyboard selection, camera zoom/reset/orbit, overflow, accessible controls, manual 2D switching, WebGL unavailability and context loss. Landing/report routes do not request the 3D runtime.

Phase 5 captures are in ignored `web/qa-screenshots/solar-<width>-3d.png` and `solar-<width>-2d.png`. The desktop, mobile and mobile fallback captures were visually inspected. Full-page desktop/mobile captures are also retained as `phase5-desktop.png` and `phase5-mobile.png`; screenshot stitching may capture the fixed skip link in component-only images.

Axe WCAG 2 A/AA and WCAG 2.1 A/AA scans cover every page in both modes at 375px, plus the measurement drawer, with no detected violations. This does not substitute for a human screen-reader or external first-read review.

## Contrast audit

| Pair                                        | Contrast ratio |
| ------------------------------------------- | -------------: |
| Primary text / warm background              |        14.95:1 |
| Muted text / white surface                  |         7.53:1 |
| Primary button text / primary               |        14.95:1 |
| Supported text / supported background       |         4.84:1 |
| Inconclusive text / inconclusive background |         6.65:1 |
| Insufficient text / insufficient background |         6.28:1 |
| Measured line / white                       |         5.02:1 |
| Expected line / white                       |         6.86:1 |
| Essential gap hatch / white                 |         4.76:1 |

The specified missingness token alone is 2.50:1 against white. It is preserved in the token system; essential gap hatching uses insufficient-border at full opacity and the raw-reference series uses text-muted, with distinct line styles and text labels.

## Scientific and production boundaries

The production module guard rejects test/fixture/dev imports and scientific research files. The emitted-content check rejects fixture identifiers and exact preview quantities, and enforces an initial 250 KiB gzip budget. The preview parser is dynamically imported only inside the compile-time development branch. Production builds contain neither the preview parser nor measured preview JSON/CSV.

The chart tests preserve null/invalid intervals, explicit exclusions between sparse samples, event boundaries, original extrema, uncertainty gaps and the point budget. The V3 source's 28 unavailable expected-power values remain chart gaps while measured and reference values remain available. If essential markers cannot fit, the chart refuses unsafe downsampling. Source energy values remain unchanged. There is no browser energy integration or derived scientific decision. Unit tests pin the byte-identical approved schema hash, reject proposed/unapproved production responses, preserve v0.1 and the actual v0.2 listing shape, and render the genuine V3 scientific metrics, `LIMIT`, unavailable event decision and proposed contextual checks.

## Approved release and real local API integration

After frontend CI passed on `a7936d44b1a4d67328b342f7fc85fdbda9803b63`, the user explicitly confirmed Rachit's artifact-specific bounded release authorization. A separate approved JSON was prepared and validated, changing only `approval_status` and `decision.owner_review`. Every other parsed field equals the historical source. Backend verification: 89 tests pass; 34 scientific tests and committed-result consistency checks pass; both genuine V3 artifacts pass strict offline validation/HTML rendering; lint and formatting pass; the full Python 3.12/x86_64 Lambda ZIP builds and validates (17,298,747 bytes).

`npm run test:api`: three tests pass against the real backend application and production frontend, with no mocked routes or preview parameters. They verify exact approved JSON/listing equality, the full selection/3D/chart/evidence/check journey on mobile and desktop, accessibility, and the actual report 302/HTML attachment with its source values, approval reference and content hash. Captures: `qa-screenshots/api-375-investigation.png`, `api-1280-investigation.png`, `api-375-report.png`, `api-1280-report.png`. Desktop/mobile investigation and desktop report captures were visually inspected. This uses an isolated approved-file store, not private S3.

## Verification limits

No deployed API URL or private S3 download was supplied. Field definitions and the specific bounded shading release are now approved under separate recorded decisions. Successful approved v0.2 local API integration is verified above; AWS end-to-end success remains unverified. The user postponed AWS deployment, superseding the earlier conditional authorization. Local completion does not depend on cloud configuration; AWS prerequisites are documented for a separate future phase. No AWS upload or production gate activation occurred.

External first-read feedback and a human screen-reader walkthrough remain manual review tasks. No AWS resources or historical scientific exports were changed. Backend additions provide local approved-release verification only; the production serving gate remains unset.
