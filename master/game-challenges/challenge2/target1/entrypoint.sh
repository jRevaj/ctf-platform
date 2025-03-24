#!/bin/bash

# Debug info
echo "Starting entrypoint script" > /tmp/debug.log
echo "Current directory: $(pwd)" >> /tmp/debug.log
ls -la / >> /tmp/debug.log

# Set a specific password for ctf-user
echo "ctf-user:starthere" | chpasswd
echo "Set password for ctf-user" >> /tmp/debug.log

# Create a hint file for the challenge
echo "I found these credentials in the admin's notes:" > /home/ctf-user/network_scan.txt
echo "Server: 172.1.0.3 - Username: ctf-user, Password: s3cret_t4rget2" >> /home/ctf-user/network_scan.txt
echo "There might be more servers on the network..." >> /home/ctf-user/network_scan.txt
chmod 644 /home/ctf-user/network_scan.txt
chown ctf-user:ctf-user /home/ctf-user/network_scan.txt

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

# Generate SSH host keys
ssh-keygen -A
echo "SSH host keys generated" >> /tmp/debug.log

# Start MySQL and create database with flag
service mysql start
sleep 5
echo "MySQL started" >> /tmp/debug.log

# MySQL flag - FLAG_PLACEHOLDER_3
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

-- Create MySQL user with excessive privileges - intentional vulnerability
CREATE USER 'webapp'@'%' IDENTIFIED BY 'webapp_password';
GRANT ALL PRIVILEGES ON *.* TO 'webapp'@'%' WITH GRANT OPTION;

-- Create MySQL user with same password as system user
CREATE USER 'ctf-user'@'localhost' IDENTIFIED BY 'starthere';
GRANT SELECT ON ctf_db.* TO 'ctf-user'@'localhost';

-- Create remote MySQL user for target2 application
CREATE USER 'remoteuser'@'%' IDENTIFIED WITH mysql_native_password BY 'remotep@ss';
GRANT ALL PRIVILEGES ON ctf_db.* TO 'remoteuser'@'%';

FLUSH PRIVILEGES;
EOF

echo "Setup SQL executed" >> /tmp/debug.log
echo "Flag inserted into database" >> /tmp/debug.log

# Setup Redis service with no authentication (vulnerable)
mkdir -p /var/run/redis
mkdir -p /var/log/redis
touch /var/log/redis/redis-server.log
chown -R redis:redis /var/run/redis /var/log/redis
# Start Redis with custom config
redis-server /etc/redis/redis.conf &
sleep 2
# Store SSH keys in Redis for lateral movement (intentional vulnerability)
redis-cli SET ssh_key "$(cat /home/ctf-user/.ssh/id_rsa)"
echo "Redis started with no authentication" >> /tmp/debug.log

# Setup cron job
mkdir -p /target1/cron
service cron start
echo "Cron service started and job configured" >> /tmp/debug.log

# Start Apache
a2ensite 000-default
service apache2 start
echo "Apache document root contents:" >> /tmp/debug.log
ls -la /var/www/html >> /tmp/debug.log
echo "Apache started" >> /tmp/debug.log

# Start SSH with debug logging to help troubleshoot
echo "Starting SSH daemon" >> /tmp/debug.log
/usr/sbin/sshd -D -e