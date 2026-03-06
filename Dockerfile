# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies if any are needed (e.g., for some python packages)
# RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Ensure the vault directory exists (it will be overriden by a volume mount usually)
RUN mkdir -p /app/vault

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV VAULT_PATH=/app/vault
ENV HEARTBEAT_FILE=/tmp/bot_heartbeat

# Healthcheck to ensure the bot is responsive
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
  CMD test $(find ${HEARTBEAT_FILE} -mmin -2 | wc -l) -gt 0 || exit 1

# Run the application
CMD ["python", "src/main.py"]
