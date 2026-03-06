"""
CoderAgent: Generates code files based on an approved implementation plan.

Takes a PlannerOutput and instructs the LLM to produce complete, working code,
then parses the response and writes each file to a local workspace directory.
"""

import os
import re
import logging
from dataclasses import dataclass, field
from pathlib import Path

from agentscope.model import OpenAIChatModel

from tools.jira_tool import JiraTicket
from agents.planner_agent import PlannerOutput

logger = logging.getLogger(__name__)

WORKSPACE_ROOT = Path("workspace")
MAX_CORRECTION_ATTEMPTS = 3

SYSTEM_PROMPT = """\
You are an expert software engineer implementing code for ScopeSentinel, \
an autonomous software delivery platform.

You will be given a Jira ticket summary and an approved implementation plan. \
Your job is to write ALL the code needed to implement it completely.

CRITICAL output format rules:
1. For every file you create, start with a line like:
   ### `relative/path/to/file.ext`
   Then immediately follow with a fenced code block containing the FULL file contents.
2. Never abbreviate code with comments like "# ... rest of code". Always write the complete file.
3. Include a `README.md` as the last file, summarizing what was built and how to run it.
4. Do not include any explanation text outside of the file blocks.

Example:
### `src/main.py`
```python
def hello():
    print("Hello!")
```

### `README.md`
```markdown
# My Project
...
```
"""


def _build_coding_prompt(ticket: JiraTicket, plan: PlannerOutput) -> str:
    steps_text = "\n".join(f"{i}. {s}" for i, s in enumerate(plan.steps, 1))
    return (
        f"**Ticket:** {ticket.id} — {ticket.summary}\n\n"
        f"**Architecture Notes:**\n{plan.architecture_notes}\n\n"
        f"**Implementation Steps:**\n{steps_text}\n\n"
        "Now implement ALL of the above steps as complete, runnable code files."
    )


def _parse_files(raw: str) -> dict[str, str]:
    """
    Parse the LLM response into {relative_path: file_content} mapping.

    Looks for blocks of the form:
        ### `path/to/file.ext`
        ```[lang]
        <content>
        ```
    """
    files: dict[str, str] = {}

    # Pattern: ### `filepath`  (optional whitespace) ``` [lang] \n content \n ```
    pattern = re.compile(
        r"###\s+`([^`]+)`\s*\n"       # ### `filepath`
        r"```[^\n]*\n"                  # ``` or ```python etc.
        r"(.*?)"                        # file content (non-greedy)
        r"```",                         # closing ```
        re.DOTALL
    )

    for match in pattern.finditer(raw):
        filepath = match.group(1).strip()
        content  = match.group(2)
        # Normalise — remove leading/trailing blank lines but keep internal ones
        files[filepath] = content.strip("\n") + "\n"

    return files


@dataclass
class CoderOutput:
    """Result of a CoderAgent run."""
    ticket_id:      str
    workspace_path: str        # Absolute path to the workspace directory
    files_written:  list[str] = field(default_factory=list)  # relative paths
    raw_response:   str = ""


