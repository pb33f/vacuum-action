# Official vacuum OpenAPI linter GitHub Action

Got an **OpenAPI** spec in your repository? Want to lint it with vacuum? This GitHub Action will do just that. 

- Super fast
- Super simple
- Super useful

All you need to do is add the action to your repo via a workflow via `pb33f/vacuum-action@v2`

Here are the configurable properties you can use in your workflow:

| Property         | Type      | Required | Description                                                                                                                                                  |
|------------------|-----------|----------|--------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `openapi_path`   | `string`  | **true** | The path or glob pattern for your OpenAPI spec file(s), relative to the root of your repository. Brace patterns such as `specs/*.{yaml,yml}` are supported.  |
| `github_token`   | `string`  | _false_  | Token with `pull-requests: write` to post comments on pull requests. Omit to skip comments, including when testing untrusted fork PRs with a read-only token. |
| `ruleset`        | `string`  | _false_  | The path to a custom ruleset file, relative to the root of your repository. If not provided, the default ruleset will be used.                               | 
| `ignore_file`    | `string`  | _false_  | Path to a Vacuum ignore file relative to the repository root. Passed to `--ignore-file` for single files or globs. Defaults to empty (no ignore file). |
| `show_rules`     | `boolean` | _false_  | If set to `true`, the action will show the rules that were applied. Defaults to `false`                                                                      |
| `fail_on_error`  | `boolean` | _false_  | If set to `true`, the action will fail if any errors are detected in the OpenAPI spec. Defaults to `true`                                                    |
| `minimum_score`  | `number`  | _false_  | The minimum score required for each matched specification. Defaults to `70`; still applies when `fail_on_error` is `false`.                                  |
| `print_logs`     | `boolean` | _false_  | If set to `true`, the action will print the markdown report to the runner logs. Defaults to `true`                                                           |
| `vacuum_version` | `string`  | _false_  | The vacuum Docker image tag to use. Defaults to `latest`.                                                                                                    |

---

## Ignore specific findings

An ignore file maps rule IDs to the result paths to suppress. For example:

```yaml
oas3-missing-example:
  - $.components.schemas.Burger.properties
```

Set `ignore_file: "vacuum.ignore.yaml"` to use this file. The same ignore file applies to every specification matched by `openapi_path`. Other findings and the configured minimum score still apply. The file must be inside the checked-out workspace; paths with spaces are supported. A missing or malformed ignore file fails the action.

## Example Workflow

```yaml
name: "Lint OpenAPI spec with vacuum"

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
    name: Run OpenAPI linting with vacuum
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v3

      - name: Run OpenAPI lint with vacuum
        uses: pb33f/vacuum-action@v2
        with:
          openapi_path: "specs/openapi.yaml"
          github_token: ${{ secrets.GITHUB_TOKEN }}
```

## Example Workflow with optional parameters

```yaml
name: "Lint OpenAPI spec with vacuum"

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
    name: Run OpenAPI linting with vacuum
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v3

      - name: Run OpenAPI lint with vacuum
        uses: pb33f/vacuum-action@v2
        with:
          openapi_path: "specs/*.{yaml,yml}"
          ruleset: "rulesets/vacuum-ruleset.yaml"
          ignore_file: "vacuum.ignore.yaml"
          show_rules: true
          fail_on_error: true
          minimum_score: 90
          print_logs: true
          vacuum_version: "v0.30.6"
          github_token: ${{ secrets.GITHUB_TOKEN }}
```

Pull request comments are created or updated only for pull request events when `github_token` is provided. On other events, the action still lints and fails the job when vacuum reports a failure or any specification falls below `minimum_score`.

The action writes `vacuum-lint-report.md` in the workspace when Vacuum produces a markdown report, including when linting fails. It handles PR comments before reporting the lint failure. An unmatched glob or command startup error fails without creating a report; any report from a previous invocation is removed.

## Development

Run the dependency-free shell regression suite with `python3 -m unittest discover -s tests -v`. To also exercise the released Docker image, run `VACUUM_ACTION_DOCKER_TESTS=1 python3 -m unittest discover -s tests -v` with Docker available. CI runs these tests and the composite action on both pull request and push events; fork PRs skip comment writes.
