FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# robots.json is mounted in at /app/robots.json by docker-compose (single source
# of truth shared with the robots service).

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
