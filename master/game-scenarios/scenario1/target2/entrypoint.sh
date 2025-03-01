# game-containers/base/entrypoint.sh
#!/bin/bash

# Debug info
echo "Starting entrypoint script" > /tmp/debug.log

# Set a password for ctf-user for debugging
echo "ctf-user:password" | chpasswd
echo "Set password for ctf-user" >> /tmp/debug.log

# Setup SSH
mkdir -p /home/ctf-user/.ssh
touch /home/ctf-user/.ssh/authorized_keys
echo "SSH directory created" >> /tmp/debug.log

# Set proper permissions
chown -R ctf-user:ctf-user /home/ctf-user/.ssh
chmod 700 /home/ctf-user/.ssh
chmod 600 /home/ctf-user/.ssh/authorized_keys
echo "SSH permissions set" >> /tmp/debug.log

# Ensure SSH host keys exist
ssh-keygen -A
echo "SSH host keys generated" >> /tmp/debug.log

# Start SSH with debug logging
echo "Starting SSH daemon" >> /tmp/debug.log
/usr/sbin/sshd -D -e

exec "$@"