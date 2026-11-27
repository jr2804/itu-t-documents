---
title: The command line
---

Every command of the package is available as `itu-t-documents <command>`.
Run `itu-t-documents --help` for the list and
`itu-t-documents <command> --help` for the details of one command. Without a
command the tool prints a two-line reminder; `itu-t-documents default` prints
the same text, `itu-t-documents --version` prints the installed version, and
`--install-completion` installs shell completion for the commands.

A command that fails prints one line on standard error and exits 1:

```text
itu-t-documents: T25-SG12-C-0192 is not available as PDF-E
```

A usage error — an unknown option, a missing argument or a value outside the
choices — exits 2 before the command runs.

## The options

Most commands take the study group and the study period. The filters of
`documents` apply to the local database, not to the network:

| Option | Commands | Meaning | Default |
|--------|----------|---------|---------|
| `--study-group`, `-g` | most | The study group, e.g. `12` | `12` |
| `--study-period`, `-p` | most | The study period, e.g. `2025-2028` or `2025` | the current period; `documents`: every period |
| `--meeting`, `-m` | `sync`, `documents` | The DMS code of a meeting, e.g. `270119` | `sync`: every meeting; `documents`: no filter |
| `--type` | `sync`, `documents` | `TD`, `C`, `COL` or `R` | `sync`: `C` and `TD`; `documents`: every type |
| `--question`, `-q` | `documents` | A question number, e.g. `5` for `Q5/12` | every question |
| `--source`, `-s` | `documents` | A submitting organisation; the match is partial | every source |
| `--last-meetings` | `top-sources` | How many of the most recent stored meetings to count | `3` |
| `--limit`, `-l` | `documents`, `top-sources` | The maximum number of results | `documents`: no limit; `top-sources`: `10` |

### What needs the network

| Command | Answers from | Account |
|---------|--------------|---------|
| `periods`, `study-groups`, `structure`, `search`, `questions`, `meetings` | The ITU-T pages, through the HTTP cache | none |
| `sync` | The ITU-T listings, into the metadata store | none |
| `documents`, `top-sources` | The metadata store only | none |
| `download` | The file cache, then the ITU-T | TIES, unless the file is cached |
| `auth` | The TIES login | TIES |
| `mcp` | Every source above, per tool | TIES only for `download_document` |

The options can also be set in the environment, which is handy when you work
on one study group all the time:

```bash
export ITU_T_DOCUMENTS_STUDY_GROUP=13
export ITU_T_DOCUMENTS_STUDY_PERIOD=2025-2028
export ITU_T_DOCUMENTS_MEETING=270119
export ITU_T_DOCUMENTS_OUTPUT_FILE=~/Documents/itu-contribution.pdf
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
SG11   SG11 (2022-2024)
SG12   SG12 (2022-2024)
SG13   SG13 (2022-2024)
SG15   SG15 (2022-2024)
SG16   SG16 (2022-2024)
SG17   SG17 (2022-2024)
SG20   SG20 (2022-2024)
```

### `structure`

The plenary, the working groups, the questions under study and the other
groups of a study group.

```bash
itu-t-documents structure --study-group 12
```

<pre><code>PLEN         plenary
WP1/12       Terminals and multimedia subjective assessment
WP2/12       Objective models and tools for multimedia quality
WP3/12       Multimedia QoS and QoE
Q1/12        SG12 work programme and quality of service/quality of experience (QoS/QoE) coordination in ITU-T Continuation of Q1/12
Q2/12        Definitions, guides and frameworks related to quality of service/quality of experience (QoS/QoE) Continuation of Q2/12
Q4/12        Objective methods for speech and audio evaluation in vehicles Continuation of Q4/12
Q5/12        Telephonometric methodologies for handset and headset terminals Continuation of Q5/12
Q6/12        Analysis methods for speech and audio using complex measurement signals Continuation of Q6/12
Q7/12        Methodologies, tools and test plans for the subjective assessment of speech, audio and audiovisual quality interactions Continuation of Q7/12
Q10/12       Conferencing and telemeeting assessment Continuation of Q10/12
Q9/12        Perceptual-based objective methods and corresponding evaluation guidelines for voice and audio quality measurements in telecommunication services Continuation of Q9/12
Q14/12       Development of models and tools for multimedia quality assessment of packet-based video services Continuation of Q14/12
Q15/12       Parametric and E-model-based planning, prediction and monitoring of conversational speech and audio-visual quality Continuation of Q15/12
Q19/12       Objective and subjective methods for evaluating perceptual audiovisual quality in multimedia and television services Continuation of Q19/12
Q12/12       Operational aspects of telecommunication network service quality and end-to-end performance considerations Continuation of Q12/12
Q13/12       Quality of experience (QoE), quality of service (QoS) and performance requirements and assessment methods for multimedia applications Continuation of Q13/12
Q17/12       Performance of packet-based networks and other networking technologies Continuation of Q17/12
Q20/12       Perceptual and field assessment principles for quality of service (QoS) and quality of experience (QoE) of digital financial services (DFS) Continuation of Q20/12
SG12RG-AFR   ITU-T SG12 Regional Group for Africa
SG12RG-AMR   ITU-T SG12 Regional Group for the Americas
SG12RG-AP    ITU-T SG12 Regional Group for Asia and the Pacific
IRG-AVQA     ITU Intersector Rapporteur Group Audiovisual Quality Assessment
QSDG         Quality of Service Development Group
</code></pre>

The order is the order of the catalogue, not numeric order: `Q10/12` comes
before `Q9/12`, and the regional groups follow the questions.

### `search`

Search the working groups, the questions and the other groups of a period.

```bash
itu-t-documents search --search speech
```

