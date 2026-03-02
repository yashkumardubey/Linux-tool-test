FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/patch-controller

COPY ../../controller/ ./controller/
WORKDIR /opt/patch-controller/controller

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["python", "app.py"]
