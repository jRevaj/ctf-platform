#!/bin/sh
set -e

# Only try to fix docker group if docker.sock exists
if [ -S /var/run/docker.sock ]; then
    DOCKER_GID=$(stat -c '%g' /var/run/docker.sock)
    if ! getent group docker >/dev/null; then
        # Only try to add group if not root
        if [ "$DOCKER_GID" -ne 0 ]; then
            addgroup --gid "$DOCKER_GID" docker || true
        fi
    fi
    usermod -aG docker appuser || true
fi

# Exec the command as appuser on production
# exec gosu appuser "$@" 

# Use root when testing locally
exec "$@"