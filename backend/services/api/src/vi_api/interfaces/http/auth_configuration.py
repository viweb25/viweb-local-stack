from urllib.parse import urlsplit

from vi_api.config.settings import Settings
from vi_api.interfaces.http.errors import ApiError, ErrorCode


def app_origin(settings: Settings) -> str:
    url = urlsplit(settings.app_origin)
    local = url.scheme == "http" and url.hostname in {"127.0.0.1", "localhost", "::1"}
    if (
        not (url.scheme == "https" or local)
        or not url.hostname
        or url.username
        or url.path not in ("", "/")
        or url.query
        or url.fragment
    ):
        raise ApiError(503, ErrorCode.SIGN_IN_UNAVAILABLE, "Sign-in configuration is unavailable")
    return f"{url.scheme}://{url.netloc}"


def cookie_name(name: str, secure: bool) -> str:
    return f"__Host-{name}" if secure else name
