FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# procps provides pkill/pgrep/ps so tests can kill individual robot processes.
RUN apt-get update && apt-get install -y --no-install-recommends procps \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

CMD ["python", "spawn.py"]
