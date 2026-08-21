# Issue tracker: GitHub

Issues and PRDs live as GitHub issues. Use the `gh` CLI inside the clone —
it infers the repo from `git remote -v`. Flag details: `gh issue <cmd> --help`.

- Create: `gh issue create --title "..." --body "..."` (heredoc for multi-line bodies).
- Read: `gh issue view <n> --comments` (add `--json` fields when labels/comments needed).
- List open: `gh issue list --state open --json number,title,labels --jq '[.[] | {number, title, labels: [.labels[].name]}]'`.
- Comment: `gh issue comment <n> --body "..."`.
- Label: `gh issue edit <n> --add-label "..."` / `--remove-label "..."`.
- Close: `gh issue close <n> --comment "..."`.

"Publish to the issue tracker" = create a GitHub issue.
"Fetch the relevant ticket" = `gh issue view <n> --comments`.
