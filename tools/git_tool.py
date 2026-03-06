"""
GitTool: Manages a sentinel feature branch and pushes generated code.

The local repo (GITHUB_REPO_LOCAL_PATH / GITHUB_REPO_NAME) is the workspace.
No separate workspace directory is needed.

Workflow:
  1. git_tool.prepare_branch(ticket_id)  → checks out sentinel branch, returns repo path
  2. CoderAgent writes files directly into that path
  3. git_tool.commit_and_push(ticket_id, summary) → commits everything and pushes
"""

import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from git import Repo, InvalidGitRepositoryError, GitCommandError
from github import Github

logger = logging.getLogger(__name__)

BRANCH_PREFIX = "sentinel"


@dataclass
class GitResult:
    """Result of a git branch + commit + push operation."""
    branch_name: str
    commit_sha: str
    remote_url: str


class GitTool:
    """
    Manages a sentinel feature branch in the target repo.
    The local repo directory acts directly as the code workspace.
    """

    def __init__(self):
        load_dotenv()
        self.token      = os.environ.get("GITHUB_TOKEN", "")
        self.repo_owner = os.environ.get("GITHUB_REPO_OWNER", "")
        self.repo_name  = os.environ.get("GITHUB_REPO_NAME", "")
        base_path       = os.environ.get("GITHUB_REPO_LOCAL_PATH", "")

        if not all([self.token, self.repo_owner, self.repo_name, base_path]):
            raise EnvironmentError(
                "Missing Git config. Please set GITHUB_TOKEN, GITHUB_REPO_OWNER, "
                "GITHUB_REPO_NAME, and GITHUB_REPO_LOCAL_PATH in your .env file."
            )

        # Canonical local path is always GITHUB_REPO_LOCAL_PATH / GITHUB_REPO_NAME
        self.local_path = (Path(base_path) / self.repo_name).resolve()
        logger.info(f"GitTool: local repo path → '{self.local_path}'")
        self._repo = self._ensure_repo()

    @property
    def workspace_path(self) -> Path:
        """The local repo root — this IS the workspace for the Coder Agent."""
        return self.local_path

    # ------------------------------------------------------------------ public

    def prepare_branch(self, ticket_id: str) -> Path:
        """
        Pull latest main and create (or reset) the sentinel/<ticket_id> branch.

        Returns:
            The local repo path to use as the Coder Agent workspace.
        """
        repo = self._repo
        branch = f"{BRANCH_PREFIX}/{ticket_id}"
        base = self._base_branch()

        logger.info(f"GitTool: checking out '{base}' and pulling latest...")
        repo.git.checkout(base)
        repo.remote("origin").pull()

        # Reset sentinel branch if it already exists
        if branch in [b.name for b in repo.branches]:
            logger.info(f"GitTool: resetting existing branch '{branch}'...")
            repo.delete_head(branch, force=True)

        logger.info(f"GitTool: creating branch '{branch}'...")
        repo.git.checkout("-b", branch)

        logger.info(f"GitTool: ready — workspace is '{self.local_path}'")
        return self.local_path

    def commit_and_push(self, ticket_id: str, summary: str) -> GitResult:
        """
        Stage all changes in the repo, commit, and push the sentinel branch.

        Args:
            ticket_id: The Jira ticket ID (e.g. "SCRUM-6").
            summary:   Short ticket summary for the commit message.

        Returns:
            A GitResult with branch name, commit SHA, and remote URL.
        """
        repo = self._repo
        branch = f"{BRANCH_PREFIX}/{ticket_id}"

        # Stage everything (new + modified + deleted)
        repo.git.add(A=True)

        if not repo.index.diff("HEAD") and not repo.untracked_files:
            logger.warning("GitTool: nothing to commit — workspace unchanged.")
            return GitResult(
                branch_name=branch,
                commit_sha=repo.head.commit.hexsha,
                remote_url=f"https://github.com/{self.repo_owner}/{self.repo_name}",
            )

        commit_msg = f"feat({ticket_id}): {summary} [ScopeSentinel]"
        commit = repo.index.commit(commit_msg)
        logger.info(f"GitTool: committed '{commit_msg}' ({commit.hexsha[:8]})")

        logger.info(f"GitTool: pushing '{branch}' to remote...")
        repo.git.push(self._authenticated_url(), f"{branch}:{branch}", "--force")
        logger.info("GitTool: push complete. ✅")

        # Return to base branch
        repo.git.checkout(self._base_branch())

        return GitResult(
            branch_name=branch,
            commit_sha=commit.hexsha,
            remote_url=f"https://github.com/{self.repo_owner}/{self.repo_name}",
        )

    # ------------------------------------------------------------------ setup

    def _ensure_repo(self) -> Repo:
        """
        Return a Repo for self.local_path.
        Resolution order:
          1. Valid local git repo     → use as-is
          2. Exists, not a git repo  → wipe it, re-clone
          3. Doesn't exist           → clone from GitHub
          4. Clone 404               → create GitHub repo, then clone
        """
        if self.local_path.exists():
            try:
                repo = Repo(self.local_path)
                logger.info("GitTool: existing local repo found — skipping clone.")
                return repo
            except InvalidGitRepositoryError:
                logger.warning(
                    f"GitTool: '{self.local_path}' exists but is not a valid git repo. "
                    "Wiping and re-cloning..."
                )
                shutil.rmtree(self.local_path)

        self.local_path.mkdir(parents=True, exist_ok=True)
        return self._clone_or_create()

    def _clone_or_create(self) -> Repo:
        """Clone from GitHub; if repo not found, create it first."""
        clone_url = self._authenticated_url()
        try:
            logger.info(
                f"GitTool: cloning {self.repo_owner}/{self.repo_name} "
                f"→ '{self.local_path}'"
            )
            repo = Repo.clone_from(clone_url, self.local_path)
            logger.info("GitTool: clone complete. ✅")
            return repo
        except GitCommandError as e:
            stderr = str(getattr(e, "stderr", "") or e)
            if "not found" in stderr.lower():
                logger.warning(
                    f"GitTool: '{self.repo_owner}/{self.repo_name}' not found on GitHub. "
                    "Creating repo now..."
                )
                self._create_github_repo()
                shutil.rmtree(self.local_path)
                self.local_path.mkdir(parents=True, exist_ok=True)
                repo = Repo.clone_from(clone_url, self.local_path)
                logger.info("GitTool: cloned newly created repo. ✅")
                return repo
            raise

    def _create_github_repo(self) -> None:
        """Create the GitHub repo via the API using PyGithub."""
        from github import Auth
        gh = Github(auth=Auth.Token(self.token))
        user = gh.get_user()
        new_repo = user.create_repo(
            name=self.repo_name,
            description=f"Auto-created by ScopeSentinel for {self.repo_name}",
            private=False,
            auto_init=True,
        )
        logger.info(f"GitTool: GitHub repo created → {new_repo.html_url} ✅")

    # ------------------------------------------------------------------ helpers

    def _base_branch(self) -> str:
        """Returns 'main' if it exists, otherwise 'master'."""
        names = [b.name for b in self._repo.branches]
        return "main" if "main" in names else "master"

    def _authenticated_url(self) -> str:
        return f"https://{self.token}@github.com/{self.repo_owner}/{self.repo_name}.git"
