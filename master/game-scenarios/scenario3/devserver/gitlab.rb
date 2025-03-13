## GitLab configuration for CTF challenge

# External URL
external_url 'http://gitlab.local'

# Disable HTTPS
nginx['redirect_http_to_https'] = false
nginx['ssl_certificate'] = "/etc/gitlab/ssl/gitlab.crt"
nginx['ssl_certificate_key'] = "/etc/gitlab/ssl/gitlab.key"

# Disable email
gitlab_rails['gitlab_email_enabled'] = false

# Set initial root password
gitlab_rails['initial_root_password'] = 'password123'

# Disable sign-up restrictions
gitlab_rails['gitlab_default_can_create_group'] = true
gitlab_rails['gitlab_username_changing_enabled'] = true

# Disable rate limits for CTF challenge
gitlab_rails['rack_attack_git_basic_auth'] = { 'enabled' => false }

# Enable server-side template injection vulnerability (simulated)
gitlab_rails['env'] = {
  'GITLAB_VULNERABLE_TEMPLATES' => 'true',
  'FLAG_ENV_VAR' => 'FLAG_PLACEHOLDER_15'
}

# Reduce memory usage for Docker environment
puma['worker_processes'] = 2
sidekiq['concurrency'] = 5
postgresql['shared_buffers'] = "256MB"
prometheus_monitoring['enable'] = false
gitlab_rails['monitoring_whitelist'] = ['0.0.0.0/0'] 