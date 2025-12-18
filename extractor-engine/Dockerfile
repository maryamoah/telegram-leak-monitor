FROM python:3.11-slim

WORKDIR /app

# Install curl (needed to download supercronic)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install supercronic (lightweight cron runner)
RUN curl -fsSL https://github.com/aptible/supercronic/releases/latest/download/supercronic-linux-amd64 \
    -o /usr/local/bin/supercronic \
    && chmod +x /usr/local/bin/supercronic

# Copy extractor engine (includes scripts/)
COPY . /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy cron schedule
COPY cronjobs /etc/cronjobs

# Start supercronic
CMD ["supercronic", "/etc/cronjobs"]

