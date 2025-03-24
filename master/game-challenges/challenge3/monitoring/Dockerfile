FROM ubuntu:22.04

# Avoid prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install required packages
RUN apt-get update && apt-get install -y \
    openssh-server \
    curl \
    wget \
    apache2 \
    php \
    php-cli \
    build-essential \
    libgd-dev \
    snmp \
    libsnmp-dev \
    libssl-dev \
    gettext \
    automake \
    autoconf \
    net-tools \
    perl \
    libnet-snmp-perl \
    unzip \
    openjdk-11-jdk \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Set up SSH
RUN mkdir -p /var/run/sshd
RUN echo 'root:monitoring_root_password' | chpasswd
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config

# Create ctf-user
RUN useradd -m -s /bin/bash ctf-user
RUN echo "ctf-user:monitoring_password" | chpasswd
RUN echo "ctf-user ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/ctf-user

# Create flags directory
RUN mkdir -p /flags
RUN chmod 700 /flags

# Create flag files
RUN echo "FLAG_PLACEHOLDER_10" > /flags/nagios_command_flag.txt
RUN echo "FLAG_PLACEHOLDER_11" > /flags/elasticsearch_query_flag.txt
RUN echo "FLAG_PLACEHOLDER_12" > /flags/status_page_flag.txt

# Download and install Nagios
WORKDIR /tmp
RUN wget https://assets.nagios.com/downloads/nagioscore/releases/nagios-4.4.6.tar.gz && \
    tar -zxf nagios-4.4.6.tar.gz && \
    cd nagios-4.4.6 && \
    ./configure --with-httpd-conf=/etc/apache2/sites-available && \
    make all && \
    make install-groups-users && \
    usermod -a -G nagios www-data && \
    make install && \
    make install-daemoninit && \
    make install-commandmode && \
    make install-config && \
    make install-webconf && \
    cd .. && \
    rm -rf nagios-4.4.6*

# Download and install Nagios plugins
RUN wget https://nagios-plugins.org/download/nagios-plugins-2.3.3.tar.gz && \
    tar -zxf nagios-plugins-2.3.3.tar.gz && \
    cd nagios-plugins-2.3.3 && \
    ./configure --with-nagios-user=nagios --with-nagios-group=nagios && \
    make && \
    make install && \
    cd .. && \
    rm -rf nagios-plugins-2.3.3*

# Install Apache utilities and configure Nagios with default credentials
RUN apt-get update && apt-get install -y apache2-utils && rm -rf /var/lib/apt/lists/*
RUN htpasswd -b -c /usr/local/nagios/etc/htpasswd.users nagiosadmin nagiosadmin

# Configure Nagios with vulnerable command
COPY nagios.cfg /usr/local/nagios/etc/nagios.cfg
COPY commands.cfg /usr/local/nagios/etc/objects/commands.cfg
COPY localhost.cfg /usr/local/nagios/etc/objects/localhost.cfg
COPY vulnerable_status.php /usr/local/nagios/share/vulnerable_status.php

# Download and install Elasticsearch
RUN wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-7.10.2-linux-x86_64.tar.gz && \
    tar -xzf elasticsearch-7.10.2-linux-x86_64.tar.gz && \
    mv elasticsearch-7.10.2 /usr/local/elasticsearch && \
    rm elasticsearch-7.10.2-linux-x86_64.tar.gz

# Configure Elasticsearch
COPY elasticsearch.yml /usr/local/elasticsearch/config/elasticsearch.yml
RUN mkdir -p /usr/local/elasticsearch/data && \
    chown -R ctf-user:ctf-user /usr/local/elasticsearch

# Add flag to Elasticsearch
COPY setup_elasticsearch.sh /setup_elasticsearch.sh
RUN chmod +x /setup_elasticsearch.sh

# Copy and set up entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
# Fix line endings just in case
RUN sed -i 's/\r$//' /entrypoint.sh

# Enable Apache modules
RUN a2enmod cgi

# Expose ports
EXPOSE 22 8080 9200

# Start services
CMD ["/bin/bash", "/entrypoint.sh"] 