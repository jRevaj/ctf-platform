FROM ubuntu:22.04

# Avoid prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install required packages
RUN apt-get update && apt-get install -y \
    openssh-server \
    vsftpd \
    samba \
    samba-common \
    curl \
    nano \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Set up SSH
RUN mkdir -p /var/run/sshd
RUN echo 'root:fileserver_root_password' | chpasswd
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config

# Create ctf-user
RUN useradd -m -s /bin/bash ctf-user
RUN echo "ctf-user:fileserver_password" | chpasswd
RUN echo "ctf-user ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/ctf-user

# Create the admin user with a custom SSH banner
RUN useradd -m -s /bin/bash admin-user
RUN echo "admin-user:admin123" | chpasswd

# Create flags directory
RUN mkdir -p /flags
RUN chmod 700 /flags

# Create flag files
RUN echo "FLAG_PLACEHOLDER_7" > /flags/hidden_share_flag.txt
RUN echo "FLAG_PLACEHOLDER_8" > /flags/ftp_upload_flag.txt
RUN echo "FLAG_PLACEHOLDER_9" > /flags/ssh_banner_flag.txt

# Configure SSH with custom banner for specific user
COPY ssh_banner.txt /etc/ssh/ssh_banner.txt
RUN echo "Match User admin-user" >> /etc/ssh/sshd_config
RUN echo "    Banner /etc/ssh/ssh_banner.txt" >> /etc/ssh/sshd_config

# Configure FTP for anonymous access with write permissions
COPY vsftpd.conf /etc/vsftpd.conf
RUN mkdir -p /var/ftp/pub
RUN chown -R ftp:ftp /var/ftp
RUN chmod 777 /var/ftp/pub
COPY ftp_flag_handler.sh /var/ftp/ftp_flag_handler.sh
RUN chmod +x /var/ftp/ftp_flag_handler.sh

# Configure Samba with public and hidden shares
COPY smb.conf /etc/samba/smb.conf
RUN mkdir -p /samba/public
RUN mkdir -p /samba/hidden
RUN echo "This is a public share. Nothing interesting here." > /samba/public/README.txt
RUN echo "FLAG_PLACEHOLDER_7" > /samba/hidden/secret_flag.txt
RUN chown -R nobody:nogroup /samba/public
RUN chown -R nobody:nogroup /samba/hidden
RUN chmod -R 777 /samba/public
RUN chmod -R 777 /samba/hidden

# Create samba user
RUN (echo "samba_password"; echo "samba_password") | smbpasswd -a ctf-user

# Copy and set up entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
# Fix line endings just in case
RUN sed -i 's/\r$//' /entrypoint.sh

# Expose ports
EXPOSE 22 21 445

# Start services
CMD ["/bin/bash", "/entrypoint.sh"] 