from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Disable global throttling in dev so tests run without a cache backend dependency
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # noqa: F405
# Disable login-specific throttle in dev (LoginView checks for this key)
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"].pop("login", None)  # noqa: F405

# Show emails in console during development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405

MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]  # noqa: F405

INTERNAL_IPS = ["127.0.0.1", "::1"]

CORS_ALLOW_ALL_ORIGINS = True

# Disable password validation in dev
AUTH_PASSWORD_VALIDATORS = []

# Easier logging in dev
LOGGING["loggers"]["apps"]["level"] = "DEBUG"  # noqa: F405
