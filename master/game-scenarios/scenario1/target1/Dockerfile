FROM alpine:latest

RUN apk update && apk add --no-cache \
    openssh-server \
    mysql \
    mysql-client \
    apache2 \
    bash \
    && rm -rf /var/cache/apk/*

# Create ctf-user
RUN adduser -D -h /home/ctf-user -s /bin/bash ctf-user

# Configure SSH
RUN mkdir /var/run/sshd
RUN ssh-keygen -A  # Generate host keys
RUN echo 'PermitRootLogin no' >> /etc/ssh/sshd_config
RUN echo 'PasswordAuthentication no' >> /etc/ssh/sshd_config

# Create flags directory with proper permissions
RUN mkdir -p /flags && \
    chown ctf-user:ctf-user /flags && \
    chmod 755 /flags

# Copy and set up entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 22 80 3306

CMD ["/usr/sbin/sshd", "-D"]