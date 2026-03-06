"""
GitTool: Commits generated code to a new branch and pushes to remote.

Reads configuration from environment variables:
  - GITHUB_TOKEN:           Personal access token for pushing (repo scope)
  - GITHUB_REPO_OWNER:      GitHub org/username (e.g. "imkaranvp")
  - GITHUB_REPO_NAME:       Repository name (e.g. "my-repo")
  - GITHUB_REPO_LOCAL_PATH: Absolute path to a local clone of the target repo
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
    Creates a feature branch, copies workspace files into the repo,
    commits, and pushes to the remote.
    """

    def __init__(self):
        load_dotenv()
        self.token       = os.environ.get("GITHUB_TOKEN", "")
        self.repo_owner  = os.environ.get("GITHUB_REPO_OWNER", "")
        self.repo_name   = os.environ.get("GITHUB_REPO_NAME", "")
        local_path       = os.environ.get("GITHUB_REPO_LOCAL_PATH", "")

        if not all([self.token, self.repo_owner, self.repo_name, local_path]):
            raise EnvironmentError(
                "Missing Git config. Please set GITHUB_TOKEN, GITHUB_REPO_OWNER, "
                "GITHUB_REPO_NAME, and GITHUB_REPO_LOCAL_PATH in your .env file."
            )

        self.local_path = Path(local_path).resolve()
        self._repo = self._ensure_repo()
        logger.info(f"GitTool: using repo at '{self.local_path}'")

    def _ensure_repo(self) -> Repo:
        """
        Return a Repo object for self.local_path.
        Resolution order:
          1. Path exists + is a valid git repo      → use it
          2. Path exists but not a git repo         → clone into <path>/<repo_name>
          3. Clone fails (repo not found on GitHub) → create the repo via API, then clone
          4. Path doesn't exist                     → clone (or create + clone)
        """
        clone_url = (
            f"https://{self.token}@github.com/{self.repo_owner}/{self.repo_name}.git"
        )

        # Case 1: already a valid repo
        if self.local_path.exists():
            try:
                repo = Repo(self.local_path)
                logger.info(f"GitTool: existing repo found at '{self.local_path}'")
                return repo
            except InvalidGitRepositoryError:
                logger.warning(
                    f"GitTool: '{self.local_path}' exists but is not a git repo. "
                    "Cloning into a new subdirectory..."
                )
                self.local_path = self.local_path / self.repo_name

        # Case 2/3/4: attempt clone; create remote repo first if not found
        self.local_path.mkdir(parents=True, exist_ok=True)
        try:
            logger.info(
                f"GitTool: cloning {self.repo_owner}/{self.repo_name} → '{self.local_path}'"
            )
            repo = Repo.clone_from(clone_url, self.local_path)
            logger.info("GitTool: clone complete. ✅")
            return repo
        except GitCommandError as e:
            if "Repository not found" in str(e.stderr) or "not found" in str(e.stderr).lower():
                logger.warning(
                    f"GitTool: repo '{self.repo_owner}/{self.repo_name}' not found on GitHub. "
                    "Creating it now..."
                )
                self._create_github_repo()
                # Re-clone after creation
                import shutil
                if self.local_path.exists():
                    shutil.rmtree(self.local_path)
                self.local_path.mkdir(parents=True, exist_ok=True)
                repo = Repo.clone_from(clone_url, self.local_path)
                logger.info("GitTool: cloned newly created repo. ✅")
                return repo
            raise  # re-raise unexpected git errors

    def _create_github_repo(self) -> None:
        """Create the GitHub repo via the API using PyGithub."""
        from github import Auth
        gh = Github(auth=Auth.Token(self.token))
        user = gh.get_user()
        repo = user.create_repo(
            name=self.repo_name,
            description=f"Auto-created by ScopeSentinel for {self.repo_name}",
            private=False,
            auto_init=True,       # creates a default branch so clone works immediately
        )
        logger.info(f"GitTool: GitHub repo created → {repo.html_url} ✅")



    # ------------------------------------------------------------------ public

    def push_workspace(
        self,
        ticket_id: str,
        summary: str,
        workspace_path: str | Path,
    ) -> GitResult:
        """
        Copy workspace files, commit, and push to a new sentinel branch.

        Args:
            ticket_id:      Jira ticket ID (e.g. "SCRUM-6").
            summary:        Short ticket summary for the commit message.
            workspace_path: Path to the generated workspace directory.

        Returns:
            A GitResult with branch name, commit SHA, and remote URL.
        """
        workspace = Path(workspace_path).resolve()
        branch = f"{BRANCH_PREFIX}/{ticket_id}"

        repo = self._repo
        origin = repo.remote("origin")

        # Ensure we start from a clean, up-to-date base branch
        base = self._base_branch()
        logger.info(f"GitTool: checking out '{base}' and pulling latest...")
        repo.git.checkout(base)
        origin.pull()

        # Create (or reset) the sentinel branch
        if branch in [b.name for b in repo.branches]:
            logger.info(f"GitTool: deleting existing branch '{branch}'...")
            repo.delete_head(branch, force=True)
        logger.info(f"GitTool: creating branch '{branch}'...")
        repo.git.checkout("-b", branch)

        # Copy workspace files into the repo
        dest_dir = self.local_path / ticket_id
        if dest_dir.exists():
            shutil.rmtree(dest_dir)
        shutil.copytree(workspace, dest_dir)
        logger.info(f"GitTool: copied '{workspace}' → '{dest_dir}'")

        # Stage and commit
        repo.git.add(str(dest_dir))
        commit_msg = f"feat({ticket_id}): {summary} [ScopeSentinel]"
        commit = repo.index.commit(commit_msg)
        logger.info(f"GitTool: committed '{commit_msg}' ({commit.hexsha[:8]})")

        # Push with token auth
        push_url = self._authenticated_url()
        logger.info(f"GitTool: pushing '{branch}' to remote...")
        repo.git.push(push_url, f"{branch}:{branch}", "--force")
        logger.info(f"GitTool: push complete. ✅")

        # Restore base branch
        repo.git.checkout(base)

        return GitResult(
            branch_name=branch,
            commit_sha=commit.hexsha,
            remote_url=f"https://github.com/{self.repo_owner}/{self.repo_name}",
        )

    # ------------------------------------------------------------------ helpers

    def _base_branch(self) -> str:
        """Returns 'main' if it exists, otherwise 'master'."""
        names = [b.name for b in self._repo.branches]
        return "main" if "main" in names else "master"

    def _authenticated_url(self) -> str:
        return f"https://{self.token}@github.com/{self.repo_owner}/{self.repo_name}.git"
