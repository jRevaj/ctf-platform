FROM ubuntu:22.04

# Avoid prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install required packages
RUN apt-get update && apt-get install -y \
    openssh-server \
    curl \
    wget \
    git \
    openjdk-11-jdk \
    gnupg \
    lsb-release \
    apt-transport-https \
    ca-certificates \
    software-properties-common \
    nginx \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Set up SSH
RUN mkdir -p /var/run/sshd
RUN echo 'root:devserver_root_password' | chpasswd
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config

# Create ctf-user
RUN useradd -m -s /bin/bash ctf-user
RUN echo "ctf-user:devserver_password" | chpasswd
RUN echo "ctf-user ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/ctf-user

# Create flags directory
RUN mkdir -p /flags
RUN chmod 700 /flags

# Create flag files
RUN echo "FLAG_PLACEHOLDER_13" > /flags/jenkins_build_flag.txt
RUN echo "FLAG_PLACEHOLDER_14" > /flags/gitlab_issue_flag.txt
RUN echo "FLAG_PLACEHOLDER_15" > /flags/environment_var_flag.txt

# Install Jenkins
RUN wget -q -O - https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key | gpg --dearmor -o /usr/share/keyrings/jenkins-keyring.gpg
RUN echo "deb [signed-by=/usr/share/keyrings/jenkins-keyring.gpg] https://pkg.jenkins.io/debian-stable binary/" > /etc/apt/sources.list.d/jenkins.list
RUN apt-get update && apt-get install -y jenkins && rm -rf /var/lib/apt/lists/*

# Configure Jenkins
COPY jenkins_config.xml /var/lib/jenkins/config.xml
COPY jenkins_init.groovy.d/ /var/lib/jenkins/init.groovy.d/
RUN mkdir -p /var/lib/jenkins/jobs/build-project
COPY jenkins_job_config.xml /var/lib/jenkins/jobs/build-project/config.xml
RUN chown -R jenkins:jenkins /var/lib/jenkins

# Install GitLab CE
RUN curl -sS https://packages.gitlab.com/install/repositories/gitlab/gitlab-ce/script.deb.sh | bash
# Pin to a specific version and add retry logic
RUN apt-get update && \
    apt-get install -y apt-transport-https && \
    echo "gitlab-ce gitlab-ce/gitlab-rails/initial_root_password password temporary_password" | debconf-set-selections && \
    for i in {1..3}; do \
        apt-get install -y gitlab-ce=15.11.13-ce.0 && break || echo "Retry attempt $i"; \
        sleep 10; \
    done && \
    rm -rf /var/lib/apt/lists/*

# Configure GitLab
COPY gitlab.rb /etc/gitlab/gitlab.rb
RUN mkdir -p /etc/gitlab/ssl
RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/gitlab/ssl/gitlab.key -out /etc/gitlab/ssl/gitlab.crt \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=gitlab.local"

# Set up vulnerable template
COPY vulnerable_template.rb /opt/gitlab/embedded/service/gitlab-rails/lib/gitlab/template/

# Create a git repository with credentials leak
RUN mkdir -p /home/ctf-user/project
WORKDIR /home/ctf-user/project
RUN git init
COPY project_files/ /home/ctf-user/project/
RUN git config --global user.email "developer@example.com" && \
    git config --global user.name "Developer" && \
    git add . && \
    git commit -m "Initial commit with credentials"
RUN chown -R ctf-user:ctf-user /home/ctf-user/project

# Copy and set up entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
# Fix line endings just in case
RUN sed -i 's/\r$//' /entrypoint.sh

# Expose ports
EXPOSE 22 8080 80

# Start services
CMD ["/bin/bash", "/entrypoint.sh"] 