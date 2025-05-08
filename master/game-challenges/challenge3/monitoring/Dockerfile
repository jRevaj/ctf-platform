FROM ubuntu:20.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install base dependencies
RUN apt-get update && apt-get install -y \
    openssh-server \
    sudo \
    curl \
    wget \
    gnupg \
    apt-transport-https \
    software-properties-common \
    ca-certificates \
    nano \
    vim \
    net-tools \
    iputils-ping \
    nginx \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Set up SSH
RUN mkdir /var/run/sshd
RUN echo 'root:password' | chpasswd
RUN echo 'PermitRootLogin yes' >> /etc/ssh/sshd_config
RUN sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

# Create users
RUN useradd -m -s /bin/bash monitor-admin && \
    echo "monitor-admin:password" | chpasswd && \
    adduser monitor-admin sudo && \
    echo "monitor-admin ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers.d/monitor-admin

RUN useradd -m -s /bin/bash ctf-user && \
    echo "ctf-user:password" | chpasswd && \
    usermod -aG sudo ctf-user && \
    echo "ctf-user ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# Install Grafana
RUN apt-get update && \
    apt-get install -y apt-transport-https software-properties-common && \
    wget -q -O /usr/share/keyrings/grafana.key https://apt.grafana.com/gpg.key && \
    echo "deb [signed-by=/usr/share/keyrings/grafana.key] https://apt.grafana.com stable main" | tee -a /etc/apt/sources.list.d/grafana.list && \
    apt-get update && \
    apt-get install -y grafana && \
    mkdir -p /var/lib/grafana/plugins && \
    mkdir -p /var/log/grafana && \
    mkdir -p /var/run/grafana && \
    chown -R grafana:grafana /var/lib/grafana && \
    chown -R grafana:grafana /var/log/grafana && \
    chown -R grafana:grafana /var/run/grafana && \
    chown -R grafana:grafana /etc/grafana && \
    rm -rf /var/lib/apt/lists/*

# Create monitoring API with vulnerabilities
RUN mkdir -p /opt/monitoring-api
WORKDIR /opt/monitoring-api

# Install API dependencies
RUN pip3 install flask flask-cors flask-httpauth requests

# Create monitoring API
COPY api.py /opt/monitoring-api/
COPY config.json /opt/monitoring-api/

# Create Grafana dashboard with hidden flag
RUN mkdir -p /var/lib/grafana/dashboards
COPY dashboard.json /var/lib/grafana/dashboards/

# Configure Grafana provisioning
RUN mkdir -p /etc/grafana/provisioning/dashboards
RUN mkdir -p /etc/grafana/provisioning/datasources

# Create a hidden datasource with the flag embedded
RUN echo '{\n\
  "apiVersion": 1,\n\
  "datasources": [\n\
    {\n\
      "access": "proxy",\n\
      "editable": true,\n\
      "name": "SystemMetrics",\n\
      "orgId": 1,\n\
      "type": "prometheus",\n\
      "url": "http://localhost:9090",\n\
      "version": 1,\n\
      "jsonData": {\n\
        "timeInterval": "5s",\n\
        "queryTimeout": "60s",\n\
        "httpMethod": "POST",\n\
        "manageAlerts": true,\n\
        "secret_token": "FLAG_PLACEHOLDER_7"\n\
      },\n\
      "secureJsonData": {\n\
        "httpHeaderValue1": "Bearer secret-token"\n\
      }\n\
    }\n\
  ]\n\
}' > /etc/grafana/provisioning/datasources/prometheus.yaml

# Configure Grafana dashboard provisioning
COPY dashboard-provider.yaml /etc/grafana/provisioning/dashboards/

# Create hidden datasource configuration file
RUN mkdir -p /etc/grafana/secrets
RUN echo "FLAG_PLACEHOLDER_7" | base64 > /etc/grafana/secrets/.ds_key
RUN chmod 600 /etc/grafana/secrets/.ds_key
RUN chown grafana:grafana /etc/grafana/secrets/.ds_key

# Create a hidden SQLite database with Grafana data
RUN apt-get update && apt-get install -y sqlite3 && \
    mkdir -p /var/lib/grafana/data && \
    echo "CREATE TABLE IF NOT EXISTS api_key (id INTEGER PRIMARY KEY AUTOINCREMENT, org_id INTEGER NOT NULL, name TEXT NOT NULL, key TEXT NOT NULL, role TEXT NOT NULL, created DATETIME NOT NULL, updated DATETIME NOT NULL, expires DATETIME NULL); INSERT INTO api_key (org_id, name, key, role, created, updated) VALUES (1, 'system-monitoring-key', 'eyJrIjoiVEdGRUc0V1VZV2NJelZXNU5Kc2RhN3dCbFpxbXFjZ1YiLCJuIjoic3lzdGVtLW1vbml0b3JpbmctZmxhZyIsImlkIjoxfQ==', 'Admin', DATETIME('now'), DATETIME('now'));" > /tmp/init.sql && \
    sqlite3 /var/lib/grafana/data/grafana.db < /tmp/init.sql && \
    rm /tmp/init.sql

# Set permission for Grafana
RUN chown -R grafana:grafana /var/lib/grafana
RUN chown -R grafana:grafana /etc/grafana

# Create entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose ports
EXPOSE 22 80 3000 8090

# Start services
CMD ["/entrypoint.sh"]
