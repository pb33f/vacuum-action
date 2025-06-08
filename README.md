# Official vacuum OpenAPI linter GitHub Action

Got an **OpenAPI** spec in your repository? Want to lint it with vacuum? This GitHub Action will do just that. 

- Super fast
- Super simple
- Super useful

All you need to do is add the action to your repo via a workflow via `pb33f/vacuum-action@v2`

Here are the configurable properties you can use in your workflow:

| Property         | Type      | Required | Description                                                                                                                    |
|------------------|-----------|----------|--------------------------------------------------------------------------------------------------------------------------------|
| `openapi_path`   | `string`  | **true** | The path to your OpenAPI spec file, relative to the root of your repository.                                                   |
| `github_token`   | `string`  | **true** | The GitHub token to use for authentication. This is required to post comments on pull requests.                                |
| `ruleset`        | `string`  | _false_  | The path to a custom ruleset file, relative to the root of your repository. If not provided, the default ruleset will be used. | 
| `show_rules`     | `boolean` | _false_  | If set to `true`, the action will show the rules that were applied. Defaults to `false`                                        |
| `fail_on_error`  | `boolean` | _false_  | If set to `true`, the action will fail if any errors are detected in the OpenAPI spec. Defaults to `true`                      |
| `minimum_score`  | `number`  | _false_  | The minimum score required to not fail the check. Defaults to `70`.                                                            |
| `print_logs`     | `boolean` | _false_  | If set to `true`, the action will print the markdown report to the runner logs. Defaults to `true`                             |

---

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
          openapi_path: "specs/openapi.yaml"
          ruleset: "rulesets/vacuum-ruleset.yaml"
          show_rules: true
          fail_on_error: true
          minimum_score: 90
          print_logs: true
          github_token: ${{ secrets.GITHUB_TOKEN }}
```