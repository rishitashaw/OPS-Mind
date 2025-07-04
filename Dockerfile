# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8080

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -e .

# Copy the application code
COPY opsmind/ ./opsmind/
COPY output/ ./output/

# Create necessary directories
RUN mkdir -p /app/opsmind/data/datasets/incidents
RUN mkdir -p /app/opsmind/data/datasets/jira

# Set proper permissions
RUN chmod -R 755 /app

# Create a non-root user
RUN useradd --create-home --shell /bin/bash appuser
RUN chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from opsmind.config.settings import validate_config; validate_config()" || exit 1

# Expose port
EXPOSE $PORT

# Command to run the application
CMD ["python", "-m", "adk", "web", "--host", "0.0.0.0", "--port", "8080"] 