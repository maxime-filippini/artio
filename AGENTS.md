# Repository guidance

## Local workspace conventions

- `.scratch/` is gitignored and reserved for the maintainer's local testing. Do not inspect, modify, delete, or add its contents to Git.
- The project todo list is `.todo/vertical-slices.md`. Read it directly when work refers to a todo item or implementation slice; do not search the repository to locate it.

## Git conventions

Always use Conventional Commit messages when creating Git commits, in the
standard `type: description` form (for example, `feat: add workflow parser`).

## Branch workflow

When starting work that needs a new branch, create it locally, push it to the
GitHub repository, and make the work's first reviewable commit. Then create a
pull request with `develop` as its base branch using the GitHub CLI.

Use Conventional Branch names in the `<type>/<description>` form, with a
lowercase, hyphen-separated description (for example,
`feat/issue-9-workflow-inputs` or `fix/parse-input-defaults`). Use a
purpose-based type such as `feat`, `fix`, `hotfix`, `release`, or `chore`;
never use an agent/vendor prefix such as `codex/`.

Keep commits small and legible, but keep pull requests behaviorally complete:
each PR should deliver a coherent, demonstrable outcome rather than an unused
internal implementation step. Keep a draft PR open and continue building on it
until that outcome is ready for review. Split work into a separate PR only when
the component has an independently valuable boundary.

## Issue workflow

Track each independently deliverable vertical slice as one GitHub issue. Use
separate issues for substantial follow-up work that can be reviewed and shipped
independently; keep closely coupled checklist items together. Link commits and
pull requests to their issue, and use `Closes #<issue-number>` in the PR body
when the PR completes the issue.

## Verification

Before pushing code changes, run `uv run ruff format --check .`, `uv run pytest`,
`uv run ruff check .`, and `uv run ty check` locally.
