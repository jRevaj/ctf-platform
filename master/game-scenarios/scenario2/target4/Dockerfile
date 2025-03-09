FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Update and install packages
RUN apt-get update && apt-get install -y \
    openssh-server \
    openssh-client \
    bash \
    curl \
    wget \
    default-jdk \
    sudo \
    vsftpd \
    net-tools \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Tomcat manually to ensure full control over installation
RUN mkdir -p /opt/tomcat && \
    cd /opt && \
    wget https://dlcdn.apache.org/tomcat/tomcat-9/v9.0.100/bin/apache-tomcat-9.0.100.tar.gz && \
    tar -xf apache-tomcat-9.0.100.tar.gz -C /opt/tomcat --strip-components=1 && \
    rm apache-tomcat-9.0.100.tar.gz && \
    chmod +x /opt/tomcat/bin/*.sh

# Create symbolic links to make Tomcat easier to find
RUN ln -s /opt/tomcat/bin /usr/share/tomcat9 && \
    ln -s /opt/tomcat/conf /etc/tomcat9 && \
    ln -s /opt/tomcat/logs /var/log/tomcat9 && \
    mkdir -p /var/lib/tomcat9/webapps && \
    ln -s /opt/tomcat/webapps /var/lib/tomcat9/webapps

# Create ctf-user
RUN useradd -m -s /bin/bash ctf-user

# Create tomcat user
RUN groupadd -r tomcat && \
    useradd -r -g tomcat -d /opt/tomcat -s /bin/false tomcat && \
    chown -R tomcat:tomcat /opt/tomcat

# Configure SSH
RUN mkdir -p /var/run/sshd

# Copy SSH config
COPY sshd_config /etc/ssh/sshd_config
RUN chmod 644 /etc/ssh/sshd_config

# Create .ssh directory with proper permissions
RUN mkdir -p /home/ctf-user/.ssh && \
    touch /home/ctf-user/.ssh/authorized_keys && \
    chown -R ctf-user:ctf-user /home/ctf-user/.ssh && \
    chmod 700 /home/ctf-user/.ssh && \
    chmod 600 /home/ctf-user/.ssh/authorized_keys

# Copy Tomcat configuration
COPY tomcat-users.xml /etc/tomcat9/tomcat-users.xml
RUN chmod 640 /etc/tomcat9/tomcat-users.xml && \
    chown -R tomcat:tomcat /etc/tomcat9

# Set up Tomcat manager with flag
RUN mkdir -p /target4/tomcat/manager
COPY flag.txt /target4/tomcat/manager/flag.txt
RUN chown -R tomcat:tomcat /target4/tomcat

# Set up VSFTPD with clean config
COPY vsftpd.conf /etc/vsftpd.conf
RUN mkdir -p /var/ftp/pub /backup
RUN chmod 777 /var/ftp/pub /backup
RUN echo "Welcome to the FTP server" > /var/ftp/pub/welcome.txt

# Add sudo permissions for tomcat restart
RUN echo "ctf-user ALL=(ALL) NOPASSWD: /usr/sbin/service tomcat9 restart" > /etc/sudoers.d/ctf-user && \
    chmod 440 /etc/sudoers.d/ctf-user

# Copy and set up entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Fix line endings just in case
RUN sed -i 's/\r$//' /entrypoint.sh

EXPOSE 22 8080 21

CMD ["/bin/bash", "/entrypoint.sh"]