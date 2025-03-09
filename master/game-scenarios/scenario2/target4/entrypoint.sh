# game-containers/base/entrypoint.sh
#!/bin/bash

# Debug info
echo "Starting entrypoint script" > /tmp/debug.log

# Set password for ctf-user for the challenge
echo "ctf-user:t4rget4_p4ssw0rd" | chpasswd
echo "Set password for ctf-user" >> /tmp/debug.log

# Create a hint file
echo "Admin notes: The Tomcat manager interface has default credentials." > /home/ctf-user/admin_notes.txt
echo "Anonymous FTP access is enabled for backups." >> /home/ctf-user/admin_notes.txt
chmod 644 /home/ctf-user/admin_notes.txt
chown ctf-user:ctf-user /home/ctf-user/admin_notes.txt

# Setup SSH
mkdir -p /home/ctf-user/.ssh
touch /home/ctf-user/.ssh/authorized_keys
echo "SSH directory created" >> /tmp/debug.log

# Set proper permissions
chown -R ctf-user:ctf-user /home/ctf-user/.ssh
chmod 700 /home/ctf-user/.ssh
chmod 600 /home/ctf-user/.ssh/authorized_keys
echo "SSH permissions set" >> /tmp/debug.log

# Setup authorized_keys with target3's public key for lateral movement
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJ9enzNPkqxRTNXNe8LUOPkkHOMehc0ZcYtBDLckInVU ctf-user@target4.local" >> /home/ctf-user/.ssh/authorized_keys

# Generate SSH host keys
ssh-keygen -A
echo "SSH host keys generated" >> /tmp/debug.log

# Set up Tomcat
# Ensure ROOT webapp exists
mkdir -p /var/lib/tomcat9/webapps/ROOT
echo "<html><body><h1>Tomcat Default Page</h1><p>This is the default Tomcat page.</p></body></html>" > /var/lib/tomcat9/webapps/ROOT/index.html
chown -R tomcat:tomcat /var/lib/tomcat9

# Start Tomcat directly from our manual installation
echo "Starting Tomcat..." >> /tmp/debug.log
# If we're using the manual installation (which we are based on our Dockerfile)
if [ -d "/opt/tomcat" ]; then
    echo "Starting Tomcat from manual installation..." >> /tmp/debug.log
    /opt/tomcat/bin/startup.sh
    echo "Tomcat started from /opt/tomcat" >> /tmp/debug.log
# Fallback to other common locations
elif [ -f "/usr/share/tomcat9/startup.sh" ]; then
    echo "Starting Tomcat from /usr/share/tomcat9..." >> /tmp/debug.log
    /usr/share/tomcat9/startup.sh
elif [ -f "/usr/libexec/tomcat9/startup.sh" ]; then
    echo "Starting Tomcat from /usr/libexec/tomcat9..." >> /tmp/debug.log
    /usr/libexec/tomcat9/startup.sh  
else
    echo "Looking for Tomcat startup script..." >> /tmp/debug.log
    TOMCAT_STARTUP=$(find / -name startup.sh 2>/dev/null | head -1)
    if [ -n "$TOMCAT_STARTUP" ]; then
        echo "Found Tomcat startup script at $TOMCAT_STARTUP" >> /tmp/debug.log
        bash "$TOMCAT_STARTUP"
    else
        echo "Could not find Tomcat startup script" >> /tmp/debug.log
    fi
fi
echo "Tomcat started" >> /tmp/debug.log

# Set up FTP server with a simpler configuration
mkdir -p /var/ftp/pub
echo "Welcome to the anonymous FTP server" > /var/ftp/pub/welcome.txt
echo "This server is used for backups" > /var/ftp/pub/README.txt

# Create a backup directory with sensitive information
mkdir -p /backup
echo "Database backup credentials: dbuser/dbpass123" > /backup/db_backup_info.txt
chmod 777 /backup
chmod 666 /backup/db_backup_info.txt

# Fix VSFTPD config
cat > /etc/vsftpd.conf << EOL
# Simple vsftpd configuration that works
listen=YES
anonymous_enable=YES
anon_upload_enable=YES
anon_mkdir_write_enable=YES
anon_other_write_enable=YES
local_enable=YES
write_enable=YES
local_umask=022
dirmessage_enable=YES
use_localtime=YES
xferlog_enable=YES
connect_from_port_20=YES
secure_chroot_dir=/var/run/vsftpd/empty
anon_root=/var/ftp
EOL

mkdir -p /var/run/vsftpd/empty

# Start vsftpd
service vsftpd start || vsftpd /etc/vsftpd.conf &
echo "FTP server started" >> /tmp/debug.log

# Start SSH with debug logging
echo "Starting SSH daemon" >> /tmp/debug.log
/usr/sbin/sshd -D -e

exec "$@"