# ScopeSentinel 🛡️

*From writing code to orchestrating intelligent execution.*

## About ScopeSentinel

### Vision
We envision a world where engineering teams operate as orchestrators of intelligent systems, seamlessly delegating work to autonomous agents that continuously build, test, and improve software—making high-quality software delivery faster, more scalable, and universally accessible.

### Mission
To transform software development from manual execution to intent-driven automation by enabling autonomous agents to design, implement, and validate code end-to-end within a controlled, human-governed workflow.

### Goal
Build a multi-tenant, extensible platform where engineers can delegate software tasks to autonomous agents that operate in isolated environments, execute work end-to-end, and deliver production-ready outputs—allowing teams to scale engineering throughput through parallel, asynchronous execution while retaining human control over critical decisions.

### Product Principles
The product is built on the principle of **intent over implementation**, where users define what needs to be done and autonomous agents handle execution end-to-end with full ownership, producing validated, production-ready outcomes. Agents operate with **autonomy but strict accountability**, ensuring every action is traceable, reviewable, and reversible, while **human judgment remains the final gate** for all critical decisions. The system combines **deterministic workflows with intelligent execution**, enabling predictable orchestration and adaptive problem-solving, all within **safe, isolated environments**. It is designed to be **parallel by default**, allowing multiple agents to run concurrently, with **tight feedback loops** for continuous validation and self-correction. Deep **tool integration over model dependency**, along with **transparency, extensibility, and multi-tenant scalability**, ensures the platform remains reliable, explainable, and adaptable—prioritizing **progress over perfection** to deliver fast, iterative value.

## What it does

```
Jira Ticket → AI Plan → [Human Approval] → Code Generation → Sandbox Validation → Git PR
```

1. **Fetches** a Jira ticket (summary, description, acceptance criteria)
2. **Plans** — an LLM generates a step-by-step implementation plan
3. **HITL Gate** — you review the plan in your terminal: Approve / Reject / Modify (with feedback for replanning)
4. **Codes** — an LLM generates all required files directly into the target repo on a `sentinel/<ticket-id>` branch
5. **Validates** — a Docker sandbox runs syntax checks, linting (`flake8`), and tests (`pytest`) on the generated code; failures trigger self-correction (up to 3 attempts)
6. **Ships** — commits and pushes the branch, then opens a GitHub PR with the Jira ticket details in the description

## Project Structure

```
ScopeSentinel/
├── main.py                  # Orchestrator — entry point
├── agents/
│   ├── planner_agent.py     # Generates & revises implementation plans
│   └── coder_agent.py       # Generates, deletes, and validates code files
├── tools/
│   ├── jira_tool.py         # Jira REST API integration
│   ├── git_tool.py          # Branch management & git push
│   └── github_tool.py       # GitHub PR creation
├── hitl/
│   └── hitl_gateway.py      # Terminal-based human approval gateway
├── sandbox/
│   ├── sandbox_runner.py    # Docker container executor
│   └── validator.py         # Syntax, lint & test runner
└── workspace/               # Fallback workspace (used when Git not configured)
```

## Setup

### 1. Install dependencies

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> Docker Desktop must be running for sandbox validation.

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key (GPT-4o is used) |
| `JIRA_URL` | Your Atlassian instance URL |
| `JIRA_USERNAME` | Your Jira email |
| `JIRA_API_TOKEN` | Jira API token |
| `GITHUB_TOKEN` | GitHub PAT with `repo` scope |
| `GITHUB_REPO_OWNER` | GitHub username or org |
| `GITHUB_REPO_NAME` | Target repository name |
| `GITHUB_REPO_LOCAL_PATH` | Local directory to clone the repo into |

> **GitHub token scopes required:** `repo` (create/push branches, open PRs, create repos)

### 3. Run

```bash
python main.py --ticket SCRUM-6
```

If no `--ticket` is provided, it runs a quick health check instead.

## How the Git workflow works

`GITHUB_REPO_LOCAL_PATH/GITHUB_REPO_NAME` is the canonical local repo path. ScopeSentinel:

- Uses it as-is if it's already a valid git repo
- Clones from GitHub if it doesn't exist
- Creates the GitHub repo automatically if it doesn't exist on GitHub

Generated code is written **directly into the local repo** on the `sentinel/<ticket-id>` branch — no separate workspace directory needed.

## Coder Agent output format

The LLM is prompted to respond using a strict format:

```
### `path/to/file.py`
```python
# file contents
```

### DELETE `path/to/remove/`
```

The agent parses this to write new files and delete directories/files as instructed.

## Self-correction loop

If sandbox validation fails, the error output is fed back to the LLM:

```
Generate → Validate → ❌ fail → Send errors to LLM → Regenerate → Validate → ✅ pass
```

Up to 3 correction attempts are made before proceeding with the last output.

## Requirements

- Python 3.12+
- Docker Desktop
- OpenAI API access
- Jira Cloud account
- GitHub account with a personal access token (`repo` scope)
