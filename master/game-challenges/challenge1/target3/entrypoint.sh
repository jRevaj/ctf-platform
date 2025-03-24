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

# Use the same public key that matches container 2's private key
cat > /home/ctf-user/.ssh/authorized_keys << 'EOL'
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC0AaqlDNwdJoHaotpClEezid+xBy2D7KZncVz2aSwwbExZHsUHG1rAptYkwL6bo91k7ntEcKsHrO9bysndMEfPinokNt6T9KeaSEScszIETAP39GQFutPX9quBOBwBgjSslj7detwR3rYp05gywtV8W9JUcDK8rZvFQ5T7vlpOSvYa4KgsHrvyrea4TMoVAP+6a/CCaaYLE3z7NErQfqY/x/1PTO8/w1g/qQDM8PmFnfDXlABm762/jMaC1f2MLtNq+DktD/6Y5a4szm1dnnAQMW/6x0nXtQIrwYuCVw5dCy9vhbgk3O9tXI8hgzblm5uaodR3wPl83voGakHdzmzDhIiXZsOB1Wf+1fkoFA5dpQhgJeRQi+uV9XGHz8ipPcqZeCKh8rcUDPJZVFLuB9Gmna2/kpS3P+pId8BabLcfI+iIAvADYgd/C3Ea/kV3/E+aj8I44rmhXvLvmIhWUVVq3fVshm5HVMF9ZRrPe5T0rZNqVXn6nDWqqcE9M+S4n11VoBOmdcX8hq1/URQig0Nt+UOOWJGDe4N9lE3UIwR08MkmWg346WK06+DgeM1bdNrV5xkUTHKaHH4HrwYkOrt2CQTge/plcmu2GB2ttjiWtM+sFbyt0IAtHgkkQ/4zNk5G7taXiGlwNpVyaflAtCu89JextB9h21j6d3cY9kiNHQ== pc1@Revaj
EOL

echo "Added matching public key to authorized_keys" >> /tmp/debug.log

# Set proper permissions
chown -R ctf-user:ctf-user /home/ctf-user/.ssh
chmod 700 /home/ctf-user/.ssh
chmod 600 /home/ctf-user/.ssh/authorized_keys
echo "SSH permissions set" >> /tmp/debug.log

# Create the final flag file
echo "Congratulations! You've found the final flag: FLAG_PLACEHOLDER_4" > /home/ctf-user/flag.txt
chmod 644 /home/ctf-user/flag.txt
chown ctf-user:ctf-user /home/ctf-user/flag.txt
echo "Created flag file" >> /tmp/debug.log

# Ensure SSH host keys exist
ssh-keygen -A
echo "SSH host keys generated" >> /tmp/debug.log

# Start SSH with debug logging
echo "Starting SSH daemon" >> /tmp/debug.log
/usr/sbin/sshd -D -e

exec "$@"