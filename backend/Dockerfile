# Base image: Python 3.13 (same version you run locally, so dev and prod match)
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# Node.js is needed because the agent launches `npx @brightdata/mcp` as a subprocess
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
 && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy ONLY the dependency list first. Docker caches each step, so editing your code
# won't re-install every package. This ordering is the most important Dockerfile habit.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app

# Don't run as root inside the container
RUN useradd -m app && chown -R app /app
USER app

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=30s --retries=5 \
  CMD curl -fs http://localhost:${PORT:-8000}/api/health || exit 1

# ${PORT:-8000}: Render injects a PORT variable; locally we fall back to 8000.
# 0.0.0.0 means "accept connections from outside the container" (127.0.0.1 would not).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]