FROM grafana/grafana:9.0.0

# Copy dashboards and provisioning files for auto-import (build context is repo root)
COPY grafana/provisioning/dashboards/dashboard.yml /etc/grafana/provisioning/dashboards/dashboard.yml
COPY grafana/provisioning/datasources/datasource.yml /etc/grafana/provisioning/datasources/datasource.yml
COPY grafana/patch_dashboard.json /etc/grafana/provisioning/dashboards/json/patch_dashboard.json
