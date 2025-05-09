FROM ubuntu:20.04

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y \
    apache2 \
    mariadb-server \
    php \
    php-mysql \
    php-curl \
    php-gd \
    php-mbstring \
    php-xml \
    php-xmlrpc \
    php-soap \
    php-intl \
    php-zip \
    wget \
    unzip \
    openssh-server \
    curl \
    sudo \
    nano \
    && rm -rf /var/lib/apt/lists/*

# Install wp-cli
RUN curl -O https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar && \
    chmod +x wp-cli.phar && \
    mv wp-cli.phar /usr/local/bin/wp && \
    echo "PATH=$PATH:/usr/local/bin" >> ~/.bashrc && \
    echo "alias wp='wp --allow-root'" >> ~/.bashrc

# Set up SSH
RUN mkdir /var/run/sshd
RUN echo 'root:password' | chpasswd
RUN echo 'PermitRootLogin yes' >> /etc/ssh/sshd_config
RUN sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

# Create a CTF user with sudo rights, but restrict from using sudo for certain commands
RUN useradd -m -s /bin/bash ctf-user && \
    echo "ctf-user:password" | chpasswd && \
    adduser ctf-user sudo && \
    echo "ctf-user ALL=(ALL) NOPASSWD:ALL, !/usr/bin/cat /var/www/html/wp-admin/secret.php, !/usr/bin/cat /var/www/html/wp-content/plugins/custom-plugin/custom-plugin.php, !/usr/bin/cat /var/www/html/wp-content/plugins/secure-plugin/secure-plugin.php, !/usr/bin/grep */secret.php, !/usr/bin/grep */custom-plugin.php, !/usr/bin/grep */secure-plugin.php" > /etc/sudoers.d/ctf-user && \
    echo "alias wp='wp --allow-root'" >> /home/ctf-user/.bashrc

# Configure Apache
RUN a2enmod rewrite
COPY apache-config.conf /etc/apache2/sites-available/000-default.conf

# Set up MariaDB
RUN service mysql start && \
    mysql -e "CREATE DATABASE wordpress;" && \
    mysql -e "CREATE USER 'wp_user'@'localhost' IDENTIFIED BY 'password';" && \
    mysql -e "GRANT ALL PRIVILEGES ON wordpress.* TO 'wp_user'@'localhost';" && \
    mysql -e "FLUSH PRIVILEGES;" && \
    mysql -e "CREATE TABLE wordpress.wp_secrets (id INT AUTO_INCREMENT PRIMARY KEY, secret_name VARCHAR(255), flag_value VARCHAR(255));" && \
    mysql -e "INSERT INTO wordpress.wp_secrets (secret_name, flag_value) VALUES ('mysql_flag', 'FLAG_PLACEHOLDER_2');"

# Download and install WordPress
WORKDIR /var/www/html
RUN rm -rf /var/www/html/*
RUN wget https://wordpress.org/latest.tar.gz && \
    tar -xzf latest.tar.gz && \
    mv wordpress/* . && \
    rmdir wordpress && \
    rm latest.tar.gz

# Configure WordPress
COPY wp-config.php /var/www/html/
RUN chown www-data:www-data /var/www/html/wp-config.php

# Create the custom plugin with flag
RUN mkdir -p /var/www/html/wp-content/plugins/custom-plugin
COPY custom-plugin.php /var/www/html/wp-content/plugins/custom-plugin/custom-plugin.php
RUN chown root:www-data /var/www/html/wp-content/plugins/custom-plugin/custom-plugin.php && \
    chmod 440 /var/www/html/wp-content/plugins/custom-plugin/custom-plugin.php

# Create the secure plugin with flag
RUN mkdir -p /var/www/html/wp-content/plugins/secure-plugin
COPY secure-plugin.php /var/www/html/wp-content/plugins/secure-plugin/secure-plugin.php
RUN chown root:www-data /var/www/html/wp-content/plugins/secure-plugin/secure-plugin.php && \
    chmod 440 /var/www/html/wp-content/plugins/secure-plugin/secure-plugin.php

# Add the hidden admin page with flag
COPY secret.php /var/www/html/wp-admin/secret.php
RUN chown root:www-data /var/www/html/wp-admin/secret.php && \
    chmod 440 /var/www/html/wp-admin/secret.php

# Secure directories
RUN chown -R www-data:www-data /var/www/html && \
    find /var/www/html -type d -exec chmod 755 {} \; && \
    find /var/www/html -type f -exec chmod 644 {} \; && \
    chmod 440 /var/www/html/wp-admin/secret.php && \
    chmod 440 /var/www/html/wp-content/plugins/custom-plugin/custom-plugin.php && \
    chmod 440 /var/www/html/wp-content/plugins/secure-plugin/secure-plugin.php

# Add startup script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose ports
EXPOSE 22 80 3306

# Start services
CMD ["/entrypoint.sh"] 