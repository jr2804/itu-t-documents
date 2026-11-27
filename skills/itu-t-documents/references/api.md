# The Python API

```bash
pip install itu-t-documents
```

```python
from itu_t_documents import ItuDocuments, StudyPeriod
```

The package is `itu_t_documents`, the distribution is `itu-t-documents`, the
command is `itu-t-documents`.

## The two entry points

| Class | What it answers |
| ----- | --------------- |
| `ItuDocuments` | The documents: meetings, questions, the store, the download. |
| `ItuCatalogue` | The structure of the ITU-T: periods, study groups, working groups, questions. |

Both are context managers; both take an optional `Settings`:

```python
from itu_t_documents import ItuDocuments, ItuCatalogue, Settings

with ItuDocuments(Settings(cache_dir="~/.cache/itu-t-documents")) as api:
    ...
```

## The documents

```python
from itu_t_documents import DocType, ItuDocuments, MeetingId, StudyPeriod

period = StudyPeriod.current()          # 2025-2028 today

with ItuDocuments() as api:
    meetings = api.list_meetings(study_group=12, study_period=period)
    for meeting in meetings:
        print(meeting.code, meeting.label)
```

| Method | What it does |
| ------ | ------------ |
| `list_meetings(study_group, study_period)` | The meetings of a study group. |
| `list_questions(study_group, study_period)` | The questions under study. |
| `fetch_documents(study_group, doc_type, study_period, meeting=None)` | The documents of a meeting, read from the DMS. |
| `fetch_document_detail(ref)` | The detail page of one document. |
| `sync_meeting(study_group, study_period, meeting, doc_types=...)` | Fetches a meeting into the store. |
| `sync_questions(study_group, study_period)` | Stores the questions of a study group. |
| `sync_detail(ref)` | Stores the detail page of one document. |
| `find_documents(study_group, ...)` | Searches the store. |
| `documents_for_question(study_group, question, ...)` | The documents of one question. |
| `contributions_by_source(study_group, source, ...)` | The contributions of one source. |
| `top_sources(study_group, meetings, ...)` | The most prolific sources of the given meetings. |
| `download(ref, file_format, language, output_file=None)` | Downloads one file. |

### Finding documents

```python
from itu_t_documents import DocType, ItuDocuments, StudyPeriod

with ItuDocuments() as api:
    api.sync_meeting(study_group=12, study_period=StudyPeriod.current(), meeting="260609")

    for record in api.find_documents(study_group=12, question=5):
        print(record.document_id, record.title, record.posted)

    for record in api.contributions_by_source(study_group=12, source="Company Ltd."):
        print(record.document_id, record.sources)
```

`find_documents` takes `study_group`, and optionally `doc_type`, `question`,
`source`, `meeting`, `study_period` and `limit`. It returns `DocumentRecord`
objects: the number, the title, the sources, the questions and the posting
date of a document. The detail page carries the files and the title, the
listing carries the rest — the store holds both.

### Downloading

```python
from pathlib import Path

from itu_t_documents import DocFormat, DocLanguage, DocumentRef, ItuDocuments

ref = DocumentRef.parse("T25-SG12-C-0192")

with ItuDocuments() as api:
    path = api.download(ref, DocFormat.WORD, DocLanguage.ENGLISH, Path("/tmp/doc.docx"))
```

`DocFormat` is `PDF`, `WORD` (the value `MSW`), `ZIP` and `HTML` (the value
`HTM`). `DocLanguage` is `ENGLISH` (`E`), `FRENCH` (`F`), `SPANISH` (`S`),
`ARABIC` (`A`), `CHINESE` (`C`), `RUSSIAN` (`R`).

## The catalogue

```python
from itu_t_documents import ItuCatalogue, StudyPeriod

period = StudyPeriod.current()

with ItuCatalogue() as catalogue:
    for group in catalogue.study_groups(period):
        print(group.code, group.label)

    structure = catalogue.structure(study_group=12, period=period)
    for question in structure.questions:
        print(question.code, question.title)

    for entry in catalogue.search("speech", period):
        print(entry.kind, entry.label)
```

| Method | What it does |
| ------ | ------------ |
| `study_groups(period)` | The study groups of a period. |
| `find_study_group(number, period)` | One study group. |
| `structure(study_group, period)` | The plenary, the working groups, the questions and the other groups. |
| `find_working_group(code, period)` | One working group. |
| `find_question(number, period, study_group=None)` | One question. |
| `search(text, period=None)` | The groups, questions and working groups that match. |

The catalogue never hard codes the structure: the study groups and the
questions change from study period to study period.

## The domain model

```python
from itu_t_documents import DocType, DocumentRef, MeetingId, StudyPeriod

period = StudyPeriod.from_year(2025)      # 2025-2028
period = StudyPeriod.containing(2026)      # 2025-2028
period = StudyPeriod.parse("2025-2028")
period = StudyPeriod.parse("2025")         # the period that starts in 2025
period = StudyPeriod.current()
period = StudyPeriod.all()

ref = DocumentRef.parse("T25-SG12-261015-TD-GEN-0520")
ref.document_id          # the identifier, unchanged
ref.display_number       # "0520"
ref.study_group_code     # "SG12"
ref.detail_url           # the page of the DMS
```

`StudyPeriod` is a closed registry: a period that the ITU-T does not have
cannot be constructed.

## The settings

```python
from itu_t_documents import Settings

settings = Settings()
settings.ties_username
settings.cache_dir       # ~/.cache/itu-t-documents
settings.config_dir      # ~/.config/itu-t-documents
```

| Variable | Meaning |
| -------- | ------- |
| `ITU_TIES_USERNAME` | The user of the TIES account. |
| `ITU_TIES_PASSWORD` | Its password. |
| `ITU_CACHE_DIR` | Where the metadata store and the file cache live. |
| `ITU_CONFIG_DIR` | Where `config.toml` and the secretspec manifest live. |
| `ITU_TIMEOUT` | The timeout of a request, in seconds. |
| `ITU_MAX_CONCURRENCY` | How many requests run at the same time. |
| `ITU_USER_AGENT` | The user agent of the requests. |
| `ITU_VERIFY_TLS` | Whether the certificates are verified. |

## The errors

All of them derive from `ItuError`:

| Error | Meaning |
| ----- | ------- |
| `AuthenticationError` | The TIES login failed. |
| `AccessDeniedError` | The account has no membership for that study group. |
| `IncompleteListingError` | The listing holds fewer documents than the ITU-T reports. |
| `UnknownEntityError` | The study group, the working group or the question does not exist. |
| `FileNotFoundError` | The document has no file in that format and language. |
