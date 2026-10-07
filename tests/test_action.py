"""Run with python3 -m unittest discover -s tests -v (no dependencies)."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
REPORT = "## [vacuum](https://quobix.com/vacuum/) OpenAPI quality report\n"


def scored_report(score):
    return REPORT + (
        "> vacuum has graded this OpenAPI specification with a score of "
        f"`{score}` out of a possible 100\n"
    )


class LintFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="vacuum action ")
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.report = self.workspace / "vacuum-lint-report.md"
        self.output = self.workspace / "outputs"
        self.summary = self.workspace / "job summary.md"
        self.env = dict(os.environ, **{
            "GITHUB_WORKSPACE": str(self.workspace),
            "GITHUB_OUTPUT": str(self.output),
            "INPUT_OPENAPI_PATH": "sample-specs/*shop.{yaml,yml}",
            "INPUT_MINIMUM_SCORE": "70",
            "INPUT_FAIL_ON_ERROR": "true",
            "INPUT_SHOW_RULES": "false",
            "INPUT_RULESET": "",
            "INPUT_PRINT_LOGS": "false",
            "INPUT_STEP_SUMMARY": "false",
            "GITHUB_STEP_SUMMARY": str(self.summary),
            "INPUT_VACUUM_VERSION": "v0.30.6",
        })
        self.bin = self.workspace / "bin"
        self.bin.mkdir()
        docker = self.bin / "docker"
        docker.write_text("""#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
