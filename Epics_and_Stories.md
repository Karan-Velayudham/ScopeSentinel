# ScopeSentinel: Prototype Epics & Stories

This document outlines the stories and epics to build the initial prototype of ScopeSentinel. The focus is exclusively on the core workflow: reading a Jira ticket, planning, requesting Human-in-the-Loop (HITL) approval, generating code securely in a sandbox, and creating a Pull Request.

## Epic 1: Foundation & AgentScope Setup
**Description:** Set up the basic Python project, integrate AgentScope, and configure the main orchestrator script.
* **Story 1.1: Project Initialization.** Set up a local Python project with a virtual environment, dependencies (`agentscope`, `jira`, `github3.py` or `PyGithub`, `docker`).
* **Story 1.2: Orchestrator Script.** Create a simple CLI or main script that drives the end-to-end prototype workflow using AgentScope.

## Epic 2: Ticket Ingestion & Planning
**Description:** Read the user request from a Jira ticket and create a concrete implementation plan.
* **Story 2.1: Jira API Integration.** Create a basic tool/service to fetch a Jira ticket's description and acceptance criteria given a ticket ID.
* **Story 2.2: The Planner Agent.** Configure an AgentScope agent responsible for analyzing the Jira ticket and breaking it down into a step-by-step implementation plan and architectural approach.

## Epic 3: HITL Approval Gateway
**Description:** Pause the workflow to allow a human to review the Planner Agent's proposed plan.
* **Story 3.1: HITL Prompt Automation.** Implement AgentScope’s `handle_interrupt` or a simple CLI-based pause mechanism to present the generated plan to the user in the terminal.
* **Story 3.2: Approval Logic.** Allow the user to "Approve" (proceed to code generation), "Reject" (abort), or "Modify" (feed feedback back to the Planner Agent).

## Epic 4: Sandbox & Code Generation
**Description:** Generate code based on the approved plan and validate it inside a secure container environment.
* **Story 4.1: The Coder Agent.** Configure an AgentScope agent capable of writing file contents based on the approved implementation plan.
* **Story 4.2: Local Sandbox Execution.** Set up a local Docker container or isolated temporary directory to act as the sandbox.
* **Story 4.3: Secure Code Validation.** Create a tool for the Coder Agent to run tests or syntax checks (e.g., `pytest`, `npm test`, `flake8`) inside the sandbox container. Return output to the agent for self-correction if needed.

## Epic 5: Review & Pull Request Creation
**Description:** Finalize the workflow by pushing the generated code to the repository and creating a Pull Request.
* **Story 5.1: Git Operations Tool.** Implement a tool to commit the generated code and push it to a new branch (e.g., `sentinel/JIRA-123`).
* **Story 5.2: GitHub PR Integration.** Create a tool to open a Pull Request against the main branch, using the Jira ticket and implementation details as the PR description.
