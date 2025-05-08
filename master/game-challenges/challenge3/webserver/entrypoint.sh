#!/bin/bash

# Start services
service mysql start
service apache2 start
service ssh start

# Install wp-cli
echo "Installing wp-cli..."
curl -O https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar
chmod +x wp-cli.phar
mv wp-cli.phar /usr/local/bin/wp
echo "wp-cli installed successfully."

# Ensure database is created properly
if [ ! -d /var/lib/mysql/wordpress ]; then
    echo "Setting up MySQL database..."
    mysql -e "CREATE DATABASE IF NOT EXISTS wordpress;"
    mysql -e "CREATE USER IF NOT EXISTS 'wp_user'@'localhost' IDENTIFIED BY 'password';"
    mysql -e "GRANT ALL PRIVILEGES ON wordpress.* TO 'wp_user'@'localhost';"
    mysql -e "FLUSH PRIVILEGES;"
    mysql -e "CREATE TABLE IF NOT EXISTS wordpress.wp_secrets (id INT AUTO_INCREMENT PRIMARY KEY, secret_name VARCHAR(255), flag_value VARCHAR(255));"
    mysql -e "INSERT INTO wordpress.wp_secrets (secret_name, flag_value) VALUES ('mysql_flag', 'FLAG_PLACEHOLDER_2');"
    echo "MySQL database setup completed."
fi

# Set proper permissions
chown -R www-data:www-data /var/www/html

# Check if WordPress is installed, if not install it
echo "Checking WordPress installation..."
if ! wp core is-installed --path=/var/www/html --allow-root; then
    echo "Installing WordPress..."
    wp core install --path=/var/www/html --url=localhost --title="WordPress Site" --admin_user=admin --admin_password=password --admin_email=admin@example.com --allow-root
    echo "WordPress installed successfully."
    
    # Activate the custom plugin
    wp plugin activate custom-plugin --path=/var/www/html --allow-root
    wp plugin activate secure-plugin --path=/var/www/html --allow-root

    echo "WordPress configuration completed."
else
    echo "WordPress is already installed."
fi

# Remove access to this entrypoint file
chmod 700 /entrypoint.sh
chown root:root /entrypoint.sh

echo "All services started. Container is ready."

# Keep container running
tail -f /dev/null 