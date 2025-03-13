#!/bin/bash

# Start SSH service
service ssh start
echo "SSH service started"

# Create necessary directories for vsftpd
mkdir -p /var/run/vsftpd/empty
mkdir -p /var/log
touch /var/log/ftp_uploads.log
chmod 666 /var/log/ftp_uploads.log

# Start FTP service
service vsftpd start
echo "FTP service started"

# Create necessary directories for Samba
mkdir -p /var/log/samba
mkdir -p /var/lib/samba
mkdir -p /run/samba

# Start Samba service
service smbd start
service nmbd start
echo "Samba services started"

# Set up a cron job to check for PHP files in FTP directory
echo "* * * * * root /var/ftp/ftp_flag_handler.sh" > /etc/cron.d/ftp-monitor
service cron start
echo "Cron service started"

# Keep container running
echo "All services started. Container is now running..."
tail -f /dev/null 