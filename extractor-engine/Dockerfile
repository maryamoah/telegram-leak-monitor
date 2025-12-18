FROM python:3.11-slim

WORKDIR /app

# Install curl (needed to fetch supercronic)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install supercronic
RUN curl -fsSL https://github.com/aptible/supercronic/releases/latest/download/supercronic-linux-amd64 \
    -o /usr/local/bin/supercronic \
    && chmod +x /usr/local/bin/supercronic

# Copy extractor code (including scripts/)
COPY . /app/

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Copy cron schedule
COPY cronjobs /etc/cronjobs

CMD ["supercronic", "/etc/cronjobs"]
