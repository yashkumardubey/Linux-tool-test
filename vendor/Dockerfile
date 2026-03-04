###############################################################################
#  PatchMaster Vendor Portal — Production Dockerfile
###############################################################################
FROM python:3.12-slim

RUN groupadd -r vendor && useradd -r -g vendor -s /sbin/nologin vendor

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Templates come from customer-manager (shared)
COPY templates/ ./templates/

# Data directory for SQLite (mount as volume)
RUN mkdir -p /app/data && chown vendor:vendor /app/data

USER vendor

EXPOSE 5050

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5050/api/health')" || exit 1

CMD ["gunicorn", "app:app", \
     "--bind", "0.0.0.0:5050", \
     "--workers", "2", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info"]
