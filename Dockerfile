# MCP Document Generator Server - Dockerfile
# Based on Python 3.11 slim image for optimal size and performance

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies required for document generation
# - libreoffice fonts for better document rendering (optional, commented out for size)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    echo 'source $HOME/.local/bin/env' >> ~/.bashrc
ENV PATH="/root/.local/bin:$PATH"

# Copy project files
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

# Install Python dependencies using uv
RUN /root/.local/bin/uv sync --frozen --no-dev

# Create directory for logs only (no token storage needed - stateless server)
RUN mkdir -p /logs

# Expose MCP server port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from mcp_document_server.server import TEMP_DIR; assert TEMP_DIR.exists()" || exit 1

# Run the MCP server
CMD ["/root/.local/bin/uv", "run", "python", "-m", "mcp_document_server.server"]
