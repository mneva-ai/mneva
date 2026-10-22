# The mneva file format

mneva keeps memory as plain Markdown files. This page describes those files so that other tools can read and write them without going through mneva. It documents what mneva does today (0.7); it is not a wish list.

If your tool writes files that follow this page, mneva will index them, search them, put them into AI chats and sync them with Obsidian. If you only read them, you get the user's memory with no SDK and no account.

## Where the files live

```
~/.mneva/                  # or $MNEVA_HOME if set
  store/<id>.md            # one record per file: the source of truth
  mneva.sqlite             # search index, derived; safe to delete
```

Everything else under `~/.mneva` (index, logs, proposals, extension copy) is derived or bookkeeping. Deleting it never loses a memory. `mneva reindex` rebuilds the index from `store/`.

## One record, one file

A record is a UTF-8 Markdown file with YAML frontmatter:

```markdown
---
scope: profile
lifespan: permanent
tool: claude-code
source: null
---

## How I want AI to work with me
Short answers first, details on request. Explain trade-offs, not basics.
```

- **File name:** `<id>.md`. The file name stem is the record id. mneva generates ids as 16 lowercase hex characters, but readers should accept any stem.
- **Body:** everything after the frontmatter, free Markdown.

### Frontmatter fields

| Field | Required | Meaning | If missing when read |
|---|---|---|---|
| `scope` | yes | Bucket the record belongs to, for example `profile` or a project name | `unknown` |
| `lifespan` | yes | `permanent` or `transient` | `permanent` |
| `tool` | yes | Which tool wrote it, for example `cli`, `claude-code`, `codex` | `unknown` |
| `source` | no | Free text about where it came from; may be `null` | none |
| `repo` | no | Git remote of the repository the record was captured in; used as a filter | none |
| `repo_path` | no | Local path of that repository | none |
| `branch` | no | Git branch at capture time | none |
| `commit_sha` | no | Git commit at capture time | none |

The four git fields are left out entirely when unset, not written as `null`.

Unknown keys are allowed in files you write, but mneva does not keep them: when mneva rewrites a record, only the fields above survive. Do not store data you need in extra keys.

## The profile

The profile is not a separate file type. It is the set of records with `scope: profile` and `lifespan: permanent`.

- Keep one topic per record, usually starting with a `## ` heading, for example "Who I am", "What I'm working on", "How I want AI to work with me", "Current priorities". `mneva setup` writes a template with these headings to `~/.mneva/profile-template.md`.
- Tools that pass the profile on under a size limit (for example `mneva brief --max-chars 1500`) include whole records only. A record that does not fit is skipped, never cut, because half a preference can mean its opposite. Short records are easier to fit.
- Records are currently taken in file name order. Do not rely on order for meaning.

## Obsidian vault mirror

`mneva sync-vault` mirrors records into an Obsidian vault and back:

```
<vault>/mneva/<scope>/<id>.md
```

A vault note has the same frontmatter plus `mneva_id: <id>`. When syncing back, only notes that carry `mneva_id` are imported, so the user's other notes are never pulled in. To add a record from Obsidian or another note tool, create a note in that folder with a new unique `mneva_id` and the fields above.

## Writing records from another tool

1. Pick a new id (16 lowercase hex characters is safest) and write `~/.mneva/store/<id>.md` with the frontmatter above.
2. Run `mneva reindex` so search sees it. Reading tools that scan `store/` directly do not need this step.
3. To change a record, rewrite the file. To delete one, delete the file.

## Compatibility promise

- Markdown files stay the source of truth. Anything else mneva stores can be rebuilt from them.
- New fields are added as optional fields. Existing fields keep their meaning.
- No account, no encryption of the files, no proprietary container. The user can open, edit, copy, version in git or delete every record with ordinary tools.
