# Frontend verification

Verified locally on Windows with Node 24 and installed Chrome, 10 October 2026. Baseline main: `73a27ac636ea94547463fbb9562265bcf25caeb6`.

All checks below passed after a clean installation.

| Check               | Result                                                                    |
| ------------------- | ------------------------------------------------------------------------- |
| `npm ci`            | Passed; 371 packages installed, zero audit vulnerabilities                |
| `npm run lint`      | Passed                                                                    |
| `npm test`          | 36 tests passed across three files                                        |
| `npm run typecheck` | Passed for application, test and development code; also required by build |
| `npm run build`     | Passed, including production import/content guards                        |
| `npm run test:e2e`  | 17 browser tests passed using installed Chrome                            |

The final production JavaScript is 124.3 KiB gzipped initially, below the 250 KiB budget. Investigation charts load separately at 123.8 KiB gzip; the report chunk is 3.7 KiB gzip. CSS is 6.28 kB gzip, with a self-hosted 48.25 kB Latin Inter font. These are build measurements, not a deployed-network performance claim.

## Browser and visual checks

Playwright covers all five routes in Summary and Analyst at 375, 768 and 1280 pixels: 30 route/mode/width combinations, each with exactly one H1, no horizontal page overflow and no browser runtime error. The research preview uses the real committed shading_01 measurements. Screenshots are retained locally in ignored `web/qa-screenshots/`, named `<width>-<mode>-<route>.png`.

Screenshots of every route were visually inspected at 375, 768 and 1280 pixels, including contact sheets retained locally alongside the original captures. Analyst screenshots were also reviewed for the investigation and evidence report. Visual corrections included separating the shading/alert chart annotations, increasing the contrast of essential hatching and raw-reference lines, preserving mobile stacking, and allowing action/progress sections to wrap at 200% CSS zoom.

The browser suite additionally verifies mode switching, explicit URL precedence, reload/navigation persistence, keyboard drawer opening/closing, focus return, 20-row pagination, all three source-driven API decisions, actual report-route navigation followed by a local HTTP 302, empty/malformed/503 states, one-record listings, production preview rejection, and reduced motion/200% zoom.

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

The chart tests preserve null/invalid intervals, explicit exclusions between sparse samples, event boundaries, original extrema, uncertainty gaps and the point budget. If essential markers cannot fit, the chart refuses unsafe downsampling. Source energy values remain unchanged. There is no browser energy integration or derived scientific decision.

## Verification limits

No deployed API URL, real approved review store or private S3 download was supplied. The API response and redirect interactions were tested with clearly synthetic test-only responses; no AWS end-to-end success is claimed. Production v0.2 approval/serving remains blocked by the documented science/backend contract process. The local development preview and the production build were both exercised.

External first-read feedback and a human screen-reader walkthrough remain manual review tasks. No AWS resources or backend/scientific files were changed.
