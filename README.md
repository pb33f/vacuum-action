# Official vacuum OpenAPI linter GitHub Action

Got an OpenAPI spec in your repository? Want to lint it with vacuum? This GitHub Action will do just that. 

- Super fast
- Super simple
- Super useful

All you need to do is add the action to your repo via a workflow via `pb33f/vacuum-action@v1`

There are currently two properties required. 

- `openapi_path` - The path to your OpenAPI spec file, relative to the root of your repository.
- `ruleset` - (optional) The path to a custom ruleset file, relative to the root of your repository. If not provided, the default ruleset will be used.

```yaml
name: "Lint OpenAPI spec with Vacuum"

on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main

permissions:
  contents: read
  pull-requests: write

jobs:
  vacuum-lint:
    runs-on: ubuntu-latest

    steps:
      - name: Check out repository
        uses: actions/checkout@v3

      - name: Run OpenAPI linting with vacuum
        id: lint-step
        uses: pb33f/vacuum-action@v1
        with:
          openapi_path: "path/to/your/openapi-spec.yaml"
          # ruleset: "rules/custom-rules.yaml" << Uncomment to use a custom ruleset
    
      # The following steps will add the vacuum report as a comment on the pull request.
      - name: Find existing vacuum report
        id: find-comment
        uses: peter-evans/find-comment@v3
        with:
          issue-number: ${{ github.event.pull_request.number || github.event.number }}
          comment-author: 'github-actions[bot]'
          body-includes: '<!-- vacuum-lint-report -->'

      - name: Create or update vacuum report
        if: ${{ github.event_name == 'pull_request' }}
        uses: peter-evans/create-or-update-comment@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          repository: ${{ github.repository }}
          issue-number: ${{ github.event.pull_request.number }}
          comment-id: ${{ steps.find-comment.outputs.comment-id }}
          body-path: ${{ steps.lint-step.outputs.report_path }}
          edit-mode: replace
```

To learn more about vacuum visit the [vacuum docs](https://quobix.com/vacuum/)