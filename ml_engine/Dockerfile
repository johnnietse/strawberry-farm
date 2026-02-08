FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements from file
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy ML engine scripts
COPY . .

# Default command (overridden by docker-compose)
CMD ["python", "--version"]
