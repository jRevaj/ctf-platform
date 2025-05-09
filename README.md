# CTF Platform

## Overview

This project is a CTF platform that allows you to create and manage CTF challenges.

## Management Commands

This directory contains management commands for the CTF platform.

### `setup_environment`

This command can set up either a single-container environment or a multi-container challenge.

### Usage

```bash
python manage.py setup_environment template_name
```

or inside docker

```bash
docker compose exec master python manage.py setup_environment template_name
```


### Requirements

The command requires the following environment variables to be set:

- `TEST_BLUE_SSH_PUBLIC_KEY`: SSH public key for blue team users
- `TEST_RED_SSH_PUBLIC_KEY`: SSH public key for red team users

### Output

The command will output connection information for all created containers, including SSH connection strings.

### `test_matchmaking`

This command tests the matchmaking system by simulating game rounds. It supports both random and Swiss-system matchmaking.

### Usage

```bash
python manage.py test_matchmaking --system random --rounds 1 --session test --template test-challenge-multi --teams 4
```

or inside docker

```bash
docker compose exec master python manage.py test-matchmaking --system random --rounds 1 --session test --template test-challenge-multi --teams 4
```

### Requirements

The command requires the following environment variables to be set:

- `TEST_SSH_PUBLIC_KEY_{x}`: SSH public keys for users (currently 8 are set for 8 users = 4 teams)

### Output

The command will output logs for whole game creation and teams rotation based on selected round number.

## Other Commands

- `clean_test_env`: Cleans up test environments
- `sync_templates`: Synchronizes challenge templates
- `init_admin`: Initializes admin user
