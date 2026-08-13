# ADR-0008: Private PVE XLSX ingestion and external icon adapter

- Status: accepted
- Date: 2026-08-12
- Owner: Builder

## Context

The project has two user-maintained Excel workbooks that already organize Deep Zone,
Remembrance Battlefield, Luna Tower, team portraits, operation notes, and source/video
links. The project is now for the user's private local use. Publishing, GitHub delivery,
and independent clear verification are not part of this development phase.

Inputs are identified by filename and SHA-256 so that future imports are reproducible:

| Workbook | SHA-256 |
|---|---|
| `深域關卡備戰所有屬性1~7.xlsx` | `9a53ab1af4b1333d7e846e38fd84e89b35b08f6ece01f374b7db2eecae71a5f0` |
| `深域關卡8~10&追憶&露娜塔.xlsx` | `e09b3c6c4d6a6c240e40a68aa724122bfdc7ad409521c011f25db0f3e7887789` |

The workbooks contain merged cells, reused embedded portraits, hyperlinks, formulas,
hidden reference sheets, multiple operation axes for one team, and shorthand video
references. CSV or PDF conversion would lose required structure.

## Decision

1. Keep both `.xlsx` files unchanged and outside the repository. A deterministic,
   read-only importer produces normalized staging artifacts and an import report.
2. Display workbook-provided teams under the exact mode, element, area, and stage from
   the workbook. Do not independently decide whether a team can clear the stage.
3. Interpret operation markers exactly as agreed by the user:
   - `O` means `SET`.
   - `X` means `NOT_SET`.
   - A five-character marker such as `XOOOO` is one team-level operation pattern with
     five workbook display positions. `全SET` normalizes to `OOOOO`.
   - Slash/newline combinations may contain multiple operation variants. Preserve the
     raw text and the ordered parsed patterns; do not collapse them into AUTO/SEMI_AUTO.
   - The workbook explanation and visible portrait direction are not yet sufficient to
     call these positions game/member slots. Preserve the literal
     `WORKBOOK_TEXT_LEFT_TO_RIGHT` order with `member_alignment=UNRESOLVED` until the
     direction is explicitly confirmed; the UI must not overlay those states on a
     portrait before that alignment is reviewed.
   - Other operation text is preserved verbatim and normalized only when an explicit
     mapping exists.
4. Preserve provenance. A displayed team records workbook identity, sheet, cell/row
   locator, source links, and parser identity. The canonical staging artifact excludes
   run-time timestamps so repeated extraction is byte-for-byte deterministic. A
   `SOURCE_PROVIDED` label means that the
   team is reproduced from the workbook; it is not a claim of independent clear
   verification.
5. Resolve characters through a separate identity mapping:
   `canonical character -> official TW name -> exact unit variant -> external asset id`.
   Visible cards may omit names, but accessible alt text and detail views retain the
   official TW name.
6. Prefer an exact six-star portrait only when reviewed, claim-bearing So-net Taiwan
   official evidence says that the exact unit variant has six stars released and the
   exact portrait exists. EsterTion, AppMedia, GameWith, and PCRD Fans cannot establish
   Taiwan names or Taiwan six-star availability. Never substitute a base character's
   six-star portrait for a seasonal or alternate unit.
7. External game art remains behind a private/local adapter. Do not commit downloaded
   portrait binaries, mirror the external library, or add a production hotlink contract.
   The current adapter uses EsterTion only as a replaceable exact JP unit-name/ID index
   and portrait-existence provider. An unresolved mapping retains the exact
   workbook-embedded portrait; only a missing or corrupt workbook asset renders a
   deterministic placeholder.
8. Video presentation uses source cards and click-to-load playback where supported.
   Do not download or re-upload videos. Resolve workbook shorthand such as `#1`, `#2`,
   and `#3` as workbook-defined source aliases. Do not inherit a URL from a previous
   row when an alias has no exact locator.
9. Existing canonical research rows are not overwritten by bulk spreadsheet ingestion.
   The staging layer has explicit ownership and only promotes data through a reviewed,
   deterministic mapping step.
10. Keep workbook content out of the existing Evidence-first `/api/v1/stages`, Team,
    Guide, and Gate contracts. A later walking slice uses an additive local
    `/api/v1/pve-library` namespace and `/pve/library/...` pages. This preserves the
    difference between `SOURCE_PROVIDED` display data and independently verified teams.
