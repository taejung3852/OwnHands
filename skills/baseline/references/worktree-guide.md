# Optional Git Worktree Isolation Guide

OwnHands records baseline facts from the developer's active workspace. Creating an isolated Git Worktree is completely optional and never forced.

## When to Consider a Worktree

1. **Dirty Working Tree**: The current working copy contains in-progress, uncommitted modifications that would contaminate pre-change test observations.
2. **Parallel Long-Running Tests**: Baseline tests take a long time, and you wish to begin editing immediately in another folder.
3. **Explicit User Preference**: The user requested an isolated feature workspace or branch.

## Setting Up an Isolated Worktree (Optional)

```bash
# 1. Detect if already in a worktree
GIT_DIR=$(cd "$(git rev-parse --git-dir)" 2>/dev/null && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd -P)
if [ "$GIT_DIR" != "$GIT_COMMON" ]; then
  echo "Already in an isolated worktree."
fi

# 2. Add a new worktree if needed
BRANCH_NAME="feat/your-feature-name"
git worktree add "../worktrees/$BRANCH_NAME" -b "$BRANCH_NAME"
cd "../worktrees/$BRANCH_NAME"
```

## Sandbox and Permission Fallback

If `git worktree add` fails due to sandbox restrictions, directory permission limits, or host tool constraints:
- Do NOT abort or fail the task.
- Fall back gracefully to the current working directory (`in-place fallback`).
- Record the current working tree cleanliness and continue the baseline observation in-place.
