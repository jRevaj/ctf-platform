FROM alpine:latest

RUN apk update && apk add --no-cache \
    openssh-server \
    openssh-sftp-server \
    openssh-client \
    bash \
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
RUN adduser -D -h /home/ctf-user -s /bin/bash ctf-user

# Configure SSH
RUN mkdir -p /var/run/sshd
RUN ssh-keygen -A  # Generate host keys

# Copy SSH config
COPY sshd_config /etc/ssh/sshd_config
RUN chmod 644 /etc/ssh/sshd_config

# Create .ssh directory with proper permissions
RUN mkdir -p /home/ctf-user/.ssh && \
    touch /home/ctf-user/.ssh/authorized_keys && \
    chown -R ctf-user:ctf-user /home/ctf-user/.ssh && \
    chmod 700 /home/ctf-user/.ssh && \
    chmod 600 /home/ctf-user/.ssh/authorized_keys

# Set up Python and Flask
COPY requirements.txt /requirements.txt
RUN python3 -m venv /app/venv && \
    . /app/venv/bin/activate && \
    pip install --no-cache-dir -r /requirements.txt

# Copy Flask application
COPY app.py /app.py
RUN chmod +x /app.py

# Copy and set up entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Fix line endings just in case
RUN sed -i 's/\r$//' /entrypoint.sh

EXPOSE 22 5000

CMD ["/bin/bash", "/entrypoint.sh"]