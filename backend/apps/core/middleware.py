import logging
import time

logger = logging.getLogger("apps.core")


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = round((time.monotonic() - start) * 1000, 2)

        logger.info(
            "%(method)s %(path)s %(status)s %(duration)sms",
            {
                "method": request.method,
                "path": request.get_full_path(),
                "status": response.status_code,
                "duration": duration_ms,
            },
        )
        return response
