FROM python:3.10-slim

# Set environment system configurations
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system dependencies needed for PostgreSQL and network requests
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY . .

# Cloud Run injects a dynamic $PORT variable, so we grab it automatically
CMD ["sh", "-c", "uvicorn services.fastapi.api:app --host 0.0.0.0 --port ${PORT:-8080}"]
