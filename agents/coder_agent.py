"""
CoderAgent: Generates code files based on an approved implementation plan.

Takes a PlannerOutput and instructs the LLM to produce complete, working code,
then parses the response and writes each file to a local workspace directory.
"""

import os
import re
import shutil
import logging
from dataclasses import dataclass, field
from pathlib import Path

from agentscope.model import OpenAIChatModel
from agentscope.mcp import StdIOStatefulClient

from agents.planner_agent import PlannerOutput

logger = logging.getLogger(__name__)

WORKSPACE_ROOT = Path("workspace")
MAX_CORRECTION_ATTEMPTS = 3

SYSTEM_PROMPT = """\
You are an expert software engineer implementing code for ScopeSentinel, \
an autonomous software delivery platform.

You will be given a Jira ticket summary and an approved implementation plan. \
Your job is to implement it completely.

CRITICAL output format rules:
1. To CREATE or MODIFY a file:
   ### `relative/path/to/file.ext`
   Then immediately follow with a fenced code block containing the FULL file contents.
2. To DELETE a file or directory:
   ### DELETE `relative/path/to/delete`
   (no code block needed — just this one line)
3. Never abbreviate code with "# ... rest of code". Always write the complete file.
4. Include a `README.md` summarizing what was built/changed.
5. Do not include explanation text outside the file/delete blocks.

Example:
### DELETE `old_folder/`
### `src/main.py`
```python
def hello():
    print("Hello!")
```
### `README.md`
```markdown
# My Project
```
"""


def _build_coding_prompt(ticket_id: str, ticket_content: str, plan: PlannerOutput) -> str:
    steps_text = "\n".join(f"{i}. {s}" for i, s in enumerate(plan.steps, 1))
    return (
        f"**Ticket:** {ticket_id}\n"
        f"**Ticket Content:**\n{ticket_content}\n\n"
        f"**Architecture Notes:**\n{plan.architecture_notes}\n\n"
        f"**Implementation Steps:**\n{steps_text}\n\n"
        "Now implement ALL of the above steps as complete, runnable code files."
    )


def _parse_files(raw: str) -> dict[str, str]:
    """
    Parse the LLM response into {relative_path: file_content} mapping.
    Looks for: ### `filepath` followed by a fenced code block.
    """
    files: dict[str, str] = {}
    pattern = re.compile(
        r"###\s+`([^`]+)`\s*\n"
        r"```[^\n]*\n"
        r"(.*?)"
        r"```",
        re.DOTALL
    )
    for match in pattern.finditer(raw):
        filepath = match.group(1).strip()
        content  = match.group(2)
        files[filepath] = content.strip("\n") + "\n"
    return files


