# Proposed public research layout — owner review

This is a proposed organization for future public releases. It does not remove, move, rewrite, or conceal any current file or Git history.

## Keep easy to find in the main repository

| Area | Keep in main tree | Reason |
|---|---|---|
| Scientific implementation | analysis/src/solarloss_research/, analysis/tools/, and focused tests | The analysis must be inspectable and runnable. |
| Protocol and provenance | V2 and future protocol, methodology, data audit, provenance, and contract decision records | Definitions, inputs, splits, and limitations determine what the numbers mean. |
| Frozen headline results | Compact V2 result JSONs, package manifest, independent verification record, and a small set of representative event artifacts | The results and their checksums should be discoverable without unpacking an archive. |
| Reproduction environment | Pinned runtime files, environment notes, and one canonical executable notebook or CLI recipe | A new reader needs a defined way to reproduce rather than several competing entrypoints. |
| Selected demonstration | A bounded shading example with explicit UTC boundaries, support, and known limitations | It illustrates the method without hiding non-events or unavailable cases. |

Historical V1/V2 reports should remain traceable. If duplicate reports are retired from the landing page, preserve the files and their history and point readers to one canonical summary.

## Package as versioned research releases

The following derived artifacts are useful, but can be grouped under immutable release tags or archival research bundles instead of all occupying the top level of the source tree:

- Full 12.9 MB five_minute_evaluation_v2.csv processed table, with the exact package manifest and schema. Keep a small sample or summary in the repository only if it cannot be mistaken for the full evaluation set.
- Executed notebook copy of about 540 KB and generated diagnostic charts/tables. Keep notebook source and the CLI reproduction path in-tree; put bulky execution outputs under a versioned release.
- The 366 KB legacy v0.1 review export, alongside its explicit warning and source history. Preserve it unchanged; it should not be presented as the canonical scientific shading review.
- Repeated historical reports and duplicated result projections where the same figures are already represented by versioned JSON and a canonical summary. Archive copies with release provenance rather than deleting them.
- Larger future plots, event-specific exports, and derived tables once their number or total size makes the source tree hard to browse.

The 652 KB measured shading demo series and compact V2 JSONs are relatively small; retaining them in-tree is reasonable if licensing and raw-source redistribution terms permit. Raw Zenodo inputs are not present in this checkout. Do not copy, expose, or repackage raw data until its license and repository policy are checked.

## Suggested release structure

Use a versioned release directory or immutable tagged archive with:

    README.md
    protocol/
    provenance/
    data/processed/
    results/
    figures/
    notebooks/executed/
    environment/
    SHA256SUMS

Each release should state the source commit, protocol hash, software/runtime versions, processed-input hashes, generation commands, license, data access instructions, and whether raw bytes were downloaded and verified during that release. Store unavailable raw data externally under its original DOI and license; never make a checksum appear to be a newly performed download check when it is only inherited from V2.

## Public landing path

Keep one short scientific README that links to:

1. Research question, frozen split, primary outcomes and limitations.
2. Provenance and input manifest.
3. Executable source and exact reproduction commands.
4. Compact headline JSONs and one selected review artifact.
5. Versioned research releases for large/bulk outputs.
6. The current contract and approval state.

Every exploratory result should say so in the artifact and documentation. Publish the failed/limited detector results and unavailable energy cases with the same visibility as the example event. This is a proposal for Rachit and repository-owner review; no layout change is made here.
