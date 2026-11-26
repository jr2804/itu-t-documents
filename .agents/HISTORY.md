# AGENTS.md — HISTORY

Recorded decisions with git references. Read when relevant to current task.
Acts as simple long-term memory for the project.

## Format

| Date       | Decision   | Rationale   | Git ref          |
| ---------- | ---------- | ----------- | ---------------- |
| 2026-11-26 | The document identifiers mirror the ITU-T DMS: `T25-SG12-261015-TD-GEN-0520` for a temporary document, `T25-SG12-C-0192` for a contribution | The identifiers are the only stable address of a document in the DMS. Contributions, collective letters and reports are numbered across the study period, so their identifier carries no meeting | Initial commit |
| 2026-11-26 | The ITU-T login is a four step SAML handshake, not a form post | `auth.itu.int` hands a `SAMLRequest` to the identity provider at `login.itu.int`, which answers with a `SAMLResponse` for the assertion consumer service of `www.itu.int`. The credential post to `login.itu.int/my.policy` is the step in between | Initial commit |
| 2026-11-26 | The listing page size is set with the `ITUDMS_PageSize` cookie | The page size is a cookie, not a URL parameter; without it a listing is silently truncated at 50 rows | Initial commit |
| 2026-11-26 | The meeting document pages are decoded as ISO-8859-1 | Those pages do not declare a charset but are encoded in ISO-8859-1, while the `net4` pages are UTF-8 | Initial commit |
| 2026-11-26 | Study groups are zero padded to two digits, so study group 5 becomes `SG05` in the identifiers and in the paths | The ITU-T writes `T25-SG05-C-0538` and serves the study group pages under `/studygroups/2025-2028/05/`; the unpadded `T25-SG5` answers with an empty page. Only the `net4` applications take the plain number as `Group=5` | 2026-11-27 |
| 2026-11-26 | The metadata store keeps the meeting of a contribution even though the identifier carries none | The listing a contribution appears in is the only source of its meeting | Initial commit |
| 2026-11-27 | secretspec is an optional credential source below the environment and the configuration file | It lets users keep the TIES password in a real secret manager instead of a file, but the package must keep working without it: `secretspec_credentials` reads `ITU_TIES_USERNAME`/`ITU_TIES_PASSWORD` from the provider alias `itu-ties` and returns `None` on a missing extra, a missing manifest or an unresolvable provider, so the layer contributes nothing in the default install | Uncommitted |

## Guidance

- Record decisions that would be costly to rediscover.
- Note false turns and why they were rejected.
- Link to relevant commits.
- Keep entries brief — enough to reconstruct reasoning.
- When this file grows too large, archive older entries to
  `.agents/history/` and leave a pointer here.
