---
name: commit-draft-pr
description: >-
  Commit local changes without pushing, then draft a PR title and description
  for the current branch. Use when the user asks to commit but not push, wants a
  PR title/description for this branch, or says: "commit the code. but don't
  push it. give me a PR title and description for this branch."
disable-model-invocation: true
---

# Commit and draft PR (no push)

## How the user will ask

commit the code. but don't push it. give me a PR title and description for this branch.

Treat close paraphrases the same (e.g. “commit locally, no push, draft PR copy”).

## Hard rules

- **Do commit** when this skill is invoked (this request *is* the commit ask).
- **Do not push** — never `git push` or set upstream unless the user explicitly asks in a later message.
- **Do not open a PR** (`gh pr create`) unless the user explicitly asks; only **draft** the title and body for them to copy.
- Follow the repo’s git safety protocol (no force push, no amend unless the usual amend conditions are met, no updating git config, no `--no-verify`).
- Do not commit secrets (`.env`, credentials, etc.); warn if those are staged/requested.

## Steps

Copy and track:

```
Commit + draft PR progress:
- [ ] Inspect status, full diff, recent commit messages
- [ ] Stage relevant files only
- [ ] Commit with a why-focused message
- [ ] Confirm clean / expected status (no push)
- [ ] Draft PR title + description from branch vs base
```

### 1. Inspect (parallel)

Run together:

```bash
git status
git diff
git diff --cached
git log -8 --oneline
git branch --show-current
```

If there is nothing to commit, say so and still draft PR title/description from commits already on the branch vs `main`/`master` (if any).

### 2. Stage and commit

- Stage only files that belong in the change (skip secrets and unrelated junk).
- Match recent commit-message style on the branch/repo (prefer concise, why-focused; 1–2 sentences).
- Commit via HEREDOC:

```bash
git commit -m "$(cat <<'EOF'
Commit message here.

EOF
)"
```

- Run `git status` after to confirm success.
- If a hook rejects the commit, fix and create a **new** commit (do not amend unless amend rules allow).

### 3. Do not push

Stop after the local commit. Tell the user the commit hash and branch name, and that nothing was pushed.

### 4. Draft PR title and description

Base the draft on **all** commits on this branch vs `main` (or `master` if that is the default), not only the latest commit:

```bash
git log main..HEAD --oneline
git diff main...HEAD
```

Return exactly this shape in the reply (fill in the content):

**PR title:** short imperative summary

**PR description:**

```markdown
## Summary
- 1–3 bullets of what changed and why

## Test plan
- [ ] concrete verification steps
```

Keep the title ≤ ~70 characters when practical. Test plan checkboxes should be actionable for a human reviewer.
