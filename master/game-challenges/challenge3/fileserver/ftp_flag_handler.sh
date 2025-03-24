#!/bin/bash

# This script is triggered when a file is uploaded to the FTP server
# It checks for specific files and reveals a flag

# Log the upload
echo "$(date): File uploaded to FTP server" >> /var/log/ftp_uploads.log

# Check if the uploaded file is a PHP file
if [ -f /var/ftp/pub/*.php ]; then
    # If a PHP file is uploaded, reveal the flag
    echo "FLAG_PLACEHOLDER_8" > /var/ftp/pub/flag_revealed.txt
    echo "$(date): PHP file detected, flag revealed" >> /var/log/ftp_uploads.log
fi

# This is a simulated vulnerability for the CTF challenge
# In a real challenge, this would be more complex and involve actual code execution