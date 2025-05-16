# Platform for custom Red vs Blue team CTF competition

This platform is implementation of my diploma thesis. You can find the implementation in the state when the thesis was submitted in the `submitted` branch.

## Usage of this platform

For using this platform you need to have [Docker](https://docs.docker.com/get-docker/) installed. Make sure you have environment variables set based on the `.env.example` file.

### Running the platform

First clone the repository:

```bash
# master branch
git clone https://github.com/sk-ctf/ctf-platform.git
# or submitted branch
git clone -b submitted https://github.com/sk-ctf/ctf-platform.git
```

Then in the root directory of the repository run the platform using:

```bash
docker compose up
```

### Production mode

For production mode edit the `entrypoint.sh` based on your server environment to ensure that the app is not running as root user and that the app-user has all necessary permissions. Then add SSL certificates to the `certs` directory and edit the `nginx.prod.conf` if needed. After that you can run the platform using:

```bash
docker compose -f docker-compose.prod.yaml up
```

## Default credentials

In development mode the app is initialized with admin account and default users. You can find credentials for default users in [test-users.txt](master/test-users.txt).

Default Django admin credentials are:

- username: `admin`
- password: `admin`

### Production mode

In production mode the app is only initialized with admin account. Credentials for the admin account are the same as in development mode.

## Useful links

- [Django](https://www.djangoproject.com/)
- [Docker SDK for Python](https://docker-py.readthedocs.io/en/stable/#)
- [Celery](https://docs.celeryq.dev/en/latest/index.html#)
- [Bootstrap](https://getbootstrap.com/)
