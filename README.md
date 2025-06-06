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
        uses: pb33f/vacuum-action@v1
        with:
          openapi_path: "static/wiretap/giftshop-openapi.yaml"
          github_token: ${{ secrets.GITHUB_TOKEN }}
          # ruleset: "rules/custom-rules.yaml" << Uncomment to use a custom ruleset
```

To learn more about vacuum visit the [vacuum docs](https://quobix.com/vacuum/)