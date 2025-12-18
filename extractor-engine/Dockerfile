FROM python:3.11-slim

WORKDIR /app

# Copy everything needed by extractor-engine
COPY extractor-engine/ /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "app.py"]