Path(os.environ['GITHUB_WORKSPACE'], 'args.json').write_text(json.dumps(sys.argv[1:]))
sys.stdout.write(os.environ['TEST_STDOUT'])
sys.stderr.write(os.environ['TEST_STDERR'])
sys.exit(int(os.environ['TEST_EXIT_CODE']))
""")
        docker.chmod(0o755)
        self.env["PATH"] = str(self.bin) + os.pathsep + self.env["PATH"]

    def run_lint(self, stdout=REPORT, exit_code=0, stderr="", **inputs):
        self.env.update({f"INPUT_{key.upper()}": str(value) for key, value in inputs.items()})
        self.env.update(TEST_STDOUT=stdout, TEST_STDERR=stderr, TEST_EXIT_CODE=str(exit_code))
        self.output.write_text("")
        result = subprocess.run(
            ["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", str(ROOT / "scripts/lint.sh")],
            cwd=self.workspace, env=self.env, capture_output=True, text=True,
        )
        # Lint status is deferred until the composite's final step.
        self.assertEqual(result.returncode, 0, result.stderr)
        outputs = dict(line.split("=", 1) for line in self.output.read_text().splitlines())
        return outputs, result


class LintTests(LintFixture):
    def test_glob_and_options_are_literal_arguments(self):
        path = "specs with spaces/**/*.{yaml,yml,json}"
        ruleset = 'rules/$(touch injected) "custom".yaml'
        outputs, _ = self.run_lint(openapi_path=path, ruleset=ruleset, show_rules="true")
        args = json.loads((self.workspace / "args.json").read_text())
        self.assertEqual(args, [
            "run", "--rm", "-v", f"{self.workspace}:/work:ro", "dshanley/vacuum:v0.30.6",
            "lint", "--pipeline-output", "--globbed-files", path,
            "--min-score", "70", "--fail-severity", "error", "--show-rules", "--ruleset", ruleset,
        ])
        self.assertFalse((self.workspace / "injected").exists())
        self.assertEqual(outputs["lint_exit_code"], "0")

    def test_failure_preserves_report_and_defers_exit(self):
        outputs, result = self.run_lint("startup chatter\n" + REPORT, exit_code=2)
        self.assertEqual(outputs, {
            "report_path": "vacuum-lint-report.md", "has_report": "true", "lint_exit_code": "2",
        })
        self.assertEqual(self.report.read_text(), "<!-- vacuum-lint-report -->\n\n" + REPORT)
        self.assertNotIn(REPORT, result.stdout)

    def test_print_logs(self):
        _, result = self.run_lint(print_logs="true")
        self.assertIn(self.report.read_text(), result.stdout)

    def test_summary_is_opt_in_and_independent_of_logs(self):
        self.summary.write_text("Existing summary\n")
        self.run_lint(print_logs="true")
        self.assertEqual(self.summary.read_text(), "Existing summary\n")
        _, result = self.run_lint(step_summary="true", print_logs="false")
        self.assertEqual(self.summary.read_text(), "Existing summary\n" + self.report.read_text())
        self.assertNotIn(REPORT, result.stdout)

    def test_summary_is_written_before_lint_failure(self):
        for exit_code in [0, 2]:
            with self.subTest(exit_code=exit_code):
                self.summary.write_text("")
                outputs, _ = self.run_lint(scored_report(10), exit_code=exit_code, step_summary="true")
                self.assertEqual(outputs["lint_exit_code"], str(exit_code or 1))
                self.assertEqual(self.summary.read_text(), self.report.read_text())

    def test_no_report_leaves_existing_summary_untouched(self):
        self.summary.write_text("Earlier step\n")
        for message, exit_code in [("No files matched\n", 2), ("", 125)]:
            with self.subTest(exit_code=exit_code):
                self.run_lint(message, exit_code=exit_code, step_summary="true")
                self.assertEqual(self.summary.read_text(), "Earlier step\n")

    def test_repeated_reports_append_to_summary(self):
        self.run_lint(scored_report(99), step_summary="true")
        first = self.summary.read_text()
        self.run_lint(scored_report(70), step_summary="true")
        self.assertEqual(self.summary.read_text(), first + self.report.read_text())

    def test_no_match_does_not_publish_diagnostic_or_stale_report(self):
        self.run_lint()
        outputs, result = self.run_lint("Please supply a specification\n", exit_code=2)
        self.assertEqual(outputs, {"has_report": "false", "lint_exit_code": "2"})
        self.assertFalse(self.report.exists())
        self.assertIn("Please supply a specification", result.stderr)

    def test_docker_error_without_stdout_does_not_create_report(self):
        outputs, result = self.run_lint("", exit_code=125, stderr="Cannot connect to Docker\n")
        self.assertEqual(outputs, {"has_report": "false", "lint_exit_code": "125"})
        self.assertFalse(self.report.exists())
        self.assertIn("Cannot connect to Docker", result.stderr)

    def test_multifile_minimum_applies_to_every_score(self):
        body = "# first.yaml\n" + scored_report(99) + "# second.yml\n" + scored_report(69)
        outputs, _ = self.run_lint(body)
        self.assertEqual(outputs["lint_exit_code"], "1")
        self.assertIn(body, self.report.read_text())

    def test_minimum_boundary_and_disabled_threshold(self):
        for score, minimum, expected in [(70, 70, "0"), (0, 70, "1"), (0, 0, "0"), (100, 101, "1")]:
            with self.subTest(score=score, minimum=minimum):
                outputs, _ = self.run_lint(scored_report(score), minimum_score=minimum)
                self.assertEqual(outputs["lint_exit_code"], expected)

    def test_existing_cli_failure_is_preserved(self):
        outputs, _ = self.run_lint(scored_report(10), exit_code=2)
        self.assertEqual(outputs["lint_exit_code"], "2")

    def test_fail_on_error_false_keeps_minimum_score(self):
        outputs, _ = self.run_lint(scored_report(69), fail_on_error="false")
        args = json.loads((self.workspace / "args.json").read_text())
        self.assertEqual(args[args.index("--fail-severity") + 1], "none")
        self.assertEqual(outputs["lint_exit_code"], "1")

    def test_multifile_processing_errors_remain_in_report(self):
        body = "## ❌ Error processing `invalid.yaml`\n\n> invalid specification\n"
        outputs, _ = self.run_lint(body, exit_code=2)
        self.assertEqual(outputs["has_report"], "true")
        self.assertIn(body, self.report.read_text())


@unittest.skipUnless(os.environ.get("VACUUM_ACTION_DOCKER_TESTS") == "1", "set VACUUM_ACTION_DOCKER_TESTS=1")
class DockerTests(LintFixture):
    """Run the same shell against the released image in addition to the stub tests."""

    def setUp(self):
        super().setUp()
        self.env["PATH"] = os.environ["PATH"]
        shutil.copytree(ROOT / "sample-specs", self.workspace / "sample-specs")

    def test_multifile_summary_survives_score_failure(self):
        outputs, _ = self.run_lint(minimum_score="101", step_summary="true")
        self.assertEqual(outputs["lint_exit_code"], "1")
        self.assertEqual(self.summary.read_text(), self.report.read_text())
        self.assertIn("sample-specs/burgershop.yaml", self.summary.read_text())
        self.assertIn("sample-specs/frieshop.yaml", self.summary.read_text())

    def test_docker_scenarios(self):
        cases = [
            ({}, "0", True),
            ({"minimum_score": "101"}, "1", True),
            ({"openapi_path": "sample-specs/burgershop.yaml", "minimum_score": "101"}, "1", True),
            ({"openapi_path": "sample-specs/absent.{yaml,yml}"}, "2", False),
            ({"openapi_path": "sample-specs/burgershop.yaml", "ruleset": "sample-specs/ruleset.yaml"}, "0", True),
        ]
        defaults = {key: value for key, value in self.env.items() if key.startswith("INPUT_")}
        for inputs, status, has_report in cases:
            with self.subTest(inputs=inputs):
                self.env.update(defaults)
                outputs, result = self.run_lint(**inputs)
                self.assertEqual(outputs["lint_exit_code"], status, result.stderr)
                self.assertEqual(outputs["has_report"], str(has_report).lower())
                self.assertEqual(self.report.exists(), has_report)
                if not inputs:
                    self.assertIn("sample-specs/burgershop.yaml", self.report.read_text())
                    self.assertIn("sample-specs/frieshop.yaml", self.report.read_text())

    def test_recursive_glob_with_spaces_and_mixed_extensions(self):
        nested = self.workspace / "specs with spaces" / "nested"
        nested.mkdir(parents=True)
        for filename in ["first spec.yaml", "second spec.yml"]:
            shutil.copy(ROOT / "sample-specs/frieshop.yaml", nested / filename)
        outputs, _ = self.run_lint(openapi_path="specs with spaces/**/*.{yaml,yml}")
        self.assertEqual(outputs["lint_exit_code"], "0")
        for filename in ["first spec.yaml", "second spec.yml"]:
            self.assertIn(filename, self.report.read_text())

    def test_lint_errors_and_fail_on_error_false(self):
        specs = self.workspace / "errors"
        specs.mkdir()
        for filename in ["first.json", "second.json"]:
            (specs / filename).write_text(json.dumps({
                "openapi": "3.0.3", "info": {"title": filename, "version": "1.0"}, "paths": {},
            }))
        (self.workspace / "rules.json").write_text(json.dumps({
            "extends": [["spectral:oas", "off"]],
            "rules": {"require-description": {
                "description": "Description is required", "severity": "error",
                "given": "$.info", "then": {"field": "description", "function": "truthy"},
            }},
        }))
        for fail_on_error in ["true", "false"]:
            with self.subTest(fail_on_error=fail_on_error):
                outputs, result = self.run_lint(
                    openapi_path="errors/*.json", ruleset="rules.json",
                    minimum_score="0", fail_on_error=fail_on_error,
                )
                self.assertEqual(outputs["lint_exit_code"] != "0", fail_on_error == "true", result.stderr)
                self.assertEqual(outputs["has_report"], "true")
                self.assertIn("require-description", self.report.read_text())


if __name__ == "__main__":
    unittest.main()
