# =============================================================================
# ScopeSentinel — Root Makefile (updated for Phase 1)
#
# Usage:
#   make dev              # Run agent-runtime health check (Phase 0)
#   make api              # Start all Phase 1 services via Docker Compose
#   make api-local        # Run FastAPI dev server locally without Docker
#   make test             # Run agent-runtime tests
#   make test-api         # Run API service tests
#   make migrate          # Run Alembic migrations
#   make build            # Build all Docker images
#   make run TICKET=X     # Run workflow via Python CLI
# =============================================================================

AGENT_DIR       := services/agent-runtime
API_DIR         := services/api
VENV            := $(AGENT_DIR)/venv
PYTHON          := $(VENV)/bin/python
PIP             := $(VENV)/bin/pip
PYTEST          := $(VENV)/bin/pytest

API_VENV        := $(API_DIR)/venv
API_PYTHON      := $(API_VENV)/bin/python
API_PIP         := $(API_VENV)/bin/pip
API_PYTEST      := $(API_VENV)/bin/pytest

IMAGE_RUNTIME   := scopesentinel-agent-runtime:latest
IMAGE_API       := scopesentinel-api:latest
TICKET          ?= SCRUM-8

.PHONY: help install install-api dev api api-local api-stop \
        test test-api build migrate seed run run-docker lint clean

# ── Default: show help ────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  ScopeSentinel Makefile"
	@echo "  ────────────────────────────────────────────────────────────"
	@echo "  Phase 0 (CLI):"
	@echo "    make install          Install agent-runtime Python deps"
	@echo "    make dev              Run agent-runtime health check"
	@echo "    make test             Run agent-runtime tests (≥70% coverage)"
	@echo "    make run TICKET=X     Run CLI workflow for ticket X"
	@echo ""
	@echo "  Phase 1 (API + Worker):"
	@echo "    make install-api      Install API service Python deps"
	@echo "    make api              Start all services via docker compose"
	@echo "    make api-local        Run FastAPI dev server locally"
	@echo "    make api-stop         Stop all running services"
	@echo "    make migrate          Run Alembic DB migrations"
	@echo "    make seed             Seed the database (also runs on startup)"
	@echo "    make test-api         Run API service tests"
	@echo ""
	@echo "  General:"
	@echo "    make build            Build all Docker images"
	@echo "    make lint             Run ruff on both services"
	@echo "    make clean            Remove build artifacts"
	@echo ""

# ── Install agent-runtime deps ────────────────────────────────────────────────
install:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r $(AGENT_DIR)/requirements.txt

# ── Install API deps ──────────────────────────────────────────────────────────
install-api:
	python3 -m venv $(API_VENV)
	$(API_PIP) install --upgrade pip
	$(API_PIP) install -r $(API_DIR)/requirements.txt

# ── Dev: install + healthcheck ────────────────────────────────────────────────
dev: install
	cd $(AGENT_DIR) && "$(abspath $(PYTHON))" main.py

# ── Phase 1: start all services via Docker Compose ────────────────────────────
api:
	docker compose -f $(AGENT_DIR)/docker-compose.yml up -d --build
	@echo ""
	@echo "  ✅ ScopeSentinel Phase 1 running:"
	@echo "     API:      http://localhost:8000"
	@echo "     Docs:     http://localhost:8000/docs"
	@echo "     Health:   http://localhost:8000/api/health"
	@echo ""

api-stop:
	docker compose -f $(AGENT_DIR)/docker-compose.yml down

# ── Local FastAPI dev server (no Docker) ─────────────────────────────────────
api-local: install-api
	cd $(API_DIR) && "$(abspath $(API_PYTHON))" -m uvicorn main:app --reload --port 8000

# ── Run Alembic migrations ────────────────────────────────────────────────────
migrate: install-api
	cd $(API_DIR) && "$(abspath $(API_PYTHON))" -m alembic upgrade head

# ── Seed the database ─────────────────────────────────────────────────────────
seed: install-api
	cd $(API_DIR) && "$(abspath $(API_PYTHON))" seed_db.py

# ── Agent runtime tests (with coverage gate) ─────────────────────────────────
test: install
	cd $(AGENT_DIR) && "$(abspath $(PYTEST))" tests/ -v

# ── API service tests ─────────────────────────────────────────────────────────
test-api: install-api
	cd $(API_DIR) && "$(abspath $(API_PYTEST))" tests/ -v

# ── Build all Docker images ───────────────────────────────────────────────────
build:
	docker build -t $(IMAGE_RUNTIME) $(AGENT_DIR)
	docker build -t $(IMAGE_API) $(API_DIR)

# ── Run CLI via Python ────────────────────────────────────────────────────────
run: install
	cd $(AGENT_DIR) && "$(abspath $(PYTHON))" main.py --ticket $(TICKET)

# ── Run CLI via Docker ────────────────────────────────────────────────────────
run-docker: build
	docker run --rm \
		--env-file $(AGENT_DIR)/.env \
		-v $(PWD)/$(AGENT_DIR)/workspace:/app/workspace \
		-v /var/run/docker.sock:/var/run/docker.sock \
		$(IMAGE_RUNTIME) --ticket $(TICKET)

# ── Lint both services ────────────────────────────────────────────────────────
lint: install install-api
	$(VENV)/bin/ruff check $(AGENT_DIR) --exclude $(AGENT_DIR)/venv
	$(API_VENV)/bin/ruff check $(API_DIR) --exclude $(API_DIR)/venv

# ── Clean ─────────────────────────────────────────────────────────────────────
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null; true
	find . -name "*.pyc" -delete 2>/dev/null; true
	rm -f $(AGENT_DIR)/coverage.xml $(AGENT_DIR)/.coverage
	@echo "  ✅ Cleaned."
