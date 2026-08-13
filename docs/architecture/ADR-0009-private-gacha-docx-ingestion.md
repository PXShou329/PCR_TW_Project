# ADR-0009: Private Gacha forecast DOCX ingestion

- Status: Accepted for the local walking slice
- Date: 2026-08-13

## Context

The user supplied `卡池未來視.docx` as the prepared data source for the private Gacha
future-sight view.  The document contains 17 ordered forecast blocks and 17 embedded JP
pool screenshots.  Its exact SHA-256 is
`0600faf911747c6df1a98afddfe1fe8e5af585ff72af11e2d34299f5e70c4cfe`.

The document is useful private input, but it is not a Taiwan official schedule.  It has
no source URL, official Evidence/Claim closure, stable pool ids, timezone, or date-boundary
semantics.  Its character labels also contain mixed parentheses and spelling variants.
The screenshots show JP dates that differ from the document's Taiwan forecasts.

The existing canonical Gacha closure must therefore remain unchanged: five timeline
events, four community sources, zero contributing community relations, and `MODEL_ONLY`
for every current event.  This DOCX is a user-curated derivative of the already registered
`GACHA-COMM-002`; it is not a fifth independent source.

## Decision

1. The DOCX is read-only private input.  The original file and its embedded images are
   not rewritten, committed, publicly mirrored, or counted as a new independent community source.
   One exact-byte, content-addressed copy may be retained under gitignored local runtime
   storage so later parser replays do not depend on the Downloads directory.
2. A standard-library OOXML parser reads paragraph text and drawing relationships offline.
   Production ingestion does not require Pandoc, Word, OCR, or network access.
3. The parser emits `gacha-community-docx-candidates/v1` canonical JSON into gitignored
   runtime storage.  The artifact contains exact source/media hashes and stable paragraph
   locators but no absolute paths or extraction timestamps.
4. The document's names remain `raw_character_names` with
   `identity_status=UNVERIFIED_COMMUNITY_NAME`.  Half-width/full-width punctuation may be
   recognized for token boundaries, but Chinese text is not corrected, fuzzily matched,
   translated, or promoted to `tw_name`.
5. The document's date lines are preserved as community forecasts with `precision=DAY`
   and `date_boundary_semantics=SOURCE_UNSPECIFIED`.  The pool type is likewise stored as
   `source_declared_pool_kind`, not the canonical official `limited_status`.  These fields
   are not official Taiwan facts and do not modify `41_GACHA_TIMELINE.csv`.
6. Embedded images are provenance-only.  Image bytes and relationships are hashed; image
   text is never OCRed into Taiwan dates or names.
7. Every initial candidate is `PENDING`, `promotion_eligible=false`, has no proposed event
   id, and contributes zero canonical writes.  Event linkage requires a later explicit
   human-review registry bound to the document, candidate, and image hashes.
8. Comments, tracked changes, tables, macros, external images, missing image parts, unsafe
   ZIP paths, invalid/reversed dates, implicit cross-year ranges, and non-explicit pool
   kinds fail closed before output replacement.
9. The local walking slice exposes the staged artifact through a separate read-only,
   file-backed API at `/api/v1/gacha-library/forecasts` and content-addressed image
   assets at `/api/v1/gacha-library/assets/{sha256}`.  Runtime loading replays the same
   deterministic parser with the fixed `GACHA-COMM-002` source id and requires the
   canonical replay bytes to equal the configured candidate JSON exactly.
10. `/gacha` renders these observations in a clearly labeled `私人文件預測／非官方`
    section.  It does not replace or merge into the independently rendered canonical
    timeline.  Failure of the private API therefore leaves the public timeline usable.
11. The same-origin Web proxy only forwards the exact forecasts route or a lowercase
    64-hex asset path.  Redirects, SVG, non-JSON upstream errors, and every image MIME
    other than JPEG, PNG, or WebP fail closed.
12. This slice adds no migration, DB write, canonical manifest change, scheduler job,
    event relation, or automatic publication path.

## Current deterministic checkpoint

| Item | Exact result |
|---|---|
| Source DOCX | 2,102,864 bytes; SHA-256 `0600faf911747c6df1a98afddfe1fe8e5af585ff72af11e2d34299f5e70c4cfe` |
| Runtime source snapshot | Exact-byte copy under `.runtime/gacha_forecast/source/`; hash and length equal the source; gitignored |
| Document shape | 80 body paragraphs; 0 tables/comments/tracked changes; 17 embedded JPEGs |
| Candidate result | 17 pools; 39 raw character labels; 13 distinct date windows; coverage 2026-08-01 through 2026-12-01 |
| Pool types | 10 `LIMITED_PICKUP`; 6 `RERUN`; 1 `PERMANENT_PICKUP` |
| Initial review state | 17 `PENDING`; 0 proposed event links; 0 canonical writes |
| Parser warning | One `UNQUOTED_CHARACTER_SEQUENCE` in pool 13; still review-blocked |
| Candidate JSON | 19,215 bytes; SHA-256 `beb41b049f995c5894219e78a883f23430f782b47699b0d4e8fdd234aefed79c` |
| Private API | 17 forecasts and 17 content-addressed JPEG assets; fixed source and independence group `GACHA-COMM-002` |
| Web presentation | Private non-official section on `/gacha`; canonical five-event timeline remains independent |

Two consecutive real-document extractions produced the same candidate bytes and hash.
The source DOCX hash remained unchanged.

## Consequences and next slice

- The private application can safely use this document without weakening the canonical
  research timeline or pretending that community labels are official Taiwan names.
- The private UI can now show the exact source text, forecast intervals, parser warnings,
  and embedded images without promoting any observation into canonical research data.
- The next slice may add a strict human-review registry for exact event linkage.  It must
  be bound to the document, candidate, and image hashes and must preserve raw names rather
  than silently correcting them.
- If a future reviewed observation is linked to an event, observation count and sources
  contributing to the final interval must remain separate.  A single D-grade day forecast
  cannot create community day-level consensus or force `MODEL_PLUS_COMMUNITY`.
- Removing the two Gacha paths from the local API configuration, or deleting the
  gitignored runtime artifact, fully rolls back this slice; no database or canonical
  research state is involved.
