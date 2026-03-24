# =============================================================================
# ScopeSentinel — adapter-service Dockerfile
# Multi-stage build: non-root user, minimal final image
# =============================================================================

FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS runtime

RUN useradd --create-home --shell /bin/bash sentinel

WORKDIR /app

COPY --from=builder /root/.local /home/sentinel/.local

COPY --chown=sentinel:sentinel . .

USER sentinel

ENV PATH="/home/sentinel/.local/bin:$PATH"

ENV LOG_FORMAT=json
ENV LOG_LEVEL=info

EXPOSE 8005
ENTRYPOINT ["python"]
CMD ["main.py"]
