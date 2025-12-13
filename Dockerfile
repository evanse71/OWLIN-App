# OWLIN - Production Docker Image
# Multi-stage build for optimized production deployment

# ---- Build UI Stage
FROM node:20-bullseye-slim AS ui-builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source files
COPY . .

# Build the UI
RUN npm run build

# ---- Runtime Stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    OWLIN_PORT=8001 \
    LLM_BASE=http://127.0.0.1:11434 \
    OWLIN_DB_URL=sqlite:///./data/owlin.db \
    PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory and user
RUN groupadd -r owlin && useradd -r -g owlin owlin
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy built UI from previous stage
COPY --from=ui-builder /app/out ./out

# Create data directory for database
RUN mkdir -p /app/data && chown -R owlin:owlin /app

# Switch to non-root user
USER owlin

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/api/health || exit 1

# Start the application
CMD ["python", "-m", "backend.final_single_port"]
