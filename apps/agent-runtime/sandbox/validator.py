"""
CodeValidator: Runs syntax checks, linting, and tests inside the sandbox.

Detects what's in the workspace and runs appropriate checks:
  - Python files → py_compile syntax check + flake8
  - test files   → pytest
  - Shell files  → bash -n syntax check
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from sandbox.sandbox_runner import SandboxRunner, SandboxResult

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Aggregated result of all validation steps."""
    passed: bool
    output: str         # Combined output from all checks (stdout + stderr)
    checks_run: list[str]   # Names of checks that were attempted


class CodeValidator:
    """
    Validates generated code inside a Docker sandbox.

    Runs checks in sequence; stops and reports on the first failure.
    """

    def __init__(self, runner: SandboxRunner):
        self.runner = runner

    def validate(self) -> ValidationResult:
        """
        Detect languages present and run appropriate validation checks.

        Returns:
            A ValidationResult with pass/fail status and combined output.
        """
        workspace = self.runner.workspace_path
        checks_run: list[str] = []
        all_output: list[str] = []

        py_files = list(workspace.rglob("*.py"))
        sh_files = list(workspace.rglob("*.sh"))
        has_tests = bool(
            list(workspace.rglob("test_*.py")) or
            list(workspace.rglob("*_test.py")) or
            (workspace / "tests").exists()
        )

        # --- 1. Python syntax check ---
        if py_files:
            rel_paths = " ".join(
                str(p.relative_to(workspace)) for p in py_files
            )
            result = self._run_check(
                name="Python syntax (py_compile)",
                command=f"python -m py_compile {rel_paths}",
                checks_run=checks_run,
                all_output=all_output,
            )
            if not result.success:
                return self._fail(all_output, checks_run)

        # --- 2. Shell script syntax check ---
        if sh_files:
            for sh in sh_files:
                rel = str(sh.relative_to(workspace))
                result = self._run_check(
                    name=f"Shell syntax ({rel})",
                    command=f"bash -n {rel}",
                    checks_run=checks_run,
                    all_output=all_output,
                )
                if not result.success:
                    return self._fail(all_output, checks_run)

        # --- 3. Flake8 linting (Python only) ---
        if py_files:
            result = self._run_check(
                name="Flake8 lint",
                command="pip install flake8 -q && flake8 --max-line-length=120 .",
                checks_run=checks_run,
                all_output=all_output,
            )
            if not result.success:
                return self._fail(all_output, checks_run)

        # --- 4. Pytest (if test files found) ---
        if has_tests:
            result = self._run_check(
                name="Pytest",
                command="pip install pytest -q && pytest -v",
                checks_run=checks_run,
                all_output=all_output,
            )
            if not result.success:
                return self._fail(all_output, checks_run)

        if not checks_run:
            logger.info("CodeValidator: no applicable files found, skipping validation.")
            return ValidationResult(
                passed=True,
                output="No applicable files to validate.",
                checks_run=[],
            )

        combined = "\n\n".join(all_output)
        logger.info(f"CodeValidator: all {len(checks_run)} check(s) passed.")
        return ValidationResult(passed=True, output=combined, checks_run=checks_run)

    # ------------------------------------------------------------------ helpers

    def _run_check(
        self,
        name: str,
        command: str,
        checks_run: list[str],
        all_output: list[str],
    ) -> SandboxResult:
        logger.info(f"CodeValidator: running '{name}'...")
        checks_run.append(name)
        result = self.runner.run(command)
        entry = f"[{name}]\n{result.summary()}"
        all_output.append(entry)
        if result.success:
            logger.info(f"  ✅ {name} passed")
        else:
            logger.warning(f"  ❌ {name} failed (exit {result.exit_code})")
        return result

    def _fail(self, all_output: list[str], checks_run: list[str]) -> ValidationResult:
        return ValidationResult(
            passed=False,
            output="\n\n".join(all_output),
            checks_run=checks_run,
        )
