# A simple Ubuntu-based host image with the patch agent installed.
# This container represents a target machine that the controller can manage.

FROM ubuntu:22.04

RUN apt-get update && apt-get install -y python3-pip apt-transport-https ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# create a directory for the agent
RUN mkdir -p /opt/patch-agent

# copy the agent code (build context is repo root)
COPY agent/ /opt/patch-agent/agent/

# install python requirements
RUN pip3 install --no-cache-dir -r /opt/patch-agent/agent/requirements.txt

# expose ports used by the agent
EXPOSE 8080 9100

# run the agent when container starts
CMD ["python3", "/opt/patch-agent/agent/agent.py", "--port", "8080", "--metrics-port", "9100"]