<pre><code>question         Q15/12         Parametric and E-model-based planning, prediction and monitoring of conversational speech and audio-visual quality Continuation of Q15/12
question         Q4/12          Objective methods for speech and audio evaluation in vehicles Continuation of Q4/12
question         Q6/12          Analysis methods for speech and audio using complex measurement signals Continuation of Q6/12
question         Q7/12          Methodologies, tools and test plans for the subjective assessment of speech, audio and audiovisual quality interactions Continuation of Q7/12
</code></pre>

The match is a case-insensitive substring of the code or the title, and the
result is sorted by kind and then by code — which is why `Q15/12` comes before
`Q4/12`.

## The documents

### `meetings`

The meetings of a study group.

```bash
itu-t-documents meetings --study-group 12
```

```text
270119  Geneva, 19 January - 27 January 2027
261015  E-Meeting, 15 October 2026
260609  Geneva, 09 June - 17 June 2026
250909  Geneva, 09 September - 18 September 2025
250325  E-Meeting, 25 March 2025
250114  Geneva, 14 January - 23 January 2025
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
260609: 0 documents
0 documents stored in /home/you/.cache/itu-t-documents/metadata.db
```

The count is what this run added, not what the store holds: the 191 documents
of the meeting were already there, so the second run adds nothing. On an empty
store the first run adds them.

Without `--meeting` every meeting of the study group is synchronised, which
takes a while — a meeting of a busy study group holds several hundred
documents. The command also reads the period-wide listing of the study group,
because a document can be posted between meetings and so belong to no meeting
listing. A run that adds such documents prints a line of its own — this is
the measured SG15 period listing on 27 November 2026:

```text
the period listing: 11 documents
```

The documents of that listing are stored without a meeting.

Without `--type`, `sync` reads contributions (`C`) and temporary documents
(`TD`), the two types a meeting is made of:

```bash
itu-t-documents sync --study-group 13 --meeting 250303 --type TD
```

The temporary documents of a meeting are read per sub-type, because the
[aggregate listing of the ITU-T](reference/itu-dms.md#the-aggregate-listing-of-the-temporary-documents)
only previews five documents per sub-type.

### `documents`

Search the documents that were stored. It never touches the network — it
answers from the local database.

```bash
itu-t-documents documents --study-group 12 --source "TU Berlin"
```

```text
T25-SG12-C-0192                  C    Q7          Proposal for a machine-learning speech dataset for subjectiv   Technische Universität Berlin (TU Berlin
T25-SG12-C-0189                  C    Q9          Draft Recommendation P.SAMD                                    Technische Universität Berlin (TU Berlin
T25-SG12-C-0174                  C    Q7          Crowdsourced speech data in objective quality prediction and   Technische Universität Berlin (TU Berlin
T25-SG12-C-0158                  C    Q9          Robustness of Speech Quality Models to Pause Manipulation: P   Technische Universität Berlin (TU Berlin
T25-SG12-C-0126                  C    Q7          Proposal for an update of ITU-T Rec. P.85                      Technische Universität Berlin (TU Berlin
T25-SG12-C-0125                  C    Q7,15,12    Text quality assessment and prediction File replaced to upda   Technische Universität Berlin (TU Berlin
```

The columns are the identifier, the type, the questions, the title and the
sources. The title is cut at 60 characters and the source at 40, which is why
the last column ends in `(TU Berlin` — the cut is the command's, not a typo.

`--question`, `--type`, `--meeting` and `--limit` narrow the same query.
Without a filter the command prints every stored document, newest number
first.

> **Known limitation.** The metadata store currently applies `--meeting` as
> the whole study group: the option is accepted, but every stored document of
> the group is returned. `sync --meeting` is not affected. Until the store is
> fixed, filter the printed identifiers instead.

### `top-sources`

Show the sources that submitted the most documents to the most recent stored
meetings. It answers from the metadata store, so run `sync` first.

```bash
itu-t-documents top-sources --study-group 12 --last-meetings 3 --limit 5
```

```text
    28  TSB
    20  ITU-T Study Group 13
    19  ITU-T Study Group 12
    16  ITU-T Study Group 21
    14  ITU-T Study Group 11
```

The count covers contributions and temporary documents. The command counts
only meetings that are already stored; `--last-meetings` selects the three
most recent of them.

### `download`

Download a document. This needs TIES credentials, unless the document was
downloaded before.

```bash
itu-t-documents download T25-SG12-R-0001 --format MSW
itu-t-documents download --document T25-SG12-C-0192 --format MSW --output-file ~/contribution.docx
```

| Option | Values | Default |
|--------|--------|---------|
| `DOCUMENT`, `--document` | The DMS identifier, as the only positional argument or as an option | required |
| `--format` | `PDF`, `MSW` (Word), `ZIP`, `HTM` | `PDF` |
| `--language` | `E`, `F`, `S`, `A`, `C`, `R` | `E` |
| `--output-file`, `-o` | A path to write to | the cache |

Without `--output-file` the document is written into the file cache. The
package picks the rendition that matches the format and the language, and it
prefers the original over a revision.

Not every document is published in every rendition. `T25-SG12-C-0192` has no
PDF, for example — it is `MSW-E` only. When the requested rendition does not
exist the command names it instead of writing an empty file:

```text
itu-t-documents: T25-SG12-C-0192 is not available as PDF-E
```

## The accounts and the server

### `auth`

Check whether the TIES credentials are configured and usable.

```bash
itu-t-documents auth
```

```text
TIES login succeeded.
```

Without credentials the command fails like every other command:

```text
itu-t-documents: no TIES credentials configured; set ITU_TIES_USERNAME and ITU_TIES_PASSWORD or store them in /home/you/.config/itu-t-documents/config.toml
```

### `mcp`

Run the MCP server over stdio, for an AI agent.

```bash
itu-t-documents mcp
```

See [the MCP server](mcp.md).
