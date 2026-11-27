---
title: The command line
---

Every command of the package is available as `itu-t-documents <command>`.
Run `itu-t-documents --help` for the list and
`itu-t-documents <command> --help` for the details of one command.

## The options

Most commands take the same options:

| Option | Meaning | Default |
|--------|---------|---------|
| `--study-group`, `-g` | The study group, e.g. `12` | `12` |
| `--study-period`, `-p` | The study period, e.g. `2025-2028` or `2025` | `2025-2028` |
| `--meeting`, `-m` | A meeting, given by its DMS code, e.g. `270119` | every meeting |
| `--type` | The document type: `TD`, `C`, `COL` or `R` | every type |
| `--question`, `-q` | A question number, e.g. `5` for `Q5/12` | every question |
| `--source`, `-s` | A submitting organisation; the match is partial | every source |
| `--limit`, `-l` | The maximum number of results | no limit |

The options can also be set in the environment, which is handy when you work
on one study group all the time:

```bash
export ITU_T_DOCUMENTS_STUDY_GROUP=13
export ITU_T_DOCUMENTS_STUDY_PERIOD=2025-2028
export ITU_T_DOCUMENTS_MEETING=270119
export ITU_T_DOCUMENTS_OUTPUT_FILE=~/Documents/itu
```

## The structure of the ITU-T

These commands read the structure of the ITU-T. They need no account.

### `periods`

```bash
itu-t-documents periods
```

```text
2005-2008    T05   net4 index 13
2009-2012    T09   net4 index 14
2013-2016    T13   net4 index 15
2017-2020    T17   net4 index 16
2022-2024    T22   net4 index 17
2025-2028    T25   net4 index 18 (current)
2029-2032    T29   net4 index 19
```

The study periods are a closed list: the ITU-T publishes them, and a period
that does not exist cannot be built. See
[the catalogue](catalogue.md).

### `study-groups`

The study groups of a period. They change from period to period, so they are
read from the ITU-T.

```bash
itu-t-documents study-groups --study-period 2022-2024
```

```text
SG02   SG02 (2022-2024)
SG03   SG03 (2022-2024)
SG05   SG05 (2022-2024)
SG09   SG09 (2022-2024)
...
```

### `structure`

The plenary, the working groups, the questions under study and the other
groups of a study group.

```bash
itu-t-documents structure --study-group 12
```

```text
PLEN         plenary
WP1/12       Terminals and multimedia subjective assessment
WP2/12       Objective models and tools for multimedia quality
WP3/12       Multimedia QoS and QoE
Q1/12        SG12 work programme and quality of service/quality of experience
Q5/12        Telephonometric methodologies for handset and headset terminals
SG12RG-AFR   ITU-T SG12 Regional Group for Africa
```

### `search`

Search the working groups, the questions and the other groups of a period.

```bash
itu-t-documents search --search speech
```

```text
question         Q15/12         Parametric and E-model-based planning, prediction and monitoring ...
question         Q4/12          Objective methods for speech and audio evaluation in vehicles ...
question         Q6/12          Analysis methods for speech and audio using complex measurement signals ...
```

## The documents

### `meetings`

The meetings of a study group.

```bash
itu-t-documents meetings --study-group 12
```

```text
270119  Geneva     2027-01-19 2027-01-27
261015  E-Meeting  2026-10-15 2026-10-23
260609  Geneva     2026-06-09 2026-06-17
```

### `questions`

The questions under study, with their working group and their rapporteurs.

```bash
itu-t-documents questions --study-group 12
```

### `sync`

Fetch the documents of a meeting and store them in the local database.

```bash
itu-t-documents sync --study-group 12 --meeting 260609
```

```text
260609: 276 documents
276 documents stored in /home/you/.cache/itu-t-documents/metadata.db
```

Without `--meeting` every meeting of the study group is synchronised, which
takes a while — a meeting of a busy study group holds several hundred
documents.

`--type` narrows the run to one document type:

```bash
itu-t-documents sync --study-group 13 --meeting 250303 --type TD
```

The temporary documents of a meeting are read per sub-type, because the
aggregate listing of the ITU-T only previews five documents per sub-type.

### `documents`

Search the documents that were stored. It never touches the network — it
answers from the local database.

```bash
itu-t-documents documents --study-group 12 --question 5
itu-t-documents documents --study-group 12 --source "TU Berlin"
itu-t-documents documents --study-group 12 --type C --limit 20
```

```text
T25-SG12-260609-TD-GEN-0467   TD   Q4,5,6,7,10 Executive Summary of the Working Party 1/12 Meeting  Chair WP1/12
```

The columns are the identifier, the type, the questions, the title and the
sources.

### `download`

Download a document. This needs TIES credentials, unless the document was
downloaded before.

```bash
itu-t-documents download --document T25-SG12-C-0192 --format PDF
itu-t-documents download --document T25-SG12-261015-TD-GEN-0520 --format MSW --language E
itu-t-documents download --document T25-SG12-C-0192 --format PDF --output-file ~/contribution.pdf
```

| Option | Values | Default |
|--------|--------|---------|
| `--document` | The DMS identifier | required |
| `--format` | `PDF`, `MSW` (Word), `ZIP`, `HTM` | `PDF` |
| `--language` | `E`, `F`, `S`, `A`, `C`, `R` | `E` |
| `--output-file`, `-o` | A path to write to | the cache |

Without `--output-file` the document is written into the file cache. The
package picks the rendition that matches the format and the language, and it
prefers the original over a revision.

## The accounts and the server

### `auth`

Check whether the TIES credentials are configured and usable.

```bash
itu-t-documents auth
```

```text
TIES login succeeded.
```

### `mcp`

Run the MCP server over stdio, for an AI agent.

```bash
itu-t-documents mcp
```

See [the MCP server](mcp.md).
