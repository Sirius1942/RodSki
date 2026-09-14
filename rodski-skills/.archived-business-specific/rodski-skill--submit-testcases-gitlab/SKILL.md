---
name: submit-testcases-gitlab
description: Submit RodSki test case assets to the shared GitLab repository from a submitter's own testcase roots. Use when the user asks to push or submit RodSki case/data/fun/model assets to GitLab. The submitter must provide their own GitLab username, personal branch, and owner directory; never target main/master/head, never write passwords into skill files, and never clean sibling submitter folders.
---

# Submit RodSki Testcases To GitLab

Use the bundled script instead of hand-writing git commands. It scans RodSki
module roots, copies only immediate child directories named `case`, `data`,
`fun`, or `model`, rebuilds only the current submitter-owned folder, then
commits and pushes to that submitter's personal GitLab branch.

The GitLab repository is a publish artifact. Every push must leave only the
currently selected testcase assets inside the current submitter-owned folder.

## Required Submitter Config

Before dry-run or push, identify the submitter's own values:

- GitLab username: `--username` or `RODSKI_GITLAB_USERNAME`
- Personal branch: `--branch` or `RODSKI_GITLAB_BRANCH`; if omitted, the script
  uses the GitLab username as the branch
- Owner directory: `--owner-dir` or `RODSKI_GITLAB_OWNER_DIR`
- Source root: `--source`; default is `$HOME/TestCase/00 Pass`

Do not reuse another colleague's branch or owner directory. Do not infer the
owner directory from previous runs unless the user explicitly confirms it.

Example setup:

```bash
export RODSKI_GITLAB_USERNAME="<gitlab_username>"
export RODSKI_GITLAB_BRANCH="<personal_branch>"
export RODSKI_GITLAB_OWNER_DIR="<owner_dir>"
```

The repository clone URL defaults to:

```text
https://gitlab.casstime.net/qa/RodSki-AutoTest
```

Use `--repo-url` only when the user provides a different repository.

## Safety Guards

The script enforces these checks in code:

- Protected branch refusal: `main`, `master`, and `head` are rejected before any
  clone or push. There is no override flag.
- Owner-scope assertion: after `git add -A`, staged paths are checked and the
  script refuses to commit if any staged path falls outside the current
  `--owner-dir`.
- Cleanup scope: push mode deletes and recreates only the current owner
  directory. Sibling submitter folders and repository-root legacy-looking
  folders are not cleaned.

Old directories such as `improve`, `00 Pass`, `00 模块`, `myenv`, `tools`,
result folders, source trees, generated agent packages, and other stray files
must never be copied.

## Source Roots

By default the script scans the single root `$HOME/TestCase/00 Pass`.
Pass `--source` more than once to merge several roots into one submission:

```bash
python3 scripts/submit_testcases_gitlab.py --dry-run \
  --source "$HOME/TestCase/00 Pass" \
  --source "$HOME/TestCase/00 落地项目"
```

All roots flatten into the same `<owner_dir>/<module>/...` layout, so the module
folder name must be unique across roots. If two roots map to the same
destination path, the script refuses with a collision error instead of silently
overwriting. Because push mode rebuilds the whole owner directory on every run,
all desired roots must be passed in the same command.

## Workflow

1. Run a scan first:

```bash
python3 scripts/submit_testcases_gitlab.py --dry-run
```

2. Check that selected module roots and copied directories are only test case
assets. The dry-run output must also say only the target owner directory will be
rebuilt and sibling submitter folders will not be cleaned.

3. Push only after the scan looks correct:

```bash
python3 scripts/submit_testcases_gitlab.py --push
```

When submitting multiple roots, repeat `--source` on the push command exactly as
on the dry-run.

If the script says there are no changes after cleaning and syncing, treat that
as a successful up-to-date check: no commit is created and no push is needed.

Use `--message "提交测试用例: <reason>"` when the user gives a specific commit
message. The script automatically appends the current RodSki version. By
default it reads `/opt/homebrew/bin/rodski --version`; use `--rodski-bin` or
`--rodski-version` only for a deliberate override.

## Credentials

Do not write the GitLab password or token into tracked skill files, scripts,
shell history, final answers, or repository files.

The submit script authenticates by trying these sources:

- `RODSKI_GITLAB_PASSWORD` environment variable
- optional local private file passed by `--password-file` or
  `RODSKI_GITLAB_PASSWORD_FILE`
- macOS Git credential helper / Keychain, when available
- existing Git credential configuration

For one-time secure setup on macOS, run:

```bash
python3 scripts/store_gitlab_credential.py --username "$RODSKI_GITLAB_USERNAME"
```

The setup script prompts for the password without echoing it and stores it in
the configured Git credential helper. It does not write a local password file
unless `--password-file` is explicitly passed or `RODSKI_GITLAB_PASSWORD_FILE`
is set. If authentication still fails, ask the user to provide or refresh
credentials outside source files.

## Reporting

After a successful push, report:

- source path(s)
- GitLab repository URL
- GitLab branch list URL
- branch file browser URL printed by the script
- branch and owner directory
- RodSki version included in the commit message
- number of module roots and copied directories
- that cleanup rebuilt only the owner directory and did not touch sibling
  submitter folders
- commit hash, if a commit was created
- whether `git push` completed

If there are no changes, say the selected test case data is already up to date
on the configured branch, no commit was created, and push was skipped.
