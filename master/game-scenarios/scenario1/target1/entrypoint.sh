#!/bin/bash

# Debug info
echo "Starting entrypoint script" > /tmp/debug.log
echo "Current directory: $(pwd)" >> /tmp/debug.log
ls -la / >> /tmp/debug.log

# Set a password for ctf-user for debugging
echo "ctf-user:password" | chpasswd
echo "Set password for ctf-user" >> /tmp/debug.log

# Setup SSH
mkdir -p /home/ctf-user/.ssh
touch /home/ctf-user/.ssh/authorized_keys
echo "SSH directory created" >> /tmp/debug.log
ls -la /home/ctf-user/.ssh >> /tmp/debug.log

# Set proper permissions
chown -R ctf-user:ctf-user /home/ctf-user/.ssh
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
CREATE USER 'ctf-user'@'localhost' IDENTIFIED BY 'password';
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

# Start SSH with debug logging to help troubleshoot
echo "Starting SSH daemon" >> /tmp/debug.log
/usr/sbin/sshd -D -e