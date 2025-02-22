FROM ubuntu:22.04

# Install necessary services
RUN apt-get update && apt-get install -y \
    openssh-server \
    apache2 \
    mysql-server \
    php \
    php-mysql \
    && rm -rf /var/lib/apt/lists/*

# Create ctf-user
RUN useradd -m -s /bin/bash ctf-user

# Configure SSH
RUN mkdir /var/run/sshd
COPY sshd_config /etc/ssh/sshd_config

# Setup Apache
COPY apache-config/000-default.conf /etc/apache2/sites-available/
COPY web-content/ /var/www/html/
RUN chown -R www-data:www-data /var/www/html

# Setup MySQL
COPY mysql-config/setup.sql /docker-entrypoint-initdb.d/
COPY mysql-config/my.cnf /etc/mysql/my.cnf

# Create flag locations
RUN mkdir -p /var/www/hidden && \
    echo "FLAG_PLACEHOLDER_1" > /var/www/hidden/secret.txt && \
    chown www-data:www-data /var/www/hidden/secret.txt && \
    chmod 640 /var/www/hidden/secret.txt

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 22 80 3306

ENTRYPOINT ["/entrypoint.sh"]