FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Update and install packages
RUN apt-get update && apt-get install -y \
    openssh-server \
    openssh-client \
    bash \
    curl \
    wget \
    gnupg \
    nodejs \
    npm \
    net-tools \
    iputils-ping \
    sudo \
    netcat

# Setup MongoDB 6.0 repository properly
RUN wget -qO - https://pgp.mongodb.com/server-6.0.asc | \
    gpg -o /usr/share/keyrings/mongodb-server-6.0.gpg --dearmor && \
    echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-6.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/6.0 multiverse" | \
    tee /etc/apt/sources.list.d/mongodb-org-6.0.list && \
    apt-get update && \
    apt-get install -y mongodb-org mongodb-org-shell mongodb-mongosh && \
    mkdir -p /data/db && \
    chmod 777 /data/db

# Create ctf-user
RUN useradd -m -s /bin/bash ctf-user

# Configure SSH
RUN mkdir -p /var/run/sshd

# Copy SSH config
COPY sshd_config /etc/ssh/sshd_config
RUN chmod 644 /etc/ssh/sshd_config

# Create .ssh directory with proper permissions
RUN mkdir -p /home/ctf-user/.ssh && \
    touch /home/ctf-user/.ssh/authorized_keys && \
    chown -R ctf-user:ctf-user /home/ctf-user/.ssh && \
    chmod 700 /home/ctf-user/.ssh && \
    chmod 600 /home/ctf-user/.ssh/authorized_keys

# Set up Node.js application
RUN mkdir -p /target2/app
COPY app/ /target2/app/
RUN cd /target2/app && npm install || true

# Set up MongoDB
RUN mkdir -p /target2/mongodb
COPY mongodb/ /target2/mongodb/
RUN chown -R ctf-user:ctf-user /target2

# Set up log poisoning vulnerability
RUN mkdir -p /var/log/nodeapp && \
    useradd -r -s /bin/false www-data || true && \
    chown -R www-data:www-data /var/log/nodeapp && \
    chmod 777 /var/log/nodeapp

# Copy and set up entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Fix line endings just in case
RUN sed -i 's/\r$//' /entrypoint.sh

EXPOSE 22 3000 27017

CMD ["/bin/bash", "/entrypoint.sh"]