FROM alpine:latest

RUN apk update && apk add --no-cache \
    openssh-server \
    openssh-sftp-server \
    openssh-client \
    sudo \
    bash \
    vim \
    nano\
    nmap \
    curl \
    shadow \
    python3 \
    py3-pip \
    gcc \
    musl-dev \
    python3-dev \
    && rm -rf /var/cache/apk/*

# Create ctf-user
RUN useradd -m -s /bin/bash ctf-user && \
    echo "ctf-user:password" | chpasswd && \
    usermod -aG wheel ctf-user && \
    echo "ctf-user ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# Configure SSH
RUN mkdir -p /var/run/sshd
RUN ssh-keygen -A  # Generate host keys

# Copy SSH config
COPY sshd_config /etc/ssh/sshd_config
RUN chmod 644 /etc/ssh/sshd_config

# Set up .ssh directory
RUN mkdir -p /home/ctf-user/.ssh && \
    touch /home/ctf-user/.ssh/authorized_keys && \
    chown -R root:root /home/ctf-user/.ssh && \
    chmod 750 /home/ctf-user/.ssh && \
    chmod 650 /home/ctf-user/.ssh/authorized_keys

# Set up Python and Flask
COPY requirements.txt /requirements.txt
RUN python3 -m venv /app/venv && \
    . /app/venv/bin/activate && \
    pip install --no-cache-dir -r /requirements.txt

# Copy Flask application
COPY app.py /app/app.py
RUN chmod +x /app/app.py

# Copy and set up entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Fix line endings just in case
RUN sed -i 's/\r$//' /entrypoint.sh

EXPOSE 22 5000

CMD ["/bin/bash", "/entrypoint.sh"]