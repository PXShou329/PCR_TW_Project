# Private PVE Guide Library — Builder Plan

## Accepted goal

Build a private local PVE guide library from the two user-provided Excel workbooks. It
must place every imported team under the workbook's corresponding mode, element, area,
and stage; render characters primarily as portraits; support Deep Zone 1–10,
Remembrance Battlefield, and Luna Tower; preserve operation notes and source/video
links; and remain usable without independently verifying that a team clears the stage.

## Non-goals

- No independent gameplay clear verification in this phase.
- No promotion of workbook rows into research Gate evidence solely because they exist in
  the workbook.
- No bulk scraping or republication of AppMedia, GameWith, PCRD Fans, or external image
  archives.
- No public deployment, GitHub commit/push/PR/tag, or release automation.
- No rewriting of the source `.xlsx` files.

## Source interpretation contract

- `O` = `SET` and `X` = `NOT_SET` in the literal workbook text order.
- Five-character strings such as `XOOOO` are ordered operation patterns in workbook
  text order; `全SET` is the normalized `OOOOO` pattern. Mixed slash/newline values may
  contain multiple variants and must retain their raw text. These positions are not
  bound to portrait/member slots until `member_alignment` is explicitly resolved.
- Five portrait positions are ordered and must remain ordered.
- Multiple operation axes attached to one portrait group remain one team with multiple
  axes, not multiple teams.
- Merged cells, workbook-defined `#n` source aliases, displayed date-like stage labels,
  hidden reference sheets, and cached formula values require explicit parsing rules.
- A `#n` alias without an exact URL remains unresolved; it never inherits the URL from
  a preceding team.
- Unmapped portraits are retained as unresolved character references and shown with the
  exact workbook-embedded portrait; only a missing or corrupt workbook asset reaches the
  placeholder. They are never guessed across unit variants.

## External reference operating policy

- Taiwan names and Taiwan six-star release status come only from reviewed, locally
  pinned So-net Taiwan official evidence. Search results and live pages are discovery
  aids, not evidence: a claim becomes usable only after its exact source is saved,
  SHA-256 pinned, and accepted by the semantic verifier. Generic So-net shells,
  redirects, navigation-only pages, mere name co-occurrence, JP guides, community
  tools, and the presence of a six-star image do not prove Taiwan release.
