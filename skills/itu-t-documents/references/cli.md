# The command line

```bash
itu-t-documents [OPTIONS] COMMAND [ARGS]
```

The command is installed with the package. `uvx itu-t-documents ...` runs it
without an installation.

Every option has an environment variable: `ITU_TIES_USERNAME`,
`ITU_TIES_PASSWORD`, `ITU_CACHE_DIR`, `ITU_CONFIG_DIR`, `ITU_TIMEOUT`,
`ITU_MAX_CONCURRENCY`, `ITU_USER_AGENT`, `ITU_VERIFY_TLS`, and one per
argument (`ITU_T_DOCUMENTS_STUDY_GROUP`, `ITU_T_DOCUMENTS_STUDY_PERIOD`,
`ITU_T_DOCUMENTS_MEETING`, `ITU_T_DOCUMENTS_OUTPUT_FILE`).

## The commands

| Command | What it does |
| ------- | ------------ |
| `default` | A short introduction to the ITU-T documents. |
| `periods` | The study periods the ITU-T knows. |
| `study-groups` | The study groups of a study period. |
| `structure` | The structure of a study group: plenary, working groups, questions. |
| `questions` | The questions under study of a study group. |
| `search` | The working groups, questions and other groups that match a text. |
| `meetings` | The meetings of a study group. |
| `sync` | Fetches the documents of a meeting into the local database. |
| `documents` | Searches the documents in the local database. |
| `download` | Downloads one document. |
| `auth` | Checks whether the TIES credentials are configured and usable. |
| `mcp` | Runs the MCP server over stdio. |
| `--version` | The version of the package. |
| `--install-completion` | Installs the shell completion. |

## The catalogue: what the ITU-T has

These commands read the structure of the ITU-T. They need the network, not
credentials.

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

```bash
itu-t-documents study-groups -p 2025-2028
```

```text
SG02   SG02 (2025-2028)
SG03   SG03 (2025-2028)
SG05   SG05 (2025-2028)
SG11   SG11 (2025-2028)
SG12   SG12 (2025-2028)
SG13   SG13 (2025-2028)
SG15   SG15 (2025-2028)
SG17   SG17 (2025-2028)
SG20   SG20 (2025-2028)
SG21   SG21 (2025-2028)
```

```bash
itu-t-documents structure -g 12 -p 2025-2028   # the whole structure of SG12
itu-t-documents questions -g 12 -p 2025-2028
```

```text
Q1/12    PLEN       SG12 work programme and quality of service/quality of experience (QoS/QoE) coordination in ITU-T
         Seong-Ho JEONG (Co-rapporteur)
Q2/12    PLEN       Definitions, guides and frameworks related to quality of service/quality of experience (QoS/QoE)
         Malick SYLLA (Rapporteur)
Q4/12     WP1/12     Objective methods for speech and audio evaluation in vehicles
         Jan REIMES (Rapporteur)
```

```bash
itu-t-documents search speech -p 2025-2028    # working groups, questions, other groups
```

## The meetings and the documents

```bash
itu-t-documents meetings -g 12 -p 2025-2028
```

```text
270119  Geneva, 19 January - 27 January 2027
261015  E-Meeting, 15 October 2026
260609  Geneva, 09 June - 17 June 2026
250909  Geneva, 09 September - 18 September 2025
250325  E-Meeting, 25 March 2025
250114  Geneva, 14 January - 23 January 2025
```

The first column is the meeting code. `sync` and `documents --meeting` take it.

```bash
itu-t-documents sync -g 12 -m 260609            # store the documents of the meeting
itu-t-documents sync -g 12 -m 260609 --type TD  # only the temporary documents
```

`--type` is `TD` (temporary document), `C` (contribution), `COL` (collective
letter) or `R` (report). Without it, `sync` fetches the contributions and the
temporary documents.

```bash
itu-t-documents documents -g 12 -q 5             # the documents of question 5
itu-t-documents documents -g 12 -m 260609
itu-t-documents documents -g 12 -s "Company Ltd."  # the source, matched partially
itu-t-documents documents -g 12 --type C -l 20   # at most 20 contributions
itu-t-documents documents -g 12 -p 2025-2028     # only one study period
```

`documents` reads the **local database**. Without a `sync` it answers from
what was stored before — that is the point of the cache, but a meeting that
was never synced is unknown to it.

## The download

```bash
itu-t-documents download T25-SG12-C-0192 --format MSW -o /tmp/doc.docx
itu-t-documents download T25-SG12-C-0192 --format MSW --language F
```

| Option | Meaning |
| ------ | ------- |
| `--document` | The document identifier, e.g. `T25-SG12-261015-TD-GEN-0520`. Required. |
| `--format` | `PDF`, `MSW` (Word), `ZIP` or `HTM`. Default `PDF`. |
| `--language` | `E` (English), `F` (French), `S` (Spanish), `A` (Arabic), `C` (Chinese), `R` (Russian). Default `E`. |
| `--output-file` | Where to write the file. The default is the cache of the package. |

The download needs TIES credentials, unless the file is already in the cache.
The format and the language must exist for the document: it is published in
the format it was submitted in, and a revision may exist in more languages
than the original.

## The credentials

```bash
itu-t-documents auth
```

```text
No TIES credentials found.
Set ITU_TIES_USERNAME and ITU_TIES_PASSWORD, or store them in /home/you/.config/itu-t-documents/config.toml.
```

The credentials resolve in this order: the environment, then
`~/.config/itu-t-documents/config.toml`, then a secretspec provider (optional
extra, inert when it is not installed). They are never written to the
repository.

## The MCP server

```bash
itu-t-documents mcp     # speaks MCP over stdio, waits for the client
```

See [mcp.md](mcp.md).
