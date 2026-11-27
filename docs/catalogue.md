---
title: The catalogue of the ITU-T
---

The ITU-T is an organisation with a structure: study periods, study groups,
working groups and questions. The structure changes — a study group that
existed in one study period may be gone in the next, and the questions under
study are replaced every year.

So the package does not know the structure. It reads it from the ITU-T, and
it refuses an entity that does not exist instead of returning something
empty.

## The study periods

The ITU-T publishes a fixed list of study periods, each of them four years
long. The package knows them, so a period that does not exist cannot be
built:

```python
from itu_t_documents import StudyPeriod

StudyPeriod.from_year(2025)    # 2025-2028
StudyPeriod.containing(2026)    # 2025-2028
StudyPeriod.current()           # the period of today
StudyPeriod.all()               # every period the ITU-T knows
```

| Period | Code | net4 index |
|--------|------|------------|
| 2005-2008 | `T05` | 13 |
| 2009-2012 | `T09` | 14 |
| 2013-2016 | `T13` | 15 |
| 2017-2020 | `T17` | 16 |
| 2022-2024 | `T22` | 17 |
| 2025-2028 | `T25` | 18 |
| 2029-2032 | `T29` | 19 |

The period that was to start in 2021 was renamed to 2022-2024, because the
extra year was used for the session that had been postponed. That is why
2021 starts no period.

The net4 index is the number the web applications of the ITU-T use for the
period.

## The study groups

The study groups of a period are read from the index page of the period:

```python
from itu_t_documents import ItuCatalogue, StudyPeriod

with ItuCatalogue() as catalogue:
    period = StudyPeriod.from_year(2025)
    [group.code for group in catalogue.study_groups(period)]
```

```text
['SG02', 'SG03', 'SG05', 'SG11', 'SG12', 'SG13', 'SG15', 'SG17', 'SG20', 'SG21']
```

They really do change:

| Period | Study groups |
|--------|--------------|
| 2013-2016 | 02, 03, 05, 09, 11, 12, 13, 15, 16, 17, 20 |
| 2017-2020 | 02, 03, 05, 09, 11, 12, 13, 15, 16, 17, 20 |
| 2022-2024 | 02, 03, 05, 09, 11, 12, 13, 15, 16, 17, 20 |
| 2025-2028 | 02, 03, 05, 11, 12, 13, 15, 17, 20, 21 |

SG9 and SG16 existed in 2022-2024 and were replaced by SG21 in 2025-2028. A
hard coded list would be wrong for one of the two.

Asking for a study group that the period does not have is an error, and the
message names the ones that exist:

```python
catalogue.find_study_group(9, period)
```

```text
UnknownEntityError: 2025-2028 has no study group SG09; its study groups are SG02, SG03, SG05, SG11, SG12, SG13, SG15, SG17, SG20, SG21
```

## The structure of a study group

The structure page of a study group lists its plenary, its working groups, its
questions under study and its other groups:

```python
structure = catalogue.structure(12, period)

structure.plenary.code              # "PLEN"
[group.code for group in structure.working_groups]   # ["WP1/12", "WP2/12", "WP3/12"]
[question.code for question in structure.questions]   # ["Q1/12", "Q2/12", …]
[(group.code, group.kind) for group in structure.other_groups]
```

```text
[('SG12RG-AFR', 'regional'), ('SG12RG-AMR', 'regional'), ('SG12RG-AP', 'regional'), ('IRG-AVQA', 'rapporteur'), ('QSDG', 'study')]
```

| Code | Kind |
|------|------|
| `PLEN` | the plenary |
| `WP1/12` | a working group |
| `Q5/12` | a question under study |
| `SG12RG-AFR` | a regional group |
| `FG-AINN` | a focus group |
| `IRG-AVQA` | an intersector rapporteur group |
| `QSDG` | a quality study group |
| `JCA-IMT2020/IMT2030` | a joint coordination activity |

The questions know the working group that handles them, because a question
follows its working group on the page:

```python
structure.question(5).working_group.code   # "WP1/12"
structure.question(1).working_group.code   # "PLEN"
```

Asking for a question or a working group that the study group does not have
is an error:

```python
structure.question(99)
```

```text
UnknownEntityError: SG12 has no question Q99/12
```

## The search

The catalogue searches the working groups, the questions and the other groups
of a period:

```python
for entry in catalogue.search("speech", period):
    print(entry.kind, entry.code, entry.title)
```

```text
question Q15/12 Parametric and E-model-based planning, prediction and monitoring …
question Q4/12  Objective methods for speech and audio evaluation in vehicles …
```

The search covers the code and the title of every group of every study group
of the period.

## On the command line

The same things are available without writing Python:

```bash
itu-t-documents periods
itu-t-documents study-groups --study-period 2022-2024
itu-t-documents structure --study-group 12
itu-t-documents search --search speech
```

And to an AI agent, through the MCP server:

| Tool | Answers |
|------|---------|
| `list_periods` | *"Which study periods are there?"* |
| `list_study_groups` | *"Which study groups does the ITU-T have?"* |
| `list_structure` | *"Which working groups does SG13 have?"* |
| `search_structure` | *"Which working group deals with speech?"* |

## Why not hard code it

The structure of the ITU-T is published by the ITU-T and it changes with every
study period. The rules of this project are therefore simple: read the
structure, never hard code it, and refuse an entity that does not exist
rather than returning an empty result that looks like an answer.
