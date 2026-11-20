from hashlib import sha256
from secrets import token_urlsafe

from vi_api.domain.identity.ports import (
    IdentityRepository,
    PasswordVerifier,
    SignInRateLimited,
    SignInRejected,
)


def token_hash(token: str) -> bytes:
    return sha256(token.encode()).digest()


class SignIn:
    def __init__(self, repository: IdentityRepository, passwords: PasswordVerifier):
        self.repository = repository
        self.passwords = passwords

    async def execute(
        self, email: str, password: str, source: str, previous_session: str | None
    ) -> str:
        email = email.strip().lower()
        if await self.repository.record_sign_in_attempt(token_hash(f"source:{source}")) > 30:
            raise SignInRateLimited
        if await self.repository.record_sign_in_attempt(token_hash(f"email:{email}")) > 8:
            raise SignInRateLimited
        credential = await self.repository.get_password_credential(email)
        stored_hash = credential[1] if credential else None
        if not await self.passwords.verify(password, stored_hash) or credential is None:
            raise SignInRejected
        token = token_urlsafe(32)
        previous_hash = token_hash(previous_session) if previous_session else None
        if not await self.repository.create_session(
            credential[0], token_hash(token), previous_hash, expected_hash=credential[1]
        ):
            raise SignInRejected
        return token
