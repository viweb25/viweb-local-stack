from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from vi_api.domain.identity.models import CurrentUser, Membership


class PostgresIdentityRepository:
    def __init__(self, sessions: async_sessionmaker):
        self.sessions = sessions

    async def record_sign_in_attempt(self, bucket: bytes) -> int:
        async with self.sessions.begin() as session:
            count = await session.scalar(
                text("""
                    INSERT INTO identity.sign_in_limits (bucket, attempts)
                    VALUES (:bucket, 1)
                    ON CONFLICT (bucket) DO UPDATE
                    SET attempts = CASE
                            WHEN sign_in_limits.window_started_at <= now() - interval '15 minutes'
                            THEN 1 ELSE LEAST(sign_in_limits.attempts + 1, 31) END,
                        window_started_at = CASE
                            WHEN sign_in_limits.window_started_at <= now() - interval '15 minutes'
                            THEN now() ELSE sign_in_limits.window_started_at END
                    RETURNING attempts
                """),
                {"bucket": bucket},
            )
        return int(count)

    async def get_password_credential(self, email: str) -> tuple[UUID, str] | None:
        async with self.sessions() as session:
            result = await session.execute(
                text("""
                    SELECT user_id, password_hash FROM identity.password_credentials
                    WHERE email = :email
                """),
                {"email": email},
            )
            row = result.one_or_none()
        return (row.user_id, row.password_hash) if row else None

    async def create_session(
        self,
        user_id: UUID,
        token_hash: bytes,
        previous_hash: bytes | None = None,
        *,
        expected_hash: str,
    ) -> bool:
        async with self.sessions.begin() as session:
            result = await session.scalar(
                text("""
                    INSERT INTO identity.sessions (user_id, token_hash, expires_at)
                    SELECT u.id, :token_hash, now() + interval '8 hours'
                    FROM identity.password_credentials AS c
                    JOIN identity.users AS u ON u.id = c.user_id
                    WHERE u.id = :user_id AND c.password_hash = :expected_hash
                      AND u.status = 'active'
                      AND EXISTS (
                        SELECT 1 FROM identity.memberships AS m
                        WHERE m.user_id = u.id AND m.status = 'active'
                      )
                    RETURNING id
                """),
                {"user_id": user_id, "expected_hash": expected_hash, "token_hash": token_hash},
            )
            if result is not None and previous_hash is not None:
                await session.execute(
                    text("""
                        UPDATE identity.sessions SET revoked_at = now()
                        WHERE token_hash = :token_hash AND revoked_at IS NULL
                    """),
                    {"token_hash": previous_hash},
                )
        return result is not None

    async def get_current_user(self, token_hash: bytes) -> CurrentUser | None:
        async with self.sessions() as session:
            result = await session.execute(
                text("""
                    SELECT u.id, u.display_name, u.email, m.org_id, o.name, m.role
                    FROM identity.sessions AS s
                    JOIN identity.users AS u ON u.id = s.user_id
                    LEFT JOIN identity.memberships AS m ON m.user_id = u.id AND m.status = 'active'
                    LEFT JOIN public.organisations AS o ON o.id = m.org_id
                    WHERE s.token_hash = :token_hash
                      AND s.revoked_at IS NULL AND s.expires_at > now() AND u.status = 'active'
                    ORDER BY o.name, m.org_id
                """),
                {"token_hash": token_hash},
            )
            rows = result.mappings().all()
        if not rows:
            return None
        first = rows[0]
        return CurrentUser(
            first["id"],
            first["display_name"],
            first["email"],
            [
                Membership(row["org_id"], row["name"], row["role"])
                for row in rows
                if row["org_id"] is not None
            ],
        )

    async def revoke_session(self, token_hash: bytes) -> None:
        async with self.sessions.begin() as session:
            await session.execute(
                text("""
                    UPDATE identity.sessions SET revoked_at = now()
                    WHERE token_hash = :token_hash AND revoked_at IS NULL
                """),
                {"token_hash": token_hash},
            )