- [EsterTion](https://redive.estertion.win/) is the private icon adapter and JP technical
  index. Every confirmed unit needs an explicit exact base; `${base}31` is the safe
  external default and `${base}61` is selected only after the Taiwan six-star gate
  passes. Downloaded archives are not mirrored or committed.
- [AppMedia](https://appmedia.jp/priconne-redive/4466131),
  [PCRD Fans](https://www.pcrdfans.com/en/battle), and
  [GameWith](https://gamewith.jp/pricone-re/) are secondary research references only.
  Open pages manually, retain a URL/locator when a fact is used, preserve each source's
  own claim, and never bulk scrape, republish, merge into a synthetic consensus, or
  present a returned team as independently clear-verified.
- Arena references remain outside the private XLSX PVE serving closure unless a future
  separately scoped, provenance-preserving arena slice is explicitly approved.
- AppMedia, PCRD Fans, and GameWith therefore remain locator-preserving secondary
  strategy research only. They do not populate this XLSX-backed library, establish
  Taiwan identity or six-star truth, or turn workbook teams into independently
  clear-verified strategies.

## Slice plan

### Slice 1: Reproducible workbook staging

- User-visible outcome: none yet; a deterministic import report proves what will be shown.
- Risk retired: spreadsheet structure and image/link interpretation.
- Deliverables:
  - read-only workbook parser;
  - normalized staging JSON schema;
  - workbook/source SHA checks;
  - per-sheet stage/team/axis/link/portrait reconciliation;
  - golden fixtures for `O`, `X`, merged teams, linked/aliased videos, and
    date-formatted stages.
- Done when a second run is byte-for-byte deterministic and source workbooks are unchanged.

### Slice 2: Character identity and private icon adapter

- User-visible outcome: a sampled set of workbook teams renders as five ordered portraits.
- Risk retired: portrait-to-unit identity and six-star variant selection.
- Deliverables:
  - canonical mapping registry;
  - perceptual/exact image hash assistance plus manual override queue;
  - exact TW six-star selection policy;
  - local external-image feature flag and deterministic fallback.
- Done when known samples map correctly and ambiguity fails closed.

### Slice 3: Deep Zone 1–10 walking skeleton

- User-visible outcome: one element can be browsed end to end, then expanded to all five.
- Risk retired: staging-to-local-API-to-Web ownership.
- Deliverables:
  - a read-only, file-backed local catalog adapter; no database migration is required
    while the library remains private and local;
  - API/client contracts with failure behavior;
  - element/area/stage filters;
  - team cards, operation marker, notes, provenance, and video cards;
  - desktop/mobile tests.
- Done when imported counts reconcile and existing canonical PVE behavior remains green.

### Slice 4: Remembrance Battlefield and Luna Tower

- User-visible outcome: the remaining workbook modes are browsable through the same PVE
  library.
- Risk retired: mode-specific grouping, bosses/floors, multiple axes, and hidden reference
  dependencies.
- Done when every supported visible sheet has an import report and UI route/filter path.

### Slice 5: Local acceptance and handoff

- User-visible outcome: the private local application runs with all imported content.
- Verification:
  - parser reconciliation and deterministic replay;
  - database/importer idempotency and drift failure tests;
  - API/OpenAPI/client parity;
  - desktop/mobile E2E;
  - source workbook byte hashes unchanged;
  - no external assets accidentally committed;
  - Git remote remains untouched.

## Context and continuity policy

- Decisions live in ADRs and this plan, not only in chat history.
- Each slice ends with tests, a short status update, and any debt recorded on disk.
- Codex context compaction is safe because the repository contains the accepted goal,
  non-goals, invariants, and next step.
- Development stays on the local-only branch `local/pve-private-xlsx-ingest` unless the
  user explicitly changes the workflow.

## Current status

- [x] Goal and non-goals accepted by the user.
- [x] Source workbooks inventoried read-only.
- [x] Local-only branch created.
- [x] Architecture boundary recorded in ADR-0008.
- [x] Slice 1 parser, staging contract, exact-byte media export, and two-workbook
  catalog merge implemented.
- [x] Slice 2 manual portrait review completed for all 619 queued formation assets,
  covering all 21,455 formation references. Final materialization records 582
  `CONFIRMED` and 37 `REVIEWED_UNKNOWN` assets across 278 exact unit variants, with no
  pending or unresolved asset. Every unconfirmed identity fails closed to the exact
  workbook-embedded portrait; no unit or six-star variant is inferred from a weak image
  candidate, an unpinned page, or material existence alone.
- [x] Slice 3 Deep Zone read-only local API/UI implemented.
- [x] Slice 4 Remembrance/Luna read-only local API/UI implemented.
- [x] Slice 5 local PVE acceptance completed for the file-backed library. The existing
  database-backed pages still require the normal Compose stack and are outside the
  lightweight PVE-only runtime used for this acceptance.

## Manual portrait review closure

All 619 candidate assets have a recorded human-review decision. Candidate similarity
only routed review; it never established identity. `CONFIRMED` requires exact
side-by-side workbook/EsterTion variant agreement plus claim-bearing, locally pinned
So-net Taiwan identity evidence. `REVIEWED_UNKNOWN` records a completed review whose
conjunctive identity/evidence gate did not close and therefore retains workbook art.
`${base}61` additionally requires exact same-base material and accepted Taiwan six-star
evidence. Final counts are 582 confirmed, 37 reviewed-unknown, and zero unresolved or
pending assets.

## Current deterministic checkpoint

| Artifact | Exact result |
|---|---|
| Workbook 1 staging | 6 sheets, 485 sections, 1,721 normalized teams, 1,756 axes, 313 assets; SHA-256 `b68dee9ae474258e78ed6f4ab0e375978fd497f3f7c04a37e7bc6ce550c3d615` |
| Workbook 2 staging | 20 sheets, 168 sections, 2,570 teams, 2,692 axes, 334 assets; SHA-256 `d93b03b906b981e1c8425e30e62ba69cef897545e5dbfe8a19b12e38919eca83` |
| Merged local catalog | 2 workbooks, 26 sheets, 653 sections, 4,291 teams, 4,448 axes, 647 assets; SHA-256 `20764c142b1798f8629155a2562bdffbed624722c2bbf87970eb530a7602f5e7` |
| Portrait candidate input | 619 queued formation assets, 21,455 references; SHA-256 `643af3c71b89f48feb7dd2ea55489c739c06e6272610f7c0acf473f40a29f049` |
| Portrait review queue | 619 reviewed formation assets; 582 `CONFIRMED`, 37 `REVIEWED_UNKNOWN`, 0 `PENDING`; SHA-256 `b41fe08c715324ab64fb22b2d06db9f9462cf6efa13f56dfca09041072248c87` |
| Reviewed portrait overrides | 619 human decisions across 278 exact variants; SHA-256 `58ae9f8b9ce0c8f0a224c9ff2be9bf655921c72aac9d4235ad8c4ead5cb8222a` |
| Character mapping manifest | 582 `RESOLVED`, 37 `REVIEWED_UNKNOWN`, 0 `UNRESOLVED`; SHA-256 `e8a118a63248fb61361209314b410b99fa2b1c8b28a502d9883918a5b7ed3ef3` |
| Derived mapped catalog | Base catalog and all Excel fallback hashes retained; SHA-256 `78017de65c86fc8455ac6f0f4d979fa9bb503eae6b6e230bd2d0a99fe22ef540` |
| Materialization sidecar | Exact base/override/EsterTion/evidence/output hashes; SHA-256 `1b073440fbd2b648e67853acbd5af4f102bdc3e288de37d99277d2a49eb81fe1` |
| Focused importer/catalog/mapping tests | 196 passed |
| Full API regression | 156 passed |
| OpenAPI/client parity | 45 schemas |
| Web verification | TypeScript PASS; Next.js production build PASS |
| PVE browser/API verification | mock-backed desktop/mobile suite 38/38; real mapped PVE desktop/mobile 6/6; final file-backed API on/off smoke read all 653 stages and 21,455 portraits; exact six-star and unresolved workbook-fallback checks passed |

The source workbook SHA-256 values remained unchanged before and after extraction.
126 reviewed assets select `${base}61` across 62 exact unit variants, covering 4,032
of 21,455 formation references. Each closes over an exact reviewed workbook identity,
exact same-variant EsterTion base and `${base}61` material, plus a pinned claim-bearing
So-net Taiwan snapshot. The evidence verifier accepts only a direct exact-name six-star
sentence, an exact item in the official grouped six-star release roster, or an exact
item in a four-signal official six-star pure-memory-piece package roster. A name in
another section or a different variant remains rejected. The remaining 456 confirmed
assets use exact `${base}31`; all 37 reviewed-unknown assets retain their exact
workbook-embedded portraits.
The real `火8!J28` alternate full-SET video is bound to the left-hand team, and any
previously unaudited run of five unconsumed portrait images now fails closed instead of
silently disappearing from the library.

## Current local acceptance instance

- Web: `http://127.0.0.1:3600/pve`
- Read-only API: `http://127.0.0.1:8600/api/v1/pve-library/stages`
- Catalog: 653 workbook sections, 4,291 teams, 4,448 operation axes, 647 exact
  workbook-embedded fallback assets, plus a derived mapping layer containing 582
  resolved and 37 fail-closed reviewed assets.
- The API and Web processes are intentionally lightweight and only guarantee the PVE
  library paths. Docker Desktop was not started, so existing database-backed pages are
  not part of this running instance.
- The isolated full-stack Compose overlay in `infra/private/compose.local-libraries.yml` uses the
  derived mapped catalog, explicitly enables the fixed-origin external icon adapter,
  and keeps the complete catalog/assets mount read-only. The application-wide feature
  default remains disabled, so only this private local overlay opts in.

The live acceptance also covers the real `火8!J28` X/Twitter plus alternate YouTube
sources, the literal `XOXOO` pattern, and the intentionally empty operation axis at
`水9!L16:S16`. A production-route bug involving encoded colon-separated stage IDs was
found by the real-catalog browser test and fixed before this checkpoint.
