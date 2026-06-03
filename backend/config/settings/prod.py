from .base import *  # noqa: F401, F403

import sentry_sdk
from django.core.exceptions import ImproperlyConfigured
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
import environ

env = environ.Env()

DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

# Bloqueia inicialização com SECRET_KEY padrão em produção
_SECRET_KEY_DEFAULT = "change-me-in-production-use-a-long-random-string"
if SECRET_KEY == _SECRET_KEY_DEFAULT:  # noqa: F405
    raise ImproperlyConfigured(
        "SECRET_KEY está com o valor padrão. "
        "Gere uma chave segura: python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\""
    )

# Security headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"

# Renderers — no BrowsableAPI in production
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
]

# Sentry
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
    )

# Static files served by nginx / CDN
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
