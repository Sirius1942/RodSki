# RodSki Agent Guide

This file is the working contract for Codex in the RodSki repository.

## 1. What This Repo Is

RodSki is an execution engine for AI agents, not a generic application scaffold.

The repo is split into four practical areas:

- `rodski/` - deterministic execution engine, parsers, drivers, CLI, schemas
- `rodski-agent/` - higher-level agent layer for design, execution, and repair
- `rodski-demo/` - official examples and acceptance coverage
- `.pb/` - project management system for requirements, specs, iterations, and conventions

`rodski-web/` is a separate helper app for browsing or editing generated test assets.

## 2. Source of Truth

Treat these as authoritative, in this order:

1. `rodski/docs/CORE_DESIGN_CONSTRAINTS.md`
2. `rodski/docs/TEST_CASE_WRITING_GUIDE.md`
3. `rodski/docs/AGENT_INTEGRATION.md`
4. `.pb/README.md`
5. `.pb/conventions/*`
6. Active `.pb/requirements/*`, `.pb/specs/*`, and `.pb/iterations/*`
7. `CLAUDE.md`

Historical notes in `.claude/memory/*` and `.pb/archive/*` are reference material only. Use them only if they do not conflict with active docs.

If code, docs, and notes disagree, follow the active docs first, then update the stale material in the same change.

## 3. Repo-Specific Working Rules

- Read the smallest relevant set of docs before editing.
- Prefer `rg` and `rg --files` for discovery.
- Use `apply_patch` for manual file edits.
- Keep changes minimal and local to the task.
- Do not revert unrelated user changes.
- Do not clean or rewrite files you did not touch unless the task explicitly asks for it.
- Do not treat generated artifacts, demo results, or build outputs as source.
- If a change affects behavior, update the matching docs and iteration records in the same patch.

## 4. Workflow

1. Identify the exact task and the active docs that govern it.
2. Inspect the relevant code and nearby tests before changing anything.
3. Make the smallest patch that solves the problem.
4. Validate with the narrowest useful test set first.
5. Expand validation only when the change touches shared behavior or public contracts.
6. Summarize what changed, what was validated, and what remains risky.

## 5. Validation Expectations

Use the validation level that matches the blast radius:

- Doc-only change: check links, paths, and cross-references.
- Local code change: run the focused unit tests for the touched module.
- Shared execution or parser change: run the relevant unit suite and `python3 rodski/selftest.py` when it makes sense.
- Acceptance or flow change: verify with `rodski-demo/` or the relevant demo module.

Useful commands in this repo:

```bash
python3 -m pytest rodski/tests/unit -q
python3 rodski/selftest.py
rodski data validate <module>
rodski run <case_path>
rodski init <target> --with-sqlite
```

If the task touches data contracts, CLI behavior, or XML structure, validate the affected demo or module end to end instead of relying on unit tests alone.

## 6. Documentation Rules

- Framework docs live in `rodski/docs/`.
- Project management docs live in `.pb/`.
- Active iteration work should update the corresponding `iteration-XX` files.
- If you change a public contract, update the matching guide, spec, or iteration note in the same change.
- Keep `CLAUDE.md` and this file aligned when repo-wide guidance changes.

## 7. Editing Constraints

- Preserve the repo's existing style and terminology.
- Do not introduce new abstractions unless they remove real duplication or clarify an existing pattern.
- Do not change core contracts, schema rules, or data semantics without updating the governing docs first.
- Do not use historical notes as the only basis for implementation.
- When there is a dirty worktree, assume untracked and modified files may belong to the user.

## 8. Current High-Signal Facts

- RodSki is positioned as an AI-agent-facing deterministic execution engine.
- `rodski-demo/` is the official example and acceptance baseline.
- `.pb/` is the project management system, not a scratch space.
- `rodski-agent/` depends on `rodski/`, not the other way around.
- Generated demo results should not be edited by hand.

## 9. When To Stop And Ask

Pause and ask the user when a task would require any of the following:

- changing a core contract without updating the governing docs
- deleting or rewriting user-owned work outside the task scope
- resolving contradictory product directions that cannot be reconciled from the active docs
- making a broad refactor that is larger than the request

## 10. Final Output

End each task with a short, factual summary that includes:

- the files changed
- the validation performed
- any known risk or follow-up

Keep the summary tight. Do not pad it with process narration.
