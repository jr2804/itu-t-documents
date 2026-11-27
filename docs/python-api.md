---
title: The Python API
---

Everything the command line does is available from Python. The entry point is
`ItuDocuments`; the structure of the ITU-T lives in `ItuCatalogue`.

```python
from itu_t_documents import DocType, ItuDocuments, MeetingId, StudyPeriod

with ItuDocuments() as api:
    period = StudyPeriod.from_year(2025)

    api.sync_meeting(12, MeetingId.from_code("260609"), period)
    for document in api.documents_for_question(study_group=12, question=5):
        print(document.document_id, document.title)
```

## `ItuDocuments`

The class combines the three sources of truth: the ITU-T web site, the
metadata store and the file cache. It is a context manager — leaving the
`with` block closes the HTTP client.

### Discovery

```python
list_meetings(study_group: int, study_period: StudyPeriod) -> list[MeetingInfo]
list_questions(study_group: int, study_period: StudyPeriod) -> list[Question]
```

The meetings of a study group and the questions under study. Both are read
from the ITU-T and cached.

### Fetching

```python
fetch_documents(study_group, doc_type, study_period, meeting=None) -> list[DocumentMetadata]
fetch_document_detail(ref: DocumentRef) -> DocumentMetadata
```

`fetch_documents` reads a listing, page by page until the last one — the
contributions of a study period can number more than a thousand. The
temporary documents of a meeting are read per sub-type, because the aggregate
listing of the ITU-T only previews five documents per sub-type.
`fetch_document_detail` reads the renditions of a single document.

### Synchronising

```python
sync_meeting(study_group, meeting, study_period,
             doc_types=(DocType.CONTRIBUTION, DocType.TEMPORARY_DOCUMENT)) -> int
sync_questions(study_group, study_period) -> int
sync_detail(ref) -> DocumentMetadata
```

`sync_meeting` stores the documents of a meeting in the local database and
returns how many it stored. `sync_detail` stores the renditions of one
document, as its detail page lists them. What a listing told about the
document — the posting date, the meeting, the sources — stays as it is.

### Searching

```python
find_documents(*, study_group=None, study_period=None, doc_type=None,
                doc_types=None, meeting=None, question=None,
                source=None, limit=None) -> list[DocumentRecord]
```

The documents of the local database, newest number first. Every filter is
optional; `source` matches partially and case insensitively and returns a
document once, however many of its sources match. `study_period` names one
stored study period; without it every stored period is searched.

```python
documents_for_question(study_group, question, meeting=None, doc_type=None,
                       study_period=None)
contributions_by_source(study_group, source, study_period=None)
top_sources(study_group, meetings=None, doc_types=(C, TD), limit=10)
```

`documents_for_question` and `contributions_by_source` search the metadata
store like `find_documents` does. `top_sources` counts the documents every source submitted:

```python
for source in api.top_sources(study_group=12, meetings=("260609",), limit=3):
    print(source.count, source.source)
```

```text
19 ITU-T Study Group 12
16 Luleå University of Technology (Sweden)
14 China Mobile Communications Co. Ltd. (China)
```

### Downloading

```python
download(ref, file_format=PDF, language=ENGLISH, output=None) -> Path
```

Downloads a document, or serves it from the file cache. The rendition that
matches the format and the language is picked automatically, and the original
is preferred over a revision. The detail page that names the renditions adds
them to the metadata store; what the listing told stays.

```python
from itu_t_documents import DocFormat, DocLanguage, DocumentRef

path = api.download(DocumentRef.parse("T25-SG12-C-0192"), DocFormat.WORD, DocLanguage.ENGLISH)
```

It raises `FileNotFoundError` when the DMS has no rendition in that format and
language, `AuthenticationError` when there are no usable credentials, and
`AccessDeniedError` when the account may not see the document.

### The catalogue

```python
api.catalogue.study_groups(period)
api.catalogue.structure(12, period)
```

The `ItuDocuments` object carries a catalogue — see
[the catalogue of the ITU-T](catalogue.md).

## The models

The models are pydantic models, frozen and validated. They are the domain
model of the ITU-T — see the
[reference of the DMS](reference/itu-dms.md) for how they map onto the wire
format.

### `DocumentRef`

The identity of a document.

```python
ref = DocumentRef.parse("T25-SG12-260609-TD-GEN-0467")

ref.document_id       # "T25-SG12-260609-TD-GEN-0467"
ref.display_number    # "467-GEN"
ref.study_group_code  # "SG12"
ref.visibility        # DocVisibility.INTERNAL
ref.download_url(DocFormat.WORD, DocLanguage.ENGLISH)
ref.detail_url()
```

### `DocumentMetadata`

