FROM ubuntu:20.04

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y \
    openssh-server \
    sudo \
    nano \
    vim \
    net-tools \
    iputils-ping \
    iproute2 \
    openssl \
    cron \
    rsync \
    zip \
    unzip \
    apache2 \
    curl \
    wget \
    gnupg \
    apt-transport-https \
    && rm -rf /var/lib/apt/lists/*

# Set up SSH
RUN mkdir /var/run/sshd
RUN echo 'root:password' | chpasswd
RUN echo 'PermitRootLogin yes' >> /etc/ssh/sshd_config
RUN sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

# Create a file server user with restricted sudo
RUN useradd -m -s /bin/bash file-admin && \
    echo "file-admin:password" | chpasswd && \
    adduser file-admin sudo && \
    echo "file-admin ALL=(ALL) NOPASSWD:ALL, !/usr/bin/openssl, !/usr/bin/cat /srv/data/backups/encrypted_*.backup" > /etc/sudoers.d/file-admin

# Set up user for SSH with passwordless sudo (security misconfiguration)
RUN useradd -m -s /bin/bash ctf-user && \
    echo "ctf-user:password" | chpasswd && \
    usermod -aG sudo ctf-user && \
    echo "ctf-user ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# Install Java for Elasticsearch
RUN apt-get update && apt-get install -y openjdk-11-jdk && rm -rf /var/lib/apt/lists/*

# Install Elasticsearch
RUN wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | apt-key add - && \
    echo "deb https://artifacts.elastic.co/packages/7.x/apt stable main" | tee /etc/apt/sources.list.d/elastic-7.x.list && \
    apt-get update && apt-get install -y elasticsearch=7.17.10 && \
    rm -rf /var/lib/apt/lists/*

# Configure Elasticsearch properly with relevant settings
RUN echo "cluster.name: fileserver-cluster" >> /etc/elasticsearch/elasticsearch.yml && \
    echo "node.name: fileserver-node" >> /etc/elasticsearch/elasticsearch.yml && \
    echo "network.host: 0.0.0.0" >> /etc/elasticsearch/elasticsearch.yml && \
    echo "discovery.type: single-node" >> /etc/elasticsearch/elasticsearch.yml && \
    echo "xpack.security.enabled: false" >> /etc/elasticsearch/elasticsearch.yml && \
    echo "http.port: 9200" >> /etc/elasticsearch/elasticsearch.yml && \
    echo "bootstrap.memory_lock: false" >> /etc/elasticsearch/elasticsearch.yml && \
    mkdir -p /etc/elasticsearch/jvm.options.d && \
    echo "-Xms512m" > /etc/elasticsearch/jvm.options.d/memory.options && \
    echo "-Xmx512m" >> /etc/elasticsearch/jvm.options.d/memory.options && \
    mkdir -p /home/elasticsearch && \
    chown -R elasticsearch:elasticsearch /home/elasticsearch && \
    usermod -d /home/elasticsearch elasticsearch

# Set system limits for Elasticsearch
RUN echo "elasticsearch soft nofile 65535" >> /etc/security/limits.conf && \
    echo "elasticsearch hard nofile 65535" >> /etc/security/limits.conf

# Create file server directories
RUN mkdir -p /srv/data/public && \
    mkdir -p /srv/data/private && \
    mkdir -p /srv/data/backups && \
    mkdir -p /srv/data/configs

# Create some example content
RUN echo "This is public information that anyone can access." > /srv/data/public/readme.txt && \
    echo "Welcome to the Corporate File Server" > /srv/data/public/welcome.txt && \
    echo "Internal company policies - Confidential" > /srv/data/private/company_policies.txt && \
    echo "Employee directory - Restricted" > /srv/data/private/employee_directory.txt && \
    echo "Development server: 192.168.100.50" > /srv/data/configs/servers.conf && \
    echo "Database server: 192.168.100.51" >> /srv/data/configs/servers.conf && \
    echo "Backup server: 192.168.100.52" >> /srv/data/configs/servers.conf

# Create the encrypted backup file with the flag
RUN echo "Company Backend Credentials\nAdmin username: administrator\nAdmin password: SuperSecretPassword123\nFlag: FLAG_PLACEHOLDER_4" > /tmp/secret_config.txt && \
    openssl enc -aes-256-cbc -salt -in /tmp/secret_config.txt -out /srv/data/backups/encrypted_config.backup -k "backup2023" && \
    rm /tmp/secret_config.txt

# Leave a hint about the encryption password in a log file
RUN echo "Backup completed on 2023-03-15. Used standard company key format: 'backup' + year." > /srv/data/backups/backup_log.txt

# Configure Apache to serve file content
RUN echo '<VirtualHost *:80>\n\
    DocumentRoot /srv/data/public\n\
    <Directory /srv/data/public>\n\
        Options Indexes FollowSymLinks\n\
        AllowOverride None\n\
        Require all granted\n\
    </Directory>\n\
</VirtualHost>' > /etc/apache2/sites-available/000-default.conf

# Set appropriate permissions
RUN chown -R root:root /srv/data && \
    chmod -R 755 /srv/data/public && \
    chmod -R 700 /srv/data/private && \
    chmod -R 750 /srv/data/configs && \
    chmod -R 777 /srv/data/backups && \
    chmod 777 /srv/data/backups/backup_log.txt && \
    chmod 777 /srv/data/backups/encrypted_config.backup

# Expose ports
EXPOSE 22 80 9200

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Start services
CMD ["/entrypoint.sh"] 