class CoderAgent:
    """
    An agent that turns an approved PlannerOutput into actual code files
    written to workspace/<ticket_id>/.
    """

    def __init__(self, model: OpenAIChatModel):
        self.model = model

    async def code(
        self,
        ticket: JiraTicket,
        plan: PlannerOutput,
        workspace_override: "Path | str | None" = None,
    ) -> CoderOutput:
        """
        Generate code for the given ticket and approved plan.

        Args:
            ticket:             The original JiraTicket.
            plan:               The HITL-approved PlannerOutput.
            workspace_override: If provided, write files here instead of workspace/<id>/.

        Returns:
            A CoderOutput describing what was written and where.
        """
        workspace = (
            Path(workspace_override).resolve()
            if workspace_override
            else WORKSPACE_ROOT / ticket.id
        )
        workspace.mkdir(parents=True, exist_ok=True)
        logger.info(f"CoderAgent: workspace at '{workspace}'")

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": _build_coding_prompt(ticket, plan)},
        ]

        logger.info(f"CoderAgent: calling LLM to generate code for {ticket.id}...")
        response = await self.model(messages)

        raw = ""
        if hasattr(response, "content") and isinstance(response.content, list):
            for block in response.content:
                if isinstance(block, dict) and block.get("type") == "text":
                    raw = block["text"]
                    break
        if not raw:
            raw = str(response)

        files = _parse_files(raw)

        if not files:
            logger.warning("CoderAgent: no file blocks found in LLM response.")

        files_written: list[str] = []
        for rel_path, content in files.items():
            dest = workspace / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            files_written.append(rel_path)
            logger.info(f"  ✍️  Written: {dest}")

        return CoderOutput(
            ticket_id=ticket.id,
            workspace_path=str(workspace.resolve()),
            files_written=files_written,
            raw_response=raw,
        )

    async def code_with_validation(
        self,
        ticket: JiraTicket,
        plan: PlannerOutput,
        workspace_override: "Path | str | None" = None,
    ) -> CoderOutput:
        """
        Generate code, then validate it in a Docker sandbox.
        If validation fails, feed errors back to the LLM and retry
        (up to MAX_CORRECTION_ATTEMPTS times).

        Args:
            ticket: The original JiraTicket.
            plan:   The HITL-approved PlannerOutput.

        Returns:
            The final CoderOutput (after self-correction if needed).
        """
        from sandbox.sandbox_runner import SandboxRunner
        from sandbox.validator import CodeValidator

        output = await self.code(ticket, plan, workspace_override=workspace_override)
        workspace = Path(output.workspace_path)

        try:
            runner = SandboxRunner(workspace)
        except RuntimeError as e:
            logger.warning(f"CoderAgent: Docker unavailable, skipping validation. {e}")
            return output

        validator = CodeValidator(runner)
        conversation: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": _build_coding_prompt(ticket, plan)},
            {"role": "assistant", "content": output.raw_response},
        ]

        for attempt in range(1, MAX_CORRECTION_ATTEMPTS + 1):
            logger.info(f"CoderAgent: running sandbox validation (attempt {attempt})...")
            result = validator.validate()

            if result.passed:
                logger.info(f"CoderAgent: validation passed on attempt {attempt}. ✅")
                break

            logger.warning(
                f"CoderAgent: validation failed (attempt {attempt}/{MAX_CORRECTION_ATTEMPTS}).\n"
                f"{result.output[:800]}"
            )

            if attempt == MAX_CORRECTION_ATTEMPTS:
                logger.error("CoderAgent: max correction attempts reached. Proceeding with last output.")
                break

            # Self-correction: send errors back to the LLM
            correction_prompt = (
                f"Your generated code failed validation (attempt {attempt}).\n\n"
                f"Errors:\n{result.output}\n\n"
                "Please fix ALL issues. Rewrite every affected file in full using the same "
                "### `filepath` + fenced code block format. Do not include explanation text."
            )
            conversation.append({"role": "user", "content": correction_prompt})

            logger.info("CoderAgent: requesting self-correction from LLM...")
            response = await self.model(conversation)

            raw = ""
            if hasattr(response, "content") and isinstance(response.content, list):
                for block in response.content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        raw = block["text"]
                        break
            if not raw:
                raw = str(response)

            conversation.append({"role": "assistant", "content": raw})

            # Overwrite files with corrected versions
            files = _parse_files(raw)
            files_written = []
            for rel_path, content in files.items():
                dest = workspace / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content, encoding="utf-8")
                files_written.append(rel_path)
                logger.info(f"  ✍️  Corrected: {dest}")

            output = CoderOutput(
                ticket_id=ticket.id,
                workspace_path=str(workspace),
                files_written=files_written,
                raw_response=raw,
            )

        return output
