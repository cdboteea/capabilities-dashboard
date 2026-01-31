FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Create non-root user for security
RUN useradd -m -u 1001 eventprocessor && \
    mkdir -p /app /app/config /app/data /app/models && \
    chown -R eventprocessor:eventprocessor /app

# Install Python dependencies
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy application code
COPY src/ /app/src/
COPY config/ /app/config/

# Set working directory and user
WORKDIR /app
USER eventprocessor

# Expose port
EXPOSE 8303

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8303/health || exit 1

# Start the service
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8303", "--reload"] 