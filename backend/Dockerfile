# Multi-stage build for smaller final image
FROM python:3.11-slim AS builder

WORKDIR /build

# Install dependencies
COPY requirements.txt .
ENV PIP_DEFAULT_TIMEOUT=300
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
#RUN pip install --no-cache-dir --retries 10 --timeout 300 -r requirements.txt
RUN pip install -r requirements.txt

# Include source in builder so CI jobs using --target builder can lint/test code.
COPY . .

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Make sure scripts are usable
ENV PATH=/usr/local/bin:$PATH

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Health check (adjust endpoint if /ping doesn't exist)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import socket; s=socket.socket(); s.connect(('127.0.0.1', 8000)); s.close()" || exit 1

EXPOSE 8000

# Run the application
CMD ["python", "run.py"]
