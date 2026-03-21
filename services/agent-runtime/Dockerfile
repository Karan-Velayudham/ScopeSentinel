# =============================================================================
# ScopeSentinel — agent-runtime Dockerfile (Story 0.3.1)
# Multi-stage build: non-root user, minimal final image
# =============================================================================

# ── Stage 1: dependency builder ──────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install dependencies into the user site-packages so we can copy them later
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# ── Stage 2: runtime image ────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Create a dedicated non-root user
RUN useradd --create-home --shell /bin/bash sentinel

WORKDIR /app

# Copy installed packages from the builder stage
COPY --from=builder /root/.local /home/sentinel/.local

# Copy application source (owned by the sentinel user)
COPY --chown=sentinel:sentinel . .

# Drop privileges
USER sentinel

# Make sure user-installed packages are on PATH
ENV PATH="/home/sentinel/.local/bin:$PATH"

# Log as JSON in containers by default
ENV LOG_FORMAT=json
ENV LOG_LEVEL=info

# Default: interactive ticket workflow; override with other scripts or flags
ENTRYPOINT ["python"]
CMD ["main.py"]
