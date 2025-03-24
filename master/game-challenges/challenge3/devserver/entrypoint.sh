#!/bin/bash

# Start SSH service
service ssh start
echo "SSH service started"

# Start Jenkins
service jenkins start
echo "Jenkins service started"

# Configure GitLab
echo "Configuring GitLab..."
gitlab-ctl reconfigure
echo "GitLab configured"

# Create a hidden issue with a flag
echo "Creating hidden GitLab issue with flag..."
sleep 30 # Wait for GitLab to be ready
gitlab-rails runner "
  # Create a project
  project = Project.new(
    name: 'Internal Project',
    path: 'internal-project',
    namespace: Namespace.first,
    visibility_level: Gitlab::VisibilityLevel::PRIVATE
  )
  project.save!
  
  # Create an issue with the flag
  issue = Issues::CreateService.new(
    container: project,
    current_user: User.first,
    params: {
      title: 'Security Vulnerability',
      description: 'Critical security issue found in the application. FLAG_PLACEHOLDER_14',
      confidential: true
    }
  ).execute
"
echo "GitLab issue created"

# Keep container running
echo "All services started. Container is now running..."
tail -f /dev/null 