# game-containers/base/entrypoint.sh
#!/bin/bash

# Debug info
echo "Starting entrypoint script" > /tmp/debug.log

# Set password for ctf-user for the challenge
echo "ctf-user:s3cret_t4rget2" | chpasswd
echo "Set password for ctf-user" >> /tmp/debug.log

# Create a hint file about target3
echo "Admin notes: The backup server at 172.1.0.4 uses key-based authentication only." > /home/ctf-user/admin_notes.txt
echo "The key is hidden somewhere in this server." >> /home/ctf-user/admin_notes.txt
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

# Ensure SSH host keys exist
ssh-keygen -A
echo "SSH host keys generated" >> /tmp/debug.log

# Create the hidden key with proper permissions
mkdir -p /var/log/.backup

# Use a fixed key instead of generating a new one each time
cat > /var/log/.backup/backup_key << 'EOL'
-----BEGIN OPENSSH PRIVATE KEY-----
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
967iICYze/2oSwAAAAlwYzFAUmV2YWo=
-----END OPENSSH PRIVATE KEY-----
EOL

cat > /var/log/.backup/backup_key.pub << 'EOL'
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC0AaqlDNwdJoHaotpClEezid+xBy2D7KZncVz2aSwwbExZHsUHG1rAptYkwL6bo91k7ntEcKsHrO9bysndMEfPinokNt6T9KeaSEScszIETAP39GQFutPX9quBOBwBgjSslj7detwR3rYp05gywtV8W9JUcDK8rZvFQ5T7vlpOSvYa4KgsHrvyrea4TMoVAP+6a/CCaaYLE3z7NErQfqY/x/1PTO8/w1g/qQDM8PmFnfDXlABm762/jMaC1f2MLtNq+DktD/6Y5a4szm1dnnAQMW/6x0nXtQIrwYuCVw5dCy9vhbgk3O9tXI8hgzblm5uaodR3wPl83voGakHdzmzDhIiXZsOB1Wf+1fkoFA5dpQhgJeRQi+uV9XGHz8ipPcqZeCKh8rcUDPJZVFLuB9Gmna2/kpS3P+pId8BabLcfI+iIAvADYgd/C3Ea/kV3/E+aj8I44rmhXvLvmIhWUVVq3fVshm5HVMF9ZRrPe5T0rZNqVXn6nDWqqcE9M+S4n11VoBOmdcX8hq1/URQig0Nt+UOOWJGDe4N9lE3UIwR08MkmWg346WK06+DgeM1bdNrV5xkUTHKaHH4HrwYkOrt2CQTge/plcmu2GB2ttjiWtM+sFbyt0IAtHgkkQ/4zNk5G7taXiGlwNpVyaflAtCu89JextB9h21j6d3cY9kiNHQ== pc1@Revaj
EOL

chmod 644 /var/log/.backup/backup_key  # Make it readable by everyone
chown root:root /var/log/.backup/backup_key
cp /var/log/.backup/backup_key.pub /home/ctf-user/.ssh/id_rsa.pub
chmod 644 /home/ctf-user/.ssh/id_rsa.pub
chown ctf-user:ctf-user /home/ctf-user/.ssh/id_rsa.pub

# Save the public key to a location that can be copied to target3
cp /var/log/.backup/backup_key.pub /home/ctf-user/target3_key.pub
chmod 644 /home/ctf-user/target3_key.pub
chown ctf-user:ctf-user /home/ctf-user/target3_key.pub

# Start SSH with debug logging
echo "Starting SSH daemon" >> /tmp/debug.log
/usr/sbin/sshd -D -e

exec "$@"