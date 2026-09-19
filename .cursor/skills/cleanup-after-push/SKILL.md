---
name: cleanup-after-push
description: >-
  After pushing a feature branch, switch to main, pull latest from remote, and
  delete the previous local feature branch. Use when the user asks to clean up
  after a push, return to main, finish a feature branch, or delete the local
  branch they just pushed.
disable-model-invocation: true
---

# Cleanup after push

Run this **after** the feature branch has been pushed (and ideally after the PR
is opened or merged as the user prefers). Deletes the **local** feature branch
only — never delete the remote branch unless the user explicitly asks.

## Steps

Copy and track:

```
Cleanup progress:
- [ ] Record current branch name
- [ ] Ensure working tree is clean
- [ ] Checkout main (or master)
- [ ] Pull latest from origin
- [ ] Delete the previous local feature branch
- [ ] Confirm final branch and status
```

### 1. Record the feature branch

```bash
FEATURE_BRANCH=$(git branch --show-current)
echo "$FEATURE_BRANCH"
```

If already on `main` or `master`, stop and tell the user there is no feature
branch to delete.

### 2. Safety checks

- Working tree must be clean (`git status`). If dirty, stop and ask the user
  what to do — do not stash or discard unless they ask.
- Never delete `main` or `master`.
- Do not run `git push --delete` or any remote branch deletion unless the user
  explicitly requests it in this turn.

### 3. Switch to main and pull

Prefer `main`; if it does not exist locally, use `master`.

```bash
git checkout main
git pull origin main
```

Use `required_permissions: ["all"]` (or network + git write) so pull can talk to
the remote.

### 4. Delete the local feature branch

```bash
git branch -d "$FEATURE_BRANCH"
```

- Use `-d` (safe delete) first.
- If Git refuses because the branch is not fully merged, tell the user and ask
  whether to force-delete with `-D`. Do **not** use `-D` unless they confirm.

### 5. Confirm

```bash
git branch --show-current
git status
git branch
```

Tell the user in one short message:
- Now on `main` (up to date)
- Which local branch was deleted
- That the remote branch was left alone (unless they asked otherwise)
