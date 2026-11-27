# The vocabulary of the ITU-T

## The study periods

The ITU-T works in study periods of three or four years. They are a closed
list — a period that does not exist cannot be constructed.

| Period | DMS code |
| ------ | -------- |
| 2005-2008 | `T05` |
| 2009-2012 | `T09` |
| 2013-2016 | `T13` |
| 2017-2020 | `T17` |
| 2022-2024 | `T22` |
| 2025-2028 | `T25` |
| 2029-2032 | `T29` |

Note the exception: the period 2022-2024 spans three years, because the period
that was to start in 2021 was postponed. A year therefore does not always
identify a period by its end — the code of a document identifier is looked up
in the list, never computed.

In the Python API: `StudyPeriod.current()`, `StudyPeriod.all()`,
`StudyPeriod.from_year(2025)` (the period that *starts* in that year),
`StudyPeriod.containing(2026)` (the period that *contains* it) and
`StudyPeriod.parse("2025-2028")` or `StudyPeriod.parse("2025")`.

## The study groups

A study group is a number: 2, 3, 5, 11, 12, 13, 15, 17, 20, 21 in the period
2025-2028. The DMS writes them with two digits (`SG02`, `SG12`) and the
identifiers carry the plain number.

The study groups change from period to period: SG9 and SG16 existed in
2022-2024 and were replaced by SG21 in 2025-2028. Read the groups of a period
from the catalogue (`itu-t-documents study-groups -p 2025-2028`), never from a
list in the code.

## The questions and the working groups

A question belongs to a study group and is written `Q<number>/<group>`:
`Q5/12` is the question 5 of study group 12.

Each question sits in a working group:

| Code | Meaning |
| ---- | ------- |
| `PLEN` | The plenary — the question is handled by the study group itself. |
| `WP1/12` | Working group 1 of study group 12. |

The people of a question are its rapporteurs: the rapporteur, the
co-rapporteurs and the associate rapporteurs, plus the editor and the
contributors. A question of the ITU-T is not the same thing as a question of
the package — the package reads them from the ITU-T.

## The meetings

A meeting is identified by its code: `270119` is the meeting that started on
the 19th of January 2027. The code is what `sync` and `documents --meeting`
expect.

```text
270119  Geneva, 19 January - 27 January 2027
261015  E-Meeting, 15 October 2026
```

`MeetingId.from_code("270119")` builds the meeting, `meeting.code` and
`meeting.label` read it back.

## The document identifiers

The identifier of a document is its address in the DMS:

```text
T25-SG12-C-0192                 a contribution of study group 12
T25-SG12-261015-TD-GEN-0520      a temporary document of the meeting 261015
T25-SG02-C-0001!R1!MSW-E.docx   the first revision of a document
```

| Part | Meaning |
| ---- | ------- |
| `T25` | The study period (`T25` = 2025-2028). |
| `SG12` | The study group. |
| `261015` | The meeting, when the document belongs to one. |
| `C` | The type: `C` contribution, `TD` temporary document, `COL` collective letter, `R` report. |
| `0192` | The number. |
| `GEN` | The sub-type of a temporary document. |
| `!R1!` | The revision number. |

Never reformat an identifier. `DocumentRef.parse()` builds the object,
`ref.document_id` gives the string back unchanged, `ref.display_number` the
number as the ITU-T writes it (`0520`).

The numbers are not consecutive: a withdrawn document leaves a hole, so
`T25-SG13-C-0669` does not exist between `C-0668` and `C-0670`. A number does
not prove that a document exists.

## The formats and the languages

| Format | Value | File |
| ------ | ----- | ---- |
| Word | `MSW` | `.doc` or `.docx` |
| PDF | `PDF` | `.pdf` |
| ZIP | `ZIP` | `.zip` |
| HTML | `HTM` | `.htm` |

| Language | Value |
| -------- | ----- |
| English | `E` |
| French | `F` |
| Spanish | `S` |
| Arabic | `A` |
| Chinese | `C` |
| Russian | `R` |

A document is published in the format it was submitted in: `T25-SG12-C-0192`
exists as MSW only, and asking for a PDF of it fails with a message that the
document is not available in that format and language. A revision may exist in
more languages than the original.

## The visibility

| Value | Meaning |
| ----- | ------- |
| `pub` | Public — the metadata is readable without an account. |
| `ties` | Protected by the TIES access control. |
| `inf` | Internal. |

## The caches

| What | Where |
| ---- | ----- |
| The metadata store | `~/.cache/itu-t-documents/metadata.db` (SQLite) |
| The HTTP cache | `~/.cache/itu-t-documents/http-cache.sqlite` (hishel) |
| The downloaded files | `~/.cache/itu-t-documents/files/` |

Everything that was seen stays there and is answerable without a login.
`ITU_CACHE_DIR` moves the whole directory.

## The rules of the DMS that the package follows

- The meeting pages are ISO-8859-1 and declare no charset — they are decoded
  as such. The `net4` pages are UTF-8.
- The listings are paginated. The page size is set with the `ITUDMS_PageSize`
  cookie, and the `Next` link of every page is followed, because the
  contributions of a study period span more than one page.
- The listings report their size. A listing that holds fewer documents than
  it reports is refused (`IncompleteListingError`) instead of being stored as
  if it were complete.
- The aggregate listing of the temporary documents of a meeting previews five
  documents per sub-type. The listing of every sub-type is read, never the
  aggregate one alone: the meeting `T25-SG13-250303` holds 549 temporary
  documents in six sub-types, the aggregate listing shows 30 rows.
- The TIES login is a four step SAML handshake. The session cookie lives in
  the HTTP client, one login serves every later request.
