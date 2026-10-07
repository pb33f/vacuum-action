#!/usr/bin/env bash
set -euo pipefail

REPORT_FILE="$GITHUB_WORKSPACE/vacuum-lint-report.md"
# A second invocation must not reuse a report from an earlier lint run.
rm -f "$REPORT_FILE"

args=(lint --pipeline-output --globbed-files "$INPUT_OPENAPI_PATH"
      --min-score "$INPUT_MINIMUM_SCORE")
if [ "$INPUT_FAIL_ON_ERROR" = "true" ]; then
  args+=(--fail-severity error)
else
  args+=(--fail-severity none)
fi
if [ "$INPUT_SHOW_RULES" = "true" ]; then
  args+=(--show-rules)
fi
if [ -n "$INPUT_RULESET" ]; then
  args+=(--ruleset "$INPUT_RULESET")
fi
if [ -n "$INPUT_IGNORE_FILE" ]; then
  args+=(--ignore-file "$INPUT_IGNORE_FILE")
fi

CMD=(docker run --rm -v "$GITHUB_WORKSPACE":/work:ro
     "dshanley/vacuum:$INPUT_VACUUM_VERSION" "${args[@]}")
echo "Running: ${CMD[*]}"
lint_exit_code=0
report=$("${CMD[@]}") || lint_exit_code=$?

# Discard startup chatter, but retain file headings and markdown processing errors.
report_body=$(printf '%s\n' "$report" | awk 'seen || /^#/{seen=1; print}')
if [ -n "$report_body" ]; then
  {
    echo '<!-- vacuum-lint-report -->'
    echo
    printf '%s\n' "$report_body"
  } > "$REPORT_FILE"

  # Vacuum v0.30.6 does not apply --min-score in its multi-file path.
  # Check each reported score as a fallback without masking a CLI failure.
  if [ "$lint_exit_code" -eq 0 ] && ! printf '%s\n' "$report_body" | awk -F '`' -v minimum="$INPUT_MINIMUM_SCORE" '
    /^> vacuum has graded this OpenAPI specification with a score of `/ {
      if ($2 + 0 < minimum + 0) failed = 1
    }
    END { exit failed ? 1 : 0 }
  '; then
    echo "An OpenAPI specification scored below the required minimum of $INPUT_MINIMUM_SCORE." >&2
    lint_exit_code=1
  fi

  if [ "$INPUT_PRINT_LOGS" = "true" ]; then
    cat "$REPORT_FILE"
  fi
  echo 'report_path=vacuum-lint-report.md' >> "$GITHUB_OUTPUT"
  echo 'has_report=true' >> "$GITHUB_OUTPUT"
else
  # A command error is useful in the logs, but is not a lint report to publish.
  printf '%s\n' "$report" >&2
  echo 'has_report=false' >> "$GITHUB_OUTPUT"
fi
echo "lint_exit_code=$lint_exit_code" >> "$GITHUB_OUTPUT"
