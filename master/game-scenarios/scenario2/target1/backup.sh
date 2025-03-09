#!/bin/bash

# Backup script for database
# This runs as root via cron job

# Flag placed in this file
# FLAG_PLACEHOLDER_4

# Set date format for backup file name
DATE=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_DIR="/var/backups/mysql"

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR
chmod 700 $BACKUP_DIR

# Database credentials - intentionally insecure
DB_USER="root"
DB_PASS="mysql_root_password"
DB_NAME="ctf_database"

# API key for external service - intentionally exposed
API_KEY="ak_live_JdJK38dgLK892jdDJKL38djDK83JdkL"

# Backup command
echo "Starting MySQL backup at $(date)"
mysqldump --user=$DB_USER --password=$DB_PASS --databases $DB_NAME > $BACKUP_DIR/mysql_backup_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/mysql_backup_$DATE.sql

# Set permissions
chmod 600 $BACKUP_DIR/mysql_backup_$DATE.sql.gz

# Basic cleanup - keep only last 5 backups
ls -tp $BACKUP_DIR/mysql_backup_* | grep -v '/$' | tail -n +6 | xargs -I {} rm -- {}

echo "Backup completed at $(date)"

# Insecure permissions for the backup directory
chmod 777 $BACKUP_DIR

# Call to another insecure script with sudo
sudo /bin/bash -c "echo 'Backup notification sent' > /var/log/backup.log" 