What the detail page says about a document: its title and the renditions it
offers. The detail page does not repeat the sources, the questions or the
posting date — those belong to the listing record, which is what
[`find_documents`](#searching) returns.

```python
metadata = api.fetch_document_detail(ref)

metadata.title            # "Executive Summary of the Working Party 1/12 Meeting"
metadata.files            # the renditions
```

The listing record carries the fields of the listing:

```python
record = api.find_documents(study_group=12, question=5, limit=1)[0]

record.posted             # datetime.date(2026, 6, 5)
record.sources            # ("Chair WP1/12",)
record.questions          # (7, 6, 5, 4, 10), the order of the DMS
```

### `DocumentFile`

One rendition of a document.

```python
for rendition in metadata.files:
    print(rendition.file_format, rendition.language, rendition.extension, rendition.size_bytes)
```

`extension` is the extension of the published file — a Word document may be a
`.docx`, a `.doc` or a `.msw` file, so it is not implied by the format.

### `StudyPeriod`, `StudyGroup`, `MeetingId`

```python
StudyPeriod.from_year(2025)         # .label == "2025-2028"
StudyPeriod.current()               # the period of today
StudyPeriod.containing(2026)        # .label == "2025-2028"
StudyGroup(number=5, period=period) # .code == "SG05"
MeetingId.from_code("261015")       # .label == "2026-10-15"
```

The study periods are a closed list — the ITU-T publishes them, and a period
that does not exist cannot be built.

### `Question`, `WorkingGroup`, `Person`

A question under study, the working group that handles it and the people who
hold a role for it.

```python
questions = {question.code: question for question in api.list_questions(12, period)}
question = questions["Q5/12"]

question.code              # "Q5/12"
question.working_group.code  # "WP1/12"
question.rapporteurs       # the people holding the rapporteur role
question.co_rapporteurs    # the people holding the co-rapporteur role
```

## The metadata store

The store is a SQLite database in the cache directory. `ItuDocuments` opens
it; use it directly when you want to query the database yourself.

```python
from sqlmodel import select

from itu_t_documents.storage.database import DocumentRow

api.store.count_documents()
api.store.store_document(metadata)
api.store.store_detail(detail)
api.store.store_question(question, period.label)
api.store.close()

with api.store.session() as session:
    rows = session.exec(select(DocumentRow)).all()
```

`store_document` stores what a listing tells about a document and
`store_detail` what its detail page adds, the renditions, without erasing
the rest. `close()` releases the database connections; `ItuDocuments` does
it for the store it opened.

The tables are `study_period`, `study_group`, `meeting`, `question`,
`person`, `document`, `document_source`, `document_question` and
`document_file`.

## The file cache

```python
api.cache.path_for(ref, DocFormat.PDF, DocLanguage.ENGLISH)
api.cache.find(ref, DocFormat.PDF, DocLanguage.ENGLISH)
api.cache.has(ref, DocFormat.PDF, DocLanguage.ENGLISH)
api.cache.store(ref, DocFormat.PDF, DocLanguage.ENGLISH, content)
api.cache.load(ref, DocFormat.PDF, DocLanguage.ENGLISH)
```

A rendition is cached under the identifier of its document, with the format
and the language in the name. A revision is kept beside the original.

## The errors

Every error of the package derives from `ItuError`:

| Error | Raised when |
|-------|-------------|
| `AuthenticationError` | The TIES login did not succeed |
| `AccessDeniedError` | The account may not see the document |
| `IncompleteListingError` | A listing holds fewer documents than it reports |
| `UnknownEntityError` | The catalogue does not know the entity |

`download` also raises the built-in `FileNotFoundError` when the DMS has no
rendition that matches the requested format and language. That one is not an
`ItuError`, so catch it separately if you download by format and language.

```python
from itu_t_documents import AccessDeniedError, ItuError

try:
    api.download(ref)
except ItuError as error:
    print(error)
```

## The configuration

`Settings` resolves the configuration from the environment, the configuration
file and the secretspec provider.

```python
from itu_t_documents import Settings

settings = Settings()
settings.ties_username
settings.cache_dir
settings.timeout
settings.secretspec_manifest
```

| Setting | Environment variable | Meaning |
|---------|----------------------|---------|
| `ties_username` | `ITU_TIES_USERNAME` | The TIES account |
| `ties_password` | `ITU_TIES_PASSWORD` | The TIES password |
| `cache_dir` | `ITU_CACHE_DIR` | The cache directory |
| `config_dir` | `ITU_CONFIG_DIR` | The configuration directory |
| `timeout` | `ITU_TIMEOUT` | The timeout of a request, in seconds |
| `max_concurrency` | `ITU_MAX_CONCURRENCY` | The number of parallel requests |
| `user_agent` | `ITU_USER_AGENT` | The user agent of the requests |
| `verify_tls` | `ITU_VERIFY_TLS` | Whether the TLS certificates are verified |
| `secretspec_manifest` | `ITU_SECRETSPEC_MANIFEST` | The manifest of the secretspec provider |

See [getting started](getting-started.md) for the file format.
