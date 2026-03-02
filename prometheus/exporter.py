#!/usr/bin/env python3
"""Simple example to push patch job status to a Pushgateway or expose custom metrics.

This is optional — the agent already exposes metrics via prometheus_client.
"""

from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
import time

registry = CollectorRegistry()
patch_status = Gauge('patch_job_status_example', 'Example patch status', registry=registry)

patch_status.set(1)  # example value

# push to pushgateway
# push_to_gateway('pushgateway.example.local:9091', job='patch_agent', registry=registry)

print('Metric prepared; configure pushgateway if desired.')
