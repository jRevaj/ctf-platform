# game-containers/base/entrypoint.sh
#!/bin/bash

# Debug info
echo "Starting entrypoint script" > /tmp/debug.log

# Set password for ctf-user for the challenge
echo "ctf-user:secr3t_t4rget3" | chpasswd
echo "Set password for ctf-user" >> /tmp/debug.log

# Create a hint file about target4
echo "Admin notes: The Tomcat server at target4 has default credentials." > /home/ctf-user/admin_notes.txt
echo "We need to deploy our application there using Jenkins." >> /home/ctf-user/admin_notes.txt
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

# Setup authorized_keys with target2's public key for lateral movement
echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC0AaqlDNwdJoHaotpClEezid+xBy2D7KZncVz2aSwwbExZHsUHG1rAptYkwL6bo91k7ntEcKsHrO9bysndMEfPinokNt6T9KeaSEScszIETAP39GQFutPX9quBOBwBgjSslj7detwR3rYp05gywtV8W9JUcDK8rZvFQ5T7vlpOSvYa4KgsHrvyrea4TMoVAP+6a/CCaaYLE3z7NErQfqY/x/1PTO8/w1g/qQDM8PmFnfDXlABm762/jMaC1f2MLtNq+DktD/6Y5a4szm1dnnAQMW/6x0nXtQIrwYuCVw5dCy9vhbgk3O9tXI8hgzblm5uaodR3wPl83voGakHdzmzDhIiXZsOB1Wf+1fkoFA5dpQhgJeRQi+uV9XGHz8ipPcqZeCKh8rcUDPJZVFLuB9Gmna2/kpS3P+pId8BabLcfI+iIAvADYgd/C3Ea/kV3/E+aj8I44rmhXvLvmIhWUVVq3fVshm5HVMF9ZRrPe5T0rZNqVXn6nDWqqcE9M+S4n11VoBOmdcX8hq1/URQig0Nt+UOOWJGDe4N9lE3UIwR08MkmWg346WK06+DgeM1bdNrV5xkUTHKaHH4HrwYkOrt2CQTge/plcmu2GB2ttjiWtM+sFbyt0IAtHgkkQ/4zNk5G7taXiGlwNpVyaflAtCu89JextB9h21j6d3cY9kiNHQ== pc1@Revaj" >> /home/ctf-user/.ssh/authorized_keys

# Generate SSH host keys
ssh-keygen -A
echo "SSH host keys generated" >> /tmp/debug.log

# Create SSH key for target4 lateral movement
mkdir -p /target3/jenkins/.ssh
cat > /target3/jenkins/.ssh/target4_key << 'EOL'
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACDfXp8zT5KsUUzVzXvC1Dj5JBzjHoXNGXGLQQy3JCJ1VAAAAKD0EEHw9BBB
8AAAAAtzc2gtZWQyNTUxOQAAACDfXp8zT5KsUUzVzXvC1Dj5JBzjHoXNGXGLQQy3JCJ1VA
AAAEAuGxVQjBBZXDzXzrZLQ9VZidf3Qzz+xIVbGhQDtQdDJN9enzNPkqxRTNXNe8LUOPkk
HOMehc0ZcYtBDLckInVUAAAAGGN0Zi11c2VyQHRhcmdldDQubG9jYWwBAgMEBQYH
-----END OPENSSH PRIVATE KEY-----
EOL

cat > /target3/jenkins/.ssh/target4_key.pub << 'EOL'
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJ9enzNPkqxRTNXNe8LUOPkkHOMehc0ZcYtBDLckInVU ctf-user@target4.local
EOL

chmod 600 /target3/jenkins/.ssh/target4_key
chmod 644 /target3/jenkins/.ssh/target4_key.pub
chown -R ctf-user:ctf-user /target3/jenkins/.ssh

# Set up Jenkins
mkdir -p /target3/jenkins/workspace
chmod +x /target3/jenkins/deploy.sh

# Set up environment variables with API key (intentionally exposed)
export JENKINS_API_KEY="jenkins_api_key_12345"
export TARGET4_DEPLOY_TOKEN="deploy_token_abcdef"
echo "export JENKINS_API_KEY=\"jenkins_api_key_12345\"" >> /home/ctf-user/.bashrc
echo "export TARGET4_DEPLOY_TOKEN=\"deploy_token_abcdef\"" >> /home/ctf-user/.bashrc

# Start Memcached with vulnerable configuration
service memcached start
echo "Memcached started with vulnerable configuration" >> /tmp/debug.log

# Store sensitive data in Memcached for the challenge
sleep 2
echo -e "set jenkins_admin_password 0 0 16\njenkins_password\r" | nc localhost 11211
echo -e "set target4_ftp_password 0 0 14\nftppass123456\r" | nc localhost 11211
echo "Sensitive data stored in Memcached" >> /tmp/debug.log

# Start Jenkins with default admin user
cd /target3/jenkins
java -jar jenkins.war --httpPort=8080 --prefix=/jenkins &
echo "Jenkins started" >> /tmp/debug.log

# Create flag file in entrypoint.sh
# FLAG_PLACEHOLDER_7

# Start SSH with debug logging
echo "Starting SSH daemon" >> /tmp/debug.log
/usr/sbin/sshd -D -e

exec "$@"