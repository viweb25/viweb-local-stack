from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request

from vi_api.app.identity.sign_in import token_hash
from vi_api.config.settings import Settings
from vi_api.container import get_identity_repository, get_settings
from vi_api.domain.identity.models import CurrentUser, Membership
from vi_api.domain.identity.ports import IdentityRepository
from vi_api.interfaces.http.auth_configuration import app_origin, cookie_name
from vi_api.interfaces.http.errors import ApiError, ErrorCode

SESSION_COOKIE = "viweb_session"
IdentityRepo = Annotated[IdentityRepository, Depends(get_identity_repository)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]


def get_session_token(request: Request, settings: SettingsDependency) -> str | None:
    secure = app_origin(settings).startswith("https:")
    token = request.cookies.get(cookie_name(SESSION_COOKIE, secure))
    return token if token and len(token) <= 128 else None


SessionToken = Annotated[str | None, Depends(get_session_token)]


async def get_current_user(repository: IdentityRepo, token: SessionToken = None) -> CurrentUser:
    if token:
        user = await repository.get_current_user(token_hash(token))
        if user is not None:
            return user
    raise ApiError(401, ErrorCode.AUTHENTICATION_REQUIRED, "Sign in to continue")


def require_organisation_access(
    org_id: UUID, user: Annotated[CurrentUser, Depends(get_current_user)]
) -> Membership:
    membership = next((item for item in user.organisations if item.org_id == org_id), None)
    if membership is None:
        raise ApiError(403, ErrorCode.ORGANISATION_ACCESS_DENIED, "Organisation access denied")
    return membership
