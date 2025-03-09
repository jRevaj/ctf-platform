#!/bin/bash

# Jenkins deployment script for target4
# This script is used by Jenkins to deploy applications to target4's Tomcat server

# Set variables
TOMCAT_HOST="target4"
TOMCAT_PORT="8080"
TOMCAT_USER="admin"
TOMCAT_PASS="tomcat_admin_password"
WAR_FILE="/target3/jenkins/workspace/app/target/app.war"
DEPLOY_PATH="/manager/text/deploy?path=/app&update=true"

# FTP credentials for backup
FTP_HOST="target4"
FTP_USER="anonymous"
FTP_PASS=""  # Anonymous access

# Log start of deployment
echo "Starting deployment to Tomcat at $(date)"

# Check if WAR file exists
if [ ! -f "$WAR_FILE" ]; then
    echo "ERROR: WAR file not found at $WAR_FILE"
    exit 1
fi

# Deploy to Tomcat using curl
echo "Deploying to Tomcat..."
curl -v -u "$TOMCAT_USER:$TOMCAT_PASS" \
    --upload-file "$WAR_FILE" \
    "http://$TOMCAT_HOST:$TOMCAT_PORT$DEPLOY_PATH"

# Create backup via FTP
echo "Creating backup via FTP..."
ftp -n $FTP_HOST << EOF
user $FTP_USER $FTP_PASS
binary
cd /backup
put $WAR_FILE app_backup.war
bye
EOF

# SSH to target4 to restart Tomcat (using key-based authentication)
echo "Restarting Tomcat service..."
ssh -i /target3/jenkins/.ssh/target4_key ctf-user@target4 "sudo service tomcat restart"

echo "Deployment completed at $(date)" 