#!/bin/bash

# Debug info
echo "Starting entrypoint script" > /tmp/debug.log
echo "Current directory: $(pwd)" >> /tmp/debug.log
ls -la / >> /tmp/debug.log

# Set a specific password for ctf-user
echo "ctf-user:admin" | chpasswd
echo "Set password for ctf-user" >> /tmp/debug.log

# Create a hint file for the challenge
echo "I found these credentials in the admin's notes:" > /home/ctf-user/network_scan.txt
echo "Server: 172.1.0.3 - Username: ctf-user, Password: s3cret_t4rget2" >> /home/ctf-user/network_scan.txt
echo "There might be more servers on the network..." >> /home/ctf-user/network_scan.txt
chmod 750 /home/ctf-user/network_scan.txt
chown root:root /home/ctf-user/network_scan.txt

# Hide the secret in hidden directories with misleading names
mkdir -p /var/www/.backup/.system
echo '#!/bin/bash' > /var/www/.backup/.system/kernel_cleanup.sh
echo 'expose_secret' >> /var/www/.backup/.system/kernel_cleanup.sh
chmod 755 /var/www/.backup/.system/kernel_cleanup.sh
chown root:root /var/www/.backup/.system/kernel_cleanup.sh

# Create a secret config file with the string
mkdir -p /etc/.hidden
echo "s3cret_t4rget2" > /etc/.hidden/network.conf
chmod 644 /etc/.hidden/network.conf
chown root:root /etc/.hidden/network.conf

# Setup SSH
mkdir -p /home/ctf-user/.ssh
touch /home/ctf-user/.ssh/authorized_keys
echo "SSH directory created" >> /tmp/debug.log
ls -la /home/ctf-user/.ssh >> /tmp/debug.log

# Set proper permissions for SSH
chown -R root:root /home/ctf-user/.ssh
chmod 700 /home/ctf-user/.ssh
chmod 600 /home/ctf-user/.ssh/authorized_keys
echo "SSH permissions set" >> /tmp/debug.log

# Ensure SSH host keys exist
ssh-keygen -A
echo "SSH host keys generated" >> /tmp/debug.log

# Start MySQL and create database with flag
mkdir -p /run/mysqld
chown -R mysql:mysql /run/mysqld
mysql_install_db --user=mysql --datadir=/var/lib/mysql
mysqld_safe --user=mysql &
sleep 5
echo "MySQL started" >> /tmp/debug.log

# Create database and set up users
mysql -u root << EOF
CREATE DATABASE IF NOT EXISTS ctf_db;
USE ctf_db;

-- Create tables
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50),
    password VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS secrets (
    id INT PRIMARY KEY,
    secret_data TEXT
);

-- Insert data
INSERT INTO users (username, password) VALUES 
('admin', 'admin123'),
('user', 'user123');

INSERT INTO secrets VALUES (1, 'FLAG_PLACEHOLDER_3');

-- Create MySQL user with same password as system user
CREATE USER 'ctf-user'@'localhost' IDENTIFIED BY 'admin123';
GRANT SELECT ON ctf_db.* TO 'ctf-user'@'localhost';
FLUSH PRIVILEGES;
EOF

echo "Setup SQL executed" >> /tmp/debug.log
echo "Flag inserted into database" >> /tmp/debug.log

# Start Apache
mkdir -p /run/apache2
mkdir -p /var/www/html
mkdir -p /var/www/hidden
# Ensure index.php is in the right place
if [ ! -f /var/www/html/index.php ]; then
    cp /index.php /var/www/html/index.php 2>> /tmp/debug.log
fi
echo "Apache document root contents:" >> /tmp/debug.log
ls -la /var/www/html >> /tmp/debug.log
httpd -D FOREGROUND &
echo "Apache started" >> /tmp/debug.log

# Start SSH in background
echo "Starting SSH daemon" >> /tmp/debug.log
/usr/sbin/sshd
echo "SSH daemon started" >> /tmp/debug.log

# Start Flask application
source /app/venv/bin/activate
python3 /app/app.py &
echo "Flask application started on port 8080" >> /tmp/debug.log

# Remove access to this entrypoint file
chmod 700 /entrypoint.sh
chown root:root /entrypoint.sh

# Keep container running
tail -f /dev/null