11. Slice 1 is file staging only and requires no migration. If the library later needs a
    database projection, use an additive local-owned schema; do not include its rows in
    existing canonical BaselineCounts or Gate calculations.
12. This phase is local-only. Do not commit, push, open pull requests, create tags, or
    otherwise publish to GitHub unless the user explicitly changes this decision later.

A manual decision is not by itself sufficient to publish an external icon. `CONFIRMED`
requires exact side-by-side workbook/EsterTion variant agreement and claim-bearing,
locally pinned So-net Taiwan identity evidence. A reviewed asset that lacks any
conjunct is `REVIEWED_UNKNOWN` and continues to serve workbook art.

Six-star evidence must be one of: a direct exact-name official release sentence; an
exact item in an official grouped six-star roster; or an exact item in an official
package roster whose title, product, contents, and eligible roster jointly prove
six-star pure-memory-piece use. Search snippets, inline co-occurrence, generic So-net
shells, redirects, and evidence for another variant fail closed.

## Source authority matrix

The user supplied the following external references on 2026-08-12. They have distinct
authority and must not be blended into one undifferentiated source:

| Source | Accepted use | Must not establish |
|---|---|---|
| [So-net Taiwan official news](https://www.princessconnect.so-net.tw/news) | Exact Taiwan display name and exact-variant Taiwan release evidence, saved locally, SHA-256 pinned, and accepted by the semantic verifier | JP asset identity by name similarity alone |
| [EsterTion image archive](https://redive.estertion.win/) | Pinned JP technical name/base lookup and existence of an exact six-digit unit icon (`${base}31` or `${base}61`) | Taiwan display name, Taiwan availability, or Taiwan six-star release; material existence alone proves none of these |
| [AppMedia arena tool](https://appmedia.jp/priconne-redive/4466131) | Manually opened secondary arena research and user-provided outbound reference | Official identity, Taiwan release truth, independent clear verification, or bulk team ingestion |
| [PCRD Fans](https://www.pcrdfans.com/en/battle) | Manually opened community arena research and user-provided outbound reference | Official identity, Taiwan release truth, independent clear verification, or bulk team ingestion |
| [GameWith Princess Connect guide](https://gamewith.jp/pricone-re/) | Manually opened JP guide context and a locator for later source-specific research | Automatic Taiwan applicability, merged operation truth, or bulk guide ingestion |

The character portrait gate therefore remains conjunctive: exact visual variant
agreement, an explicit exact EsterTion base with the same JP variant name, claim-bearing
Taiwan official exact-name identity evidence, and existing exact `${base}31` material are
all required before an external icon can replace the workbook image. Six-star
additionally requires exact same-base `${base}61` material and one accepted So-net
six-star evidence form: direct exact-name sentence, grouped roster, or the four-signal
package roster described above. Any missing or conflicting condition keeps the workbook
image. AppMedia, PCRD Fans, and GameWith remain locator-preserving secondary strategy
research only. They cannot populate this XLSX-backed library, establish official Taiwan
identity or release state, or independently prove that a workbook team clears content.
Arena research remains outside this decision's current scope.

## Consequences

- The user can browse the full workbook collection without waiting for independent
  gameplay verification.
- Import correctness is still testable: stages, team counts, portrait order, operation
  markers, links, and locators must reconcile with the source workbooks.
- Content truth and independent clear verification remain distinct concepts.
- Asset availability or licensing uncertainty cannot block data ingestion, because the
  workbook portrait remains the deterministic fallback, the UI has a final placeholder
  path for missing/corrupt workbook assets, and the icon provider is replaceable.
- The private library uses a separate read-only file-backed API namespace, so Deep Zone,
  Remembrance Battlefield, and Luna Tower require no serving-database migration and do
  not change canonical materialization or Gate counts.
- Completing manual review of all 619 queued assets does not force 619 external icons:
  fail-closed decisions remain workbook-backed, explicit, and auditable.
- Mutable runtime counts and artifact hashes are recorded in the operations plan's
  deterministic checkpoint rather than duplicated in this ADR.

## Reversibility

Easy. Disable the local XLSX content source and icon adapter, then return to the existing
canonical PVE projection. The source workbooks and existing canonical data remain
unchanged.
