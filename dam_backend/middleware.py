from django.conf import settings


class LocalProxyMiddleware:
    """Trust forwarding metadata only from the loopback Caddy upstream connection.

    Upstream servers must bind to loopback. Local processes are in the trust
    boundary; this middleware cannot authenticate another local process.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        local_proxy = settings.SECURE_DEMO and request.META.get("REMOTE_ADDR") in {"127.0.0.1", "::1"}
        if local_proxy:
            if request.META.get("HTTP_X_FORWARDED_PROTO") == "https":
                request.META["wsgi.url_scheme"] = "https"
        else:
            request.META.pop("HTTP_X_FORWARDED_FOR", None)
        request.META.pop("HTTP_X_FORWARDED_PROTO", None)
        response = self.get_response(request)
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response
