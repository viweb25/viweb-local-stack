from typing import Protocol
from uuid import UUID

from vi_api.domain.identity.models import CurrentUser


class SignInRejected(Exception):
    pass


class SignInRateLimited(Exception):
    pass


class PasswordVerifier(Protocol):
    async def verify(self, password: str, stored_hash: str | None) -> bool: ...


class IdentityRepository(Protocol):
    async def record_sign_in_attempt(self, bucket: bytes) -> int: ...

    async def get_password_credential(self, email: str) -> tuple[UUID, str] | None: ...

    async def create_session(
        self,
        user_id: UUID,
        token_hash: bytes,
        previous_hash: bytes | None = None,
        *,
        expected_hash: str,
    ) -> bool: ...

    async def get_current_user(self, token_hash: bytes) -> CurrentUser | None: ...

    async def revoke_session(self, token_hash: bytes) -> None: ...
