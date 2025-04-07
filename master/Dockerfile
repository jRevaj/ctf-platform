FROM python:3.12.7

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=core.settings

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Create log directory
RUN mkdir -p /var/log/ctf && chmod 777 /var/log/ctf

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Default command (can be overridden in docker-compose.yaml)
CMD ["sh", "-c", "python manage.py migrate && python manage.py init_admin && python manage.py runserver 0.0.0.0:8000"]