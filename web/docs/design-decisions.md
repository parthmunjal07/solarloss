# Design decisions

Authority: [Frontend Design and Build Specification, sections 1–17](https://docs.google.com/document/d/1O1C472Fbj7ZJP3NeE-Sp1RFNQXypLFIPegP2BN2FNrg/edit). Science follows committed V2 results; serving follows backend v0.1.

- Retain React/TypeScript/Vite. React Router owns routes and reading mode; TanStack Query owns cache/retries; Zod validates responses; Recharts supplies code-split charts; Lucide supplies five icon types; Inter Variable is self-hosted, Latin subset.
- Tailwind theme variables support tokens. Named CSS keeps visual review straightforward. Native details provides disclosure; Radix Dialog provides drawer focus trapping/return. A full shadcn catalogue, class helpers and motion library add no necessary behavior.
- Charts render without draw animation, keeping mode changes stable and honoring reduced motion. Skeleton pulse stops under reduced motion.
- The missingness token has only 2.50:1 contrast on white. Essential hatching therefore uses the documented insufficient-border token at full opacity (4.76:1), and the raw-reference line uses text-muted (7.53:1). The original tokens are preserved. Alert text is placed below the curve to avoid overlapping the experimental-label annotation.
- Ajv and ajv-formats validate the complete proposed JSON Schema in an isolated offline adapter; Zod then narrows renderable metric types and enforces the proposed-only gate. This adapter and its test fixtures are prohibited from production imports. Zod's JSON Schema converter cannot represent the contract's conditional rules, so they are not dropped or approximated.
- Minimum 44px controls supersede the 36px toggle example. Colors, type hierarchy, decision border styles, 1120px content width and 400/280px chart heights follow the document. Explicit mobile padding/spacing exceptions are retained.
- Render only actual listed experiments, rather than three illustrative cards. No invented records.
- Summary uses observed energy, model-expected energy and signed deviation only where supplied. v0.1 deficit is provisional; missing totals stay unavailable. Analyst adds coverage.
- Bounds, precise annotations, residuals, model metadata and next checks are unavailable when absent. Research LIMIT never becomes a three-state artifact decision. Preview checks remain unapproved.
- Development middleware reads committed research on demand. Production has no scientific CSV/JSON imports or middleware. The compact projection is separate from the underspecified proposed API contract.
- No demo video URL was supplied; show Not available. Illustrative curve, decision and reading-mode previews carry SAMPLE labels.
- A first-read check by someone outside the team remains a manual product-review check.

Verification and measured build sizes are recorded in `verification.md` after checks finish.
