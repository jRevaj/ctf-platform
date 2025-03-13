FROM debian:11

# Avoid prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install required packages
RUN apt-get update && apt-get install -y \
    openssh-server \
    curl \
    wget \
    git \
    redis-server \
    nginx \
    sqlite3 \
    supervisor \
    ca-certificates \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Set up SSH
RUN mkdir -p /var/run/sshd
RUN echo 'root:intranet_root_password' | chpasswd
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config

# Create ctf-user
RUN useradd -m -s /bin/bash ctf-user
RUN echo "ctf-user:intranet_password" | chpasswd

# Create flags directory
RUN mkdir -p /flags
RUN chmod 700 /flags

# Create flag files
RUN echo "FLAG_PLACEHOLDER_4" > /flags/api_endpoint_flag.txt
RUN echo "FLAG_PLACEHOLDER_5" > /flags/redis_command_flag.txt
RUN echo "FLAG_PLACEHOLDER_6" > /flags/session_hijacking_flag.txt

# Configure Redis with no authentication (vulnerability)
COPY redis.conf /etc/redis/redis.conf

# Download and set up Gogs
WORKDIR /opt
RUN wget -O gogs.tar.gz https://dl.gogs.io/0.12.9/gogs_0.12.9_linux_amd64.tar.gz && \
    tar -xzf gogs.tar.gz && \
    rm gogs.tar.gz

# Configure Gogs
RUN mkdir -p /opt/gogs/custom/conf/
COPY app.ini /opt/gogs/custom/conf/app.ini
RUN mkdir -p /var/lib/gogs
RUN chown -R ctf-user:ctf-user /opt/gogs /var/lib/gogs

# Set up the vulnerable API endpoint
COPY api_endpoints.go /opt/gogs/routes/api/v1/api_endpoints.go

# Configure Nginx for Gogs
COPY gogs.nginx.conf /etc/nginx/sites-available/default

# Set up supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy and set up entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
# Fix line endings just in case
RUN sed -i 's/\r$//' /entrypoint.sh

# Store the session hijacking flag in Redis
RUN redis-server /etc/redis/redis.conf --daemonize yes && \
    redis-cli set secret_flag "FLAG_PLACEHOLDER_5" && \
    redis-cli shutdown

# Expose ports
EXPOSE 22 3000 6379

# Start services
CMD ["/bin/bash", "/entrypoint.sh"] 