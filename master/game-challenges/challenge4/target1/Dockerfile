FROM alpine:latest

RUN apk update && apk add --no-cache \
    openssh-server \
    openssh-sftp-server \
    openssh-client \
    mysql \
    mysql-client \
    apache2 \
    bash \
    vim \
    nano\
    nmap \
    curl \
    shadow \
    php \
    php-apache2 \
    php-pdo \
    php-pdo_mysql \
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

# Create flags directory
RUN mkdir -p /flags && \
    chown ctf-user:ctf-user /flags && \
    chmod 755 /flags

COPY flag.txt /flags/flag.txt

# Set up .ssh directory
RUN mkdir -p /home/ctf-user/.ssh && \
    touch /home/ctf-user/.ssh/authorized_keys && \
    chown -R root:root /home/ctf-user/.ssh && \
    chmod 750 /home/ctf-user/.ssh && \
    chmod 650 /home/ctf-user/.ssh/authorized_keys

# Set up Apache and copy web files
COPY index.php /var/www/html/index.php
RUN chown -R apache:apache /var/www/html

# Set up Python and Flask
COPY requirements.txt /app/requirements.txt
RUN python3 -m venv /app/venv && \
    . /app/venv/bin/activate && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy Flask application
COPY app.py /app/app.py
RUN chmod +x /app/app.py

# Copy and compile C file with secret
COPY expose_secret.c /expose_secret.c
RUN gcc -o /usr/local/bin/expose_secret /expose_secret.c
RUN chmod +x /usr/local/bin/expose_secret

# Copy and set up entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Fix line endings just in case
RUN sed -i 's/\r$//' /entrypoint.sh

EXPOSE 22 80 3306 8080

CMD ["/bin/bash", "/entrypoint.sh"]
