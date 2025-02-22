FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    openssh-server \
    && rm -rf /var/lib/apt/lists/*

# Create ctf-user
RUN useradd -m -s /bin/bash ctf-user

# Configure SSH
RUN mkdir /var/run/sshd
RUN echo 'PermitRootLogin no' >> /etc/ssh/sshd_config
RUN echo 'PasswordAuthentication no' >> /etc/ssh/sshd_config

# Create flags directory with proper permissions
RUN mkdir -p /flags && \
    chown ctf-user:ctf-user /flags && \
    chmod 755 /flags

EXPOSE 22

CMD ["/usr/sbin/sshd", "-D"]