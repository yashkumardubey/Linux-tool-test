FROM python:3.10-slim

# Install minimal packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    openssl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create user
RUN useradd --system --no-create-home --shell /usr/sbin/nologin patchagent || true

WORKDIR /opt/patch-agent

# Copy agent
COPY ../../agent/ ./agent/
COPY ../../systemd/patch-agent.service ./patch-agent.service

WORKDIR /opt/patch-agent/agent

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080 9100

ENV AGENT_RUN_AS_USER=patchagent

# By default run without TLS (controller will use http unless configured)
CMD ["python", "agent.py", "--dev-server", "--port", "8080", "--metrics-port", "9100"]
