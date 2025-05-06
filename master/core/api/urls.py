from django.urls import path

from core.api.views import health_check

api_urls = [
    path('health/', health_check, name='health_check'),
]
