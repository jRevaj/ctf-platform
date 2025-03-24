#!/bin/bash

# Start SSH service
service ssh start
echo "SSH service started"

# Initialize MySQL data directory if needed
if [ ! -d "/var/lib/mysql/mysql" ]; then
    echo "Initializing MySQL data directory..."
    mysqld --initialize-insecure --user=mysql
fi

# Start MySQL service
service mysql start
echo "MySQL service started"

# Wait for MySQL to be ready
echo "Waiting for MySQL to be ready..."
while ! mysqladmin ping -h localhost --silent; do
    sleep 1
done
echo "MySQL is ready"

# Run setup SQL script if database not already set up
if ! mysql -e "USE wordpress;" 2>/dev/null; then
    echo "Setting up MySQL database..."
    mysql < /tmp/setup.sql
    echo "MySQL database setup completed"
fi

# Configure WordPress if not already configured
if [ ! -f "/var/www/html/wp-config.php" ]; then
    echo "Configuring WordPress..."
    cp /var/www/html/wp-config-sample.php /var/www/html/wp-config.php
    
    # Update WordPress configuration
    sed -i "s/database_name_here/wordpress/" /var/www/html/wp-config.php
    sed -i "s/username_here/wp_user/" /var/www/html/wp-config.php
    sed -i "s/password_here/weakpassword/" /var/www/html/wp-config.php
    
    # Add authentication unique keys and salts
    sed -i "s/put your unique phrase here/$(date +%s%N | sha256sum | base64 | head -c 64)/g" /var/www/html/wp-config.php
    
    # Set correct permissions
    chown -R www-data:www-data /var/www/html
    chmod -R 755 /var/www/html
    
    echo "WordPress configured"
fi

# Start Apache
service apache2 start
echo "Apache service started"

# Keep container running
echo "All services started. Container is now running..."
tail -f /dev/null 