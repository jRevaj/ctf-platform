FROM ubuntu:22.04

# Avoid prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install required packages
RUN apt-get update && apt-get install -y \
    apache2 \
    mariadb-server \
    php \
    php-mysql \
    php-mbstring \
    php-curl \
    php-xml \
    php-zip \
    openssh-server \
    curl \
    wget \
    nano \
    unzip \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Set up SSH
RUN mkdir -p /var/run/sshd
RUN echo 'root:webserver_root_password' | chpasswd
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config

# Create ctf-user
RUN useradd -m -s /bin/bash ctf-user
RUN echo "ctf-user:webserver_password" | chpasswd
RUN echo "ctf-user ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/ctf-user

# Create directory for flags
RUN mkdir -p /flags
RUN chmod 700 /flags

# Create flag files
RUN echo "FLAG_PLACEHOLDER_1" > /flags/wordpress_plugin_flag.txt
RUN echo "FLAG_PLACEHOLDER_2" > /flags/mysql_user_flag.txt
RUN echo "FLAG_PLACEHOLDER_3" > /flags/hidden_admin_flag.txt

# Set up MySQL for the vulnerability
COPY my.cnf /etc/mysql/my.cnf
COPY setup.sql /tmp/setup.sql

# Download and set up WordPress
RUN mkdir -p /var/www/html
WORKDIR /var/www/html
RUN wget https://wordpress.org/latest.tar.gz && \
    tar -xzvf latest.tar.gz && \
    mv wordpress/* . && \
    rmdir wordpress && \
    rm latest.tar.gz

# Install a vulnerable WordPress plugin (simulated)
RUN mkdir -p /var/www/html/wp-content/plugins/vulnerable-plugin
COPY vulnerable-plugin.php /var/www/html/wp-content/plugins/vulnerable-plugin/vulnerable-plugin.php

# Create hidden admin panel
COPY secret.php /var/www/html/wp-admin/secret.php

# Set correct permissions
RUN chown -R www-data:www-data /var/www/html
RUN chmod -R 755 /var/www/html

# Configure Apache
COPY 000-default.conf /etc/apache2/sites-available/000-default.conf
RUN a2enmod headers

# Copy and set up entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
# Fix line endings just in case
RUN sed -i 's/\r$//' /entrypoint.sh

# Expose ports
EXPOSE 22 80 3306

# Start services
CMD ["/bin/bash", "/entrypoint.sh"] 