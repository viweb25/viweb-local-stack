from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from vi_api.app.identity.sign_in import SignIn
from vi_api.bootstrap import app
from vi_api.config.settings import Settings
from vi_api.container import get_identity_repository, get_settings, get_sign_in
from vi_api.domain.identity.models import CurrentUser, Membership
from vi_api.infrastructure.identity.passwords import ScryptPasswordVerifier, hash_password
from vi_api.interfaces.http.dependencies.identity import require_organisation_access
from vi_api.interfaces.http.errors import ApiError


@pytest.mark.parametrize("origin", ["http://127.0.0.1:3000", "https://inspection.example.com"])
def test_password_login_session_logout_and_rate_limit(origin):
    organisation = Membership(uuid4(), "Example", "owner")
    user = CurrentUser(uuid4(), "Test User", None, [organisation])
    password = "test password for the suite"
    hashed = hash_password(password)
    sessions = set()
    attempts = {}

    class Repository:
        async def record_sign_in_attempt(self, bucket):
            attempts[bucket] = attempts.get(bucket, 0) + 1
            return attempts[bucket]

        async def get_password_credential(self, email):
            return (user.id, hashed) if email == "owner@example.test" else None

        async def create_session(self, user_id, token_hash, previous_hash=None, *, expected_hash):
            assert user_id == user.id and expected_hash == hashed
            sessions.discard(previous_hash)
            sessions.add(token_hash)
            return True

        async def get_current_user(self, token_hash):
            return user if token_hash in sessions else None

        async def revoke_session(self, token_hash):
            sessions.discard(token_hash)

    repo = Repository()
    app.dependency_overrides.update(
        {
            get_settings: lambda: Settings(app_origin=origin),
            get_identity_repository: lambda: repo,
            get_sign_in: lambda: SignIn(repo, ScryptPasswordVerifier()),
        }
    )
    try:
        client = TestClient(app, base_url=origin)
        headers = {"Origin": origin}
        login = "/api/v1/auth/login"
        payload = {"email": "OWNER@example.test", "password": password}
        assert client.get("/api/v1/auth/me").status_code == 401
        assert client.post(login, json=payload).status_code == 403
        bad = client.post(login, json={**payload, "password": "wrong"}, headers=headers)
        unknown = client.post(
            login, json={**payload, "email": "nobody@example.test"}, headers=headers
        )
        assert bad.status_code == unknown.status_code == 401
        assert bad.json() == unknown.json()
        response = client.post(login, json=payload, headers=headers)
        assert response.status_code == 204
        cookie = response.headers["set-cookie"]
        assert "HttpOnly" in cookie and "SameSite=strict" in cookie
        if origin.startswith("https:"):
            assert cookie.startswith("__Host-viweb_session=") and "Secure" in cookie
        assert client.get("/api/v1/auth/me").json()["id"] == str(user.id)
        assert require_organisation_access(organisation.org_id, user) == organisation
        with pytest.raises(ApiError) as error:
            require_organisation_access(uuid4(), user)
        assert error.value.status_code == 403
        assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
        assert client.get("/api/v1/auth/me").status_code == 401
        assert not sessions
        for bucket in attempts:
            attempts[bucket] = 8
        assert client.post(login, json=payload, headers=headers).status_code == 429
    finally:
        app.dependency_overrides.clear()


def test_signup_requires_correct_code_and_origin(monkeypatch):
    from vi_api.interfaces.http.controllers import auth

    origin = "http://127.0.0.1:3000"
    code = "private-signup-code-for-test"
    calls = []

    async def provision(email, organisation, password_hash):
        assert await ScryptPasswordVerifier().verify("test signup password", password_hash)
        calls.append((email, organisation))

    monkeypatch.setattr(auth, "provision_owner", provision)
    monkeypatch.setitem(
        app.dependency_overrides,
        get_settings,
        lambda: Settings(app_origin=origin, signup_code=code),
    )
    with TestClient(app, base_url=origin) as client:
        url = "/api/v1/auth/signup"
        payload = {
            "email": "OWNER@example.test",
            "password": "test signup password",
            "organisation": " Example Factory ",
            "code": code,
        }
        assert client.post(url, json=payload).status_code == 403
        headers = {"Origin": origin}
        assert (
            client.post(url, headers=headers, json={**payload, "code": "wrong"}).status_code == 403
        )
        assert client.post(url, headers=headers, json=payload).status_code == 204
        assert client.get("/api/v1/auth/me").status_code == 401
    assert calls == [("owner@example.test", "Example Factory")]
