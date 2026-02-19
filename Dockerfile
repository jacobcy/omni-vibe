# Multi-stage build with uv for fast dependency resolution
FROM python:3.11-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first (cache layer)
COPY pyproject.toml uv.lock* ./

# Install production dependencies only
RUN uv sync --no-dev --no-install-project

# Copy source code
COPY src/ ./src/

# --- Runtime stage ---
FROM python:3.11-slim

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy source code
COPY src/ ./src/
COPY config.yaml.example ./config.yaml.example

# Use the virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Run main program
CMD ["python", "-m", "src.main"]
