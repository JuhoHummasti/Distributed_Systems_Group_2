FROM grafana/grafana

# Copy datasources
COPY config/datasources /etc/grafana/provisioning/datasources/

# Copy dashboards
COPY config/dashboards /etc/grafana/provisioning/dashboards/

env DS_PROMETHEUS="Prometheus"