# Circle Core Framework - Secure Dockerfile
# Multi-stage build for minimal attack surface

# Build stage
FROM python:3.8-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Final stage
FROM python:3.8-slim

# Create non-root user
RUN useradd -m circlecore

WORKDIR /app

# Copy only the built wheels from the builder stage
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/*

# Copy application code
COPY . .

# Switch to non-root user
USER circlecore

# Run with minimal capabilities
ENTRYPOINT ["python", "-m", "circle_core"]
