# =============================================================================
# ScopeSentinel — Root Makefile (Story 0.3.3)
#
# Delegates to services/agent-runtime for all runtime targets.
# Usage:
#   make test
#   make build
#   make run TICKET=SCRUM-8
#   make dev
# =============================================================================

AGENT_DIR := services/agent-runtime
VENV      := $(AGENT_DIR)/venv
PYTHON    := $(VENV)/bin/python
PIP       := $(VENV)/bin/pip
PYTEST    := $(VENV)/bin/pytest
IMAGE     := scopesentinel-agent-runtime:latest
TICKET    ?= SCRUM-8

.PHONY: help dev install test build run clean lint

# ── Default: show help ────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  ScopeSentinel Makefile"
	@echo "  ────────────────────────────────────────────────"
	@echo "  make install          Install Python dependencies into venv"
	@echo "  make dev              Install + run healthcheck (no ticket needed)"
	@echo "  make test             Run pytest with coverage (≥70% gate)"
	@echo "  make build            Build Docker image"
	@echo "  make run TICKET=X     Run full workflow for ticket X (via Python)"
	@echo "  make run-docker TICKET=X  Run workflow inside Docker container"
	@echo "  make lint             Run ruff linter"
	@echo "  make clean            Remove __pycache__, .pytest_cache, coverage files"
	@echo ""

# ── Install dependencies ──────────────────────────────────────────────────────
install:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r $(AGENT_DIR)/requirements.txt

# ── Dev: install + healthcheck ────────────────────────────────────────────────
dev: install
	cd $(AGENT_DIR) && $(abspath $(PYTHON)) main.py

# ── Test with coverage gate ───────────────────────────────────────────────────
test: install
	cd $(AGENT_DIR) && $(abspath $(PYTEST)) tests/ -v

# ── Docker build ──────────────────────────────────────────────────────────────
build:
	docker build -t $(IMAGE) $(AGENT_DIR)

# ── Run via Python directly ───────────────────────────────────────────────────
run:
	cd $(AGENT_DIR) && $(abspath $(PYTHON)) main.py --ticket $(TICKET)

# ── Run via Docker container ──────────────────────────────────────────────────
run-docker: build
	docker run --rm \
		--env-file $(AGENT_DIR)/.env \
		-v $(PWD)/$(AGENT_DIR)/workspace:/app/workspace \
		-v /var/run/docker.sock:/var/run/docker.sock \
		$(IMAGE) --ticket $(TICKET)

# ── Lint ──────────────────────────────────────────────────────────────────────
lint:
	$(VENV)/bin/ruff check $(AGENT_DIR) --exclude $(AGENT_DIR)/venv

# ── Clean ─────────────────────────────────────────────────────────────────────
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null; true
	find . -name "*.pyc" -delete 2>/dev/null; true
	rm -f $(AGENT_DIR)/coverage.xml $(AGENT_DIR)/.coverage
	@echo "  ✅ Cleaned."
