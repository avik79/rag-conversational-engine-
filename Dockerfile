# Multi-stage build for RAG Conversational Engine

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml uv.lock* ./
COPY . .

# Install dependencies with uv if available, otherwise pip
RUN pip install --upgrade pip setuptools wheel && \
    if [ -f uv.lock ]; then \
      pip install uv && \
      uv pip install --system -e .; \
    else \
      pip install -e .; \
    fi

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 appuser

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /app /app

# Copy only necessary files for runtime
COPY --chown=appuser:appuser . .

# Create necessary directories
RUN mkdir -p data logs/hitl 2>/dev/null && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port for Streamlit
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true

# Command: Run Streamlit app
CMD ["streamlit", "run", "app/main.py", "--logger.level=info"]