def _parse_deletions(raw: str) -> list[str]:
    """
    Parse ### DELETE `path` lines from the LLM response.
    Returns a list of relative paths to delete.
    """
    pattern = re.compile(r"###\s+DELETE\s+`([^`]+)`", re.IGNORECASE)
    return [m.group(1).strip() for m in pattern.finditer(raw)]


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
        ticket_id: str,
        ticket_content: str,
        plan: PlannerOutput,
        workspace_override: "Path | str | None" = None,
    ) -> CoderOutput:
        """
        Generate code for the given ticket and approved plan.

        Args:
            ticket_id:          The original Jira ticket ID.
            ticket_content:     The text content of the Jira ticket.
            plan:               The HITL-approved PlannerOutput.
            workspace_override: If provided, write files here instead of workspace/<id>/.

        Returns:
            A CoderOutput describing what was written and where.
        """
        workspace = (
            Path(workspace_override).resolve()
            if workspace_override
            else WORKSPACE_ROOT / ticket_id
        )
        workspace.mkdir(parents=True, exist_ok=True)
        logger.info(f"CoderAgent: workspace at '{workspace}'")

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": _build_coding_prompt(ticket_id, ticket_content, plan)},
        ]

        logger.info(f"CoderAgent: calling LLM to generate code for {ticket_id}...")
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
        deletions = _parse_deletions(raw)

        if not files and not deletions:
            logger.warning("CoderAgent: no file or delete blocks found in LLM response.")

        # Process deletions first
        files_written: list[str] = []
        for rel_path in deletions:
            target = workspace / rel_path
            if target.exists():
                if target.is_dir():
                    shutil.rmtree(target)
                    logger.info(f"  🗑️  Deleted dir : {target}")
                else:
                    target.unlink()
                    logger.info(f"  🗑️  Deleted file: {target}")
            else:
                logger.warning(f"  ⚠️  DELETE target not found: {target}")

        # Write / overwrite files
        for rel_path, content in files.items():
            dest = workspace / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            files_written.append(rel_path)
            logger.info(f"  ✍️  Written: {dest}")

        return CoderOutput(
            ticket_id=ticket_id,
            workspace_path=str(workspace.resolve()),
            files_written=files_written,
            raw_response=raw,
        )

    async def code_with_validation(
        self,
        ticket_id: str,
        ticket_content: str,
        plan: PlannerOutput,
        mcp_client: StdIOStatefulClient,
    ) -> CoderOutput:
        """
        Generate code, then validate it in a Docker sandbox.
        If validation fails, feed errors back to the LLM and retry.
        Also uses MCP tools to prepare git branch, commit, push, and PR.

        Args:
            ticket_id:      The original Jira ticket ID.
            ticket_content: The formatted jira ticket content fetched from MCP.
            plan:           The HITL-approved PlannerOutput.
            mcp_client:     The MCP client to interact with Git and Github tools.

        Returns:
            The final CoderOutput (after self-correction if needed).
        """
        from sandbox.sandbox_runner import SandboxRunner
        from sandbox.validator import CodeValidator

        # 1. Prepare Git Branch via MCP
        workspace_path = None
        try:
            prep_func = await mcp_client.get_callable_function("prepare_git_branch")
            res = await prep_func(ticket_id=ticket_id)
            if hasattr(res, 'content'):
                res_text = res.content[0]['text']
            else:
                res_text = str(res)
            
            # Very basic extraction: "Branch prepared at /path"
            if " at " in res_text:
                workspace_path = res_text.split(" at ")[-1].strip()
            logger.info(f"CoderAgent: MCP prepare_git_branch returned: {res_text}")
        except Exception as e:
            logger.warning(f"CoderAgent: Failed to prepare branch via MCP: {e}")

        # 2. Code and Validate
        output = await self.code(ticket_id, ticket_content, plan, workspace_override=workspace_path)
        workspace = Path(output.workspace_path)

        try:
            runner = SandboxRunner(workspace)
        except RuntimeError as e:
            logger.warning(f"CoderAgent: Docker unavailable, skipping validation. {e}")
            runner = None
            
        if runner:
            validator = CodeValidator(runner)
            conversation: list[dict] = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": _build_coding_prompt(ticket_id, ticket_content, plan)},
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
                    ticket_id=ticket_id,
                    workspace_path=str(workspace),
                    files_written=files_written,
                    raw_response=raw,
                )

        # 3. Commit, Push, and Create PR via MCP
        if workspace_path is not None:
            try:
                commit_func = await mcp_client.get_callable_function("commit_and_push")
                res = await commit_func(ticket_id=ticket_id, summary=plan.summary)
                logger.info(f"CoderAgent: Commit and push returned: {res}")

                pr_func = await mcp_client.get_callable_function("create_pull_request")
                res = await pr_func(ticket_id=ticket_id, plan=plan.raw_plan, branch_name=f"sentinel/{ticket_id}")
                logger.info(f"CoderAgent: Create PR returned: {res}")
            except Exception as e:
                logger.warning(f"CoderAgent: Failed to finalize PR via MCP: {e}")

        return output
