from rest_framework.throttling import AnonRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """5 attempts per minute per IP on the login endpoint.

    ``get_rate()`` is overridden to read from ``api_settings`` at call time
    instead of from the class-level ``THROTTLE_RATES`` snapshot. This ensures
    the rate is correctly picked up when Django's ``settings`` fixture replaces
    ``REST_FRAMEWORK`` in tests (the class attribute would otherwise remain
    stale after a ``setting_changed`` signal).
    """

    scope = "login"

    def get_rate(self):
        from rest_framework.settings import api_settings
        return api_settings.DEFAULT_THROTTLE_RATES.get(self.scope)
