# Troubleshooting

Every error of the package derives from `ItuError`.

## `AuthenticationError`

```text
TIES login failed: <the message of the access policy>
```

The TIES login did not succeed. The causes in the order of their likelihood:

1. **The credentials are wrong.** Check them with `itu-t-documents auth`.
2. **The account is not a TIES account** or the password expired.
3. **The access policy redirected without a target** — the ITU-T changed the
   handshake, not something the caller can fix.

The login is a four step SAML handshake against `auth.itu.int` and
`login.itu.int`. It happens once per session: the session cookie lives in the
HTTP client and every later request uses it. A failure is not retried.

## `AccessDeniedError`

```text
T25-SG12-C-0192 is not accessible with these credentials; the membership of the TIES account does not cover SG12
```

**This is not a wrong password.** The ITU-T answers a document outside the
membership of the account with 401 and a page that blames the credentials,
which is misleading: the login itself succeeded.

A TIES account covers only the study groups of its membership. Ask the
membership holder to add the study group, or work with the metadata of the
group, which is public. Do not log in again — the login is fine.

## `IncompleteListingError`

```text
the listing holds 900 of 972 documents; not every page of the ITU-T listing could be read
```

The listing was truncated. The listings of the DMS are paginated, and the
package compares what it read with the number of documents the ITU-T reports.
A truncated listing is never stored as if it were complete.

What to do:

1. Run the command again — the HTTP cache may hold the missing page.
2. If it repeats, the page size or the pagination of the ITU-T changed; the
   package reads the `Next` link of every page and sets the `ITUDMS_PageSize`
   cookie to 900, the most the web interface offers.

## `UnknownEntityError`

```text
2025-2028 has no study group SG99; its study groups are ['SG02', 'SG03', ...]
SG12 has no working group WP9/12
no study group of 2025-2028 has a question Q99
```

The entity does not exist in that study period. The study groups, the working
groups and the questions change from period to period: SG9 and SG16 existed in
2022-2024 and were replaced by SG21 in 2025-2028.

What to do: read the entities of the period with
`itu-t-documents study-groups -p <period>` and
`itu-t-documents structure -g <group> -p <period>`, and search for a name
with `itu-t-documents search <text> -p <period>`.

## `FileNotFoundError`

```text
T25-SG12-C-0192 is not available as PDF-E
```

The document has no file in that format and that language. A document is
published in the format it was submitted in: `T25-SG12-C-0192` exists as MSW
only. A revision may exist in more languages than the original.

What to do: read the detail page of the document
(`ref.detail_url` in the API) and pick a format and a language it offers.

## "No TIES credentials found"

```text
No TIES credentials found.
Set ITU_TIES_USERNAME and ITU_TIES_PASSWORD, or store them in ~/.config/itu-t-documents/config.toml.
```

The credentials resolve in this order: the environment, then the
configuration file, then a secretspec provider (an optional extra, inert when
it is not installed). The configuration file lives outside the repository and
holds:

```toml
[credentials]
username = "..."
password = "..."
```

A secretspec provider that resolves a secret as an *empty* value is reported
by name:

```text
the secretspec provider 'itu-ties' resolved ITU_TIES_PASSWORD as an empty value; quote the value in the provider's .env file
```

A `dotenv` provider reads everything behind an unquoted `#` as a comment, so
a password that begins with one has to be quoted: `ITU_TIES_PASSWORD="#abc"`.

## The command answers with nothing

`documents` reads the **local database**. A meeting that was never synced is
unknown to it, and the answer is empty rather than an error.

```bash
itu-t-documents sync -g 12 -m 260609     # store the meeting first
itu-t-documents documents -g 12 -m 260609
```

The MCP tools synchronise themselves, the command line does not.

## The listing shows fewer documents than expected

The numbers of the documents are not consecutive, and a withdrawn document
leaves a hole. `T25-SG13-C-0669` does not exist between `C-0668` and
`C-0670`. A number does not prove that a document exists, and a status code
does not prove it either.

## The output of the CLI looks different than expected

The columns are the plain values of the model: the study group is written
with two digits (`SG12`), the meeting code without a separator (`260609`), the
period as its years (`2025-2028`). The identifiers of the documents are
never reformatted.
