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

## Issue workflow

Track each independently deliverable vertical slice as one GitHub issue. Use
separate issues for substantial follow-up work that can be reviewed and shipped
independently; keep closely coupled checklist items together. Link commits and
pull requests to their issue, and use `Closes #<issue-number>` in the PR body
when the PR completes the issue.
