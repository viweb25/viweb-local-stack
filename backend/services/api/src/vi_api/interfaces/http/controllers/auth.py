from typing import Annotated

from anyio import to_thread
from fastapi import APIRouter, Depends, Header, Request, Response
from pydantic import BaseModel, Field, SecretStr
from sqlalchemy.exc import IntegrityError

from vi_api.app.identity.sign_in import SignIn, token_hash
from vi_api.container import get_sign_in
from vi_api.domain.identity.models import CurrentUser
from vi_api.domain.identity.ports import SignInRateLimited, SignInRejected
from vi_api.infrastructure.identity.passwords import LIMIT, hash_password
from vi_api.infrastructure.identity.provision_owner import provision_owner
from vi_api.interfaces.http.auth_configuration import app_origin, cookie_name
from vi_api.interfaces.http.dependencies.identity import (
    SESSION_COOKIE,
    IdentityRepo,
    SessionToken,
    SettingsDependency,
    get_current_user,
)
from vi_api.interfaces.http.errors import ApiError, ErrorCode
from vi_api.interfaces.http.schemas.errors import ErrorResponse

router = APIRouter(prefix="/api/v1/auth", tags=["Identity"])
SESSION_TTL = 8 * 60 * 60
SignInDependency = Annotated[SignIn, Depends(get_sign_in)]


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+$")
    password: SecretStr = Field(min_length=1, max_length=128)


def same_origin(settings: SettingsDependency, origin: Annotated[str | None, Header()] = None):
    expected = app_origin(settings)
    if origin != expected:
        raise ApiError(403, ErrorCode.INVALID_REQUEST_ORIGIN, "Request origin is not allowed")
    return expected


BrowserOrigin = Annotated[str, Depends(same_origin)]


class SignupRequest(LoginRequest):
    password: SecretStr = Field(min_length=15, max_length=128)
    organisation: str = Field(min_length=1, max_length=200, pattern=r"\S")


@router.post(
    "/signup",
    status_code=204,
    responses={code: {"model": ErrorResponse} for code in (403, 409)},
)
async def signup(credentials: SignupRequest, origin: BrowserOrigin) -> None:
    password_hash = await to_thread.run_sync(
        hash_password, credentials.password.get_secret_value(), limiter=LIMIT
    )
    try:
        await provision_owner(
            credentials.email.lower(), credentials.organisation.strip(), password_hash
        )
    except IntegrityError as exc:
        raise ApiError(
            409, ErrorCode.SIGNUP_CONFLICT, "An account already uses this email"
        ) from exc


@router.post(
    "/login",
    status_code=204,
    responses={code: {"model": ErrorResponse} for code in (401, 403, 429)},
)
async def login(
    request: Request,
    response: Response,
    credentials: LoginRequest,
    sign_in: SignInDependency,
    origin: BrowserOrigin,
    previous_session: SessionToken = None,
) -> None:
    source = request.client.host if request.client else "unknown"
    try:
        token = await sign_in.execute(
            credentials.email, credentials.password.get_secret_value(), source, previous_session
        )
    except SignInRateLimited as exc:
        raise ApiError(
            429, ErrorCode.SIGN_IN_RATE_LIMITED, "Too many attempts. Try again later."
        ) from exc
    except SignInRejected as exc:
        raise ApiError(
            401, ErrorCode.INVALID_CREDENTIALS, "Email or password is incorrect"
        ) from exc
    secure = origin.startswith("https:")
    response.set_cookie(
        cookie_name(SESSION_COOKIE, secure),
        token,
        max_age=SESSION_TTL,
        secure=secure,
        httponly=True,
        samesite="strict",
        path="/",
    )


@router.get("/me", responses={401: {"model": ErrorResponse}})
async def me(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
    return user


@router.post("/logout", status_code=204, responses={403: {"model": ErrorResponse}})
async def logout(
    response: Response,
    repository: IdentityRepo,
    origin: BrowserOrigin,
    token: SessionToken = None,
) -> None:
    if token:
        await repository.revoke_session(token_hash(token))
    secure = origin.startswith("https:")
    response.delete_cookie(
        cookie_name(SESSION_COOKIE, secure), secure=secure, httponly=True, samesite="strict"
    )
