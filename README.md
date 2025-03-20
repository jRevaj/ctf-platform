# CTF Platform

## Overview

This project is a CTF platform that allows you to create and manage CTF scenarios.

## Management Commands

This directory contains management commands for the CTF platform.

### `setup_environment`

This command can set up either a single-container environment or a multi-container scenario.

### Usage

```bash
python manage.py setup_environment template_name
```

### Requirements

The command requires the following environment variables to be set:

- `TEST_BLUE_SSH_PUBLIC_KEY`: SSH public key for blue team users
- `TEST_RED_SSH_PUBLIC_KEY`: SSH public key for red team users

### Output

The command will output connection information for all created containers, including SSH connection strings.

## Other Commands

Usage of these commands is the same as in `setup_environment` command.

- `clean_test_env`: Cleans up test environments
- `sync_templates`: Synchronizes scenario templates
- `init_admin`: Initializes admin user
