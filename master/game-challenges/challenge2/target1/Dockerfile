FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Update and install packages
RUN apt-get update && apt-get install -y \
    openssh-server \
    openssh-client \
    mysql-server \
    apache2 \
    bash \
    curl \
    php \
    php-mysql \
    redis-server \
    sudo \
    cron \
    pwgen \
    net-tools \
    netcat \
    && rm -rf /var/lib/apt/lists/*

# Insert flag into Dockerfile
# This is FLAG_PLACEHOLDER_1
RUN echo "FLAG_PLACEHOLDER_1" > /etc/flag1.txt

# Create ctf-user
RUN useradd -m -s /bin/bash ctf-user

# Configure SSH
RUN mkdir -p /var/run/sshd
RUN mkdir -p /var/run/mysqld && chmod 777 /var/run/mysqld

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

# Set up weak sudo configuration for www-data (Apache) user
RUN echo "www-data ALL=(ALL) NOPASSWD: /usr/bin/find, /bin/cat" > /etc/sudoers.d/www-data && \
    chmod 440 /etc/sudoers.d/www-data

# Set up Apache and copy web files
COPY 000-default.conf /etc/apache2/sites-available/000-default.conf
COPY index.php /var/www/html/index.php
RUN chown -R www-data:www-data /var/www/html

# Set up Redis with no authentication
COPY redis.conf /etc/redis/redis.conf

# Set up cron jobs
RUN mkdir -p /target1/cron && \
    chmod 755 /target1/cron
COPY backup.sh /target1/cron/backup.sh
RUN chmod +x /target1/cron/backup.sh && \
    echo "*/10 * * * * root /target1/cron/backup.sh" > /etc/cron.d/backup

# Copy MySQL configuration
COPY my.cnf /etc/mysql/my.cnf
COPY setup.sql /docker-entrypoint-initdb.d/setup.sql

# Copy and set up entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
# Fix line endings just in case
RUN sed -i 's/\r$//' /entrypoint.sh

# Add SSH key for lateral movement
COPY id_rsa /home/ctf-user/.ssh/id_rsa
COPY id_rsa.pub /home/ctf-user/.ssh/id_rsa.pub
RUN chmod 600 /home/ctf-user/.ssh/id_rsa && \
    chmod 644 /home/ctf-user/.ssh/id_rsa.pub && \
    chown -R ctf-user:ctf-user /home/ctf-user/.ssh

EXPOSE 22 80 3306 6379

CMD ["/bin/bash", "/entrypoint.sh"]
