# game-containers/test-challenge-base/entrypoint.sh
#!/bin/bash

# Nastavenie SSH
mkdir -p /home/ctf-user/.ssh
touch /home/ctf-user/.ssh/authorized_keys
chown -R ctf-user:ctf-user /home/ctf-user/.ssh
chmod 700 /home/ctf-user/.ssh
chmod 600 /home/ctf-user/.ssh/authorized_keys

# Spustenie SSH služby
service ssh start

exec "$@"