#!/bin/bash

# Setup SSH
mkdir -p /home/ctf-user/.ssh
touch /home/ctf-user/.ssh/authorized_keys
chown -R ctf-user:ctf-user /home/ctf-user/.ssh
chmod 700 /home/ctf-user/.ssh
chmod 600 /home/ctf-user/.ssh/authorized_keys

# Start MySQL and create database with flag
service mysql start
mysql -u root << EOF
CREATE DATABASE IF NOT EXISTS ctf_db;
USE ctf_db;
CREATE TABLE IF NOT EXISTS secrets (
    id INT PRIMARY KEY,
    secret_data TEXT
);
INSERT INTO secrets VALUES (1, 'FLAG_PLACEHOLDER_2');
EOF

# Start Apache
service apache2 start

# Start SSH
/usr/sbin/sshd -D