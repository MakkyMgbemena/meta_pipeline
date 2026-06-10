FROM python:3.12-slim


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
RUN  pip install --no-cache-dir -r requirements.txt


# Copy the rest of the application files
COPY . .

# Cloud Run injects a dynamic $PORT variable and we choose the service type via SERVICE_TYPE.
COPY entrypoint.sh .
CMD ["sh", "entrypoint.sh"]
