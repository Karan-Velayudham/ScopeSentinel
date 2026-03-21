# ScopeSentinel: Prototype Epics & Stories

This document outlines the stories and epics to build the initial prototype of ScopeSentinel. The focus is exclusively on the core workflow: reading a Jira ticket, planning, requesting Human-in-the-Loop (HITL) approval, generating code securely in a sandbox, and creating a Pull Request.

## Epic 1: Foundation & AgentScope Setup
**Description:** Set up the basic Python project, integrate AgentScope, and configure the main orchestrator script.
* **Story 1.1: Project Initialization.** Set up a local Python project with a virtual environment, dependencies (`agentscope`, `jira`, `github3.py` or `PyGithub`, `docker`).
* **Story 1.2: Orchestrator Script.** Create a simple CLI or main script that drives the end-to-end prototype workflow using AgentScope.

## Epic 2: Ticket Ingestion & Planning
**Description:** Read the user request from a Jira ticket and create a concrete implementation plan.
* **Story 2.1: Jira MCP Integration.** Integrate a Jira MCP server to fetch a Jira ticket's description and acceptance criteria given a ticket ID.
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
* **Story 5.1: Git MCP Integration.** Integrate a Git MCP server (or custom Git Tool) to commit the generated code and push it to a new branch (e.g., `sentinel/JIRA-123`).
* **Story 5.2: GitHub MCP Integration.** Integrate a GitHub MCP server to open a Pull Request against the main branch, using the Jira ticket and implementation details as the PR description.

## Epic 6: API Control Plane & Integration
**Description:** Transition the orchestrator from a CLI script to a robust FastAPI service, enabling webhook triggers and external API access.
* **Story 6.1: FastAPI Server Setup.** Implement a FastAPI web server to expose endpoints for triggering and monitoring agentic workflows.
* **Story 6.2: Webhook Handlers.** Add support for inbound webhooks (e.g., Jira transitions, GitHub push events) to automatically kick off tasks.

## Epic 7: Dynamic MCP Server Registry
**Description:** Transition from a hardcoded custom MCP server wrapper to a dynamic, user-configurable registry of official MCP servers (GitHub, Jira, etc.).
* **Story 7.1: Configuration Layer.** Allow users to define a list of standard MCP servers (e.g., in a YAML file) that ScopeSentinel should connect to dynamically at startup.
* **Story 7.2: Orchestrator Client Pool.** Update `main.py` to initialize a pool of `StdIOStatefulClient` connections based on the registry.
* **Story 7.3: Dynamic Agent Tool Calling.** Refactor Agents to accept the dynamic list of loaded MCP tools instead of hardcoding tool names, allowing the LLM to discover and use the correct tools based on schema.

## Epic 8: The Knowledge Layer & RAG Integration
**Description:** Implement context retrieval for Mode A (Brownfield) repositories using a vector database.
* **Story 8.1: Vector DB Setup.** Integrate Qdrant or Milvus into the project stack (e.g., via Docker Compose).
* **Story 8.2: Repository Indexing (SimpleKnowledge).** Create a flow to ingest, chunk, and index existing codebase repositories so agents can search and understand legacy context.

## Epic 9: Enhanced Sandbox Isolation
**Description:** Move beyond basic local directories to true security boundaries using Docker or gVisor for agent execution.
* **Story 9.1: Ephemeral Containers.** Update the Sandbox execution logic to spin up isolated, ephemeral Docker containers for every code generation/validation step.
* **Story 9.2: Command Sanitization.** Implement middleware to filter out high-risk shell commands (e.g., `rm -rf`, `sudo`).

## Epic 10: Advanced Governance & Secret Management
**Description:** Extend the governance layer with robust secret masking and additional HITL checkpoints.
* **Story 10.1: Multi-stage HITL.** Add distinct approval gates for Commit Approval and Deploy Approval, augmenting the existing Plan Approval step.
* **Story 10.2: Vault Integration.** Integrate HashiCorp Vault (or similar) to inject secrets safely without exposing them to the LLM context.

## Epic 11: Multi-Tenancy & Project Scaffolding
**Description:** Complete the SaaS architecture by adding organization isolation and support for Greenfield application scaffolding.
* **Story 11.1: Greenfield Scaffolding.** Implement the Mode B workflow where the Architect agent designs and bootstraps new repositories via `gh cli`.
* **Story 11.2: Tenant Isolation.** Add Organization IDs to knowledge bases, workspaces, and database entities to ensure secure multi-tenancy.
