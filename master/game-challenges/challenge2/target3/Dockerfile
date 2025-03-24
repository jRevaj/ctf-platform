FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Update and install packages
RUN apt-get update && apt-get install -y \
    openssh-server \
    openssh-client \
    bash \
    curl \
    openjdk-11-jdk \
    git \
    memcached \
    sudo \
    wget \
    netcat \
    && rm -rf /var/lib/apt/lists/*

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

# Set up Jenkins
RUN mkdir -p /target3/jenkins
WORKDIR /target3/jenkins
RUN wget https://get.jenkins.io/war-stable/2.346.3/jenkins.war
COPY jenkins/ /target3/jenkins/
RUN chown -R ctf-user:ctf-user /target3

# Set up Memcached with no authentication (vulnerable)
COPY memcached.conf /etc/memcached.conf

# Copy and set up entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Fix line endings just in case
RUN sed -i 's/\r$//' /entrypoint.sh

EXPOSE 22 8080 11211

CMD ["/bin/bash", "/entrypoint.sh"]