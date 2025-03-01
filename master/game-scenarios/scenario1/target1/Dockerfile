FROM alpine:latest

RUN apk update && apk add --no-cache \
    openssh-server \
    openssh-sftp-server \
    mysql \
    mysql-client \
    apache2 \
    bash \
    shadow \
    php \
    php-apache2 \
    php-pdo \
    php-pdo_mysql \
    && rm -rf /var/cache/apk/*

# Create ctf-user
RUN adduser -D -h /home/ctf-user -s /bin/bash ctf-user

# Configure SSH
RUN mkdir -p /var/run/sshd
RUN ssh-keygen -A  # Generate host keys

# Copy SSH config
COPY sshd_config /etc/ssh/sshd_config
RUN chmod 644 /etc/ssh/sshd_config

# Create flags directory with proper permissions
RUN mkdir -p /flags && \
    chown ctf-user:ctf-user /flags && \
    chmod 755 /flags

COPY flag.txt /flags/flag.txt

# Create .ssh directory with proper permissions
RUN mkdir -p /home/ctf-user/.ssh && \
    touch /home/ctf-user/.ssh/authorized_keys && \
    chown -R ctf-user:ctf-user /home/ctf-user/.ssh && \
    chmod 700 /home/ctf-user/.ssh && \
    chmod 600 /home/ctf-user/.ssh/authorized_keys

# Set up Apache and copy web files
COPY 000-default.conf /etc/apache2/conf.d/default.conf
COPY index.php /var/www/html/index.php
RUN chown -R apache:apache /var/www/html

# Copy and set up entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
# Fix line endings just in case
RUN sed -i 's/\r$//' /entrypoint.sh

EXPOSE 22 80 3306

CMD ["/bin/bash", "/entrypoint.sh"]
