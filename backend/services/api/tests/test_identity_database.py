import asyncio
import os
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from vi_api.app.identity.sign_in import token_hash
from vi_api.infrastructure.repository.identity import PostgresIdentityRepository

URL = os.getenv("DATABASE_TEST_URL")
pytestmark = pytest.mark.skipif(not URL, reason="Set DATABASE_TEST_URL to a migrated test database")


def test_identity_repository_resolves_only_active_memberships_and_revokes_session():
    async def check():
        engine = create_async_engine(URL)
        try:
            async with engine.connect() as connection:
                transaction = await connection.begin()
                try:
                    org, other_org, user = uuid4(), uuid4(), uuid4()
                    await connection.execute(
                        text("INSERT INTO public.organisations (id, name) VALUES (:id, :name)"),
                        [{"id": org, "name": "Example"}, {"id": other_org, "name": "Other"}],
                    )
                    await connection.execute(
                        text("INSERT INTO identity.users (id) VALUES (:user)"), {"user": user}
                    )
                    email = f"{user}@example.test"
                    await connection.execute(
                        text("""
                            INSERT INTO identity.password_credentials
                                (user_id, email, password_hash)
                            VALUES (:user, :email, 'test-hash')
                        """),
                        {"email": email, "user": user},
                    )
                    await connection.execute(
                        text("""
                            INSERT INTO identity.memberships (org_id, user_id, role, status)
                            VALUES (:org, :user, 'operator', :status)
                        """),
                        [
                            {"org": org, "user": user, "status": "active"},
                            {"org": other_org, "user": user, "status": "revoked"},
                        ],
                    )
                    repo = PostgresIdentityRepository(
                        async_sessionmaker(connection, join_transaction_mode="create_savepoint")
                    )
                    hashed = token_hash(str(uuid4()))
                    assert await repo.record_sign_in_attempt(hashed) == 1
                    assert await repo.record_sign_in_attempt(hashed) == 2
                    assert await repo.get_password_credential(email) == (user, "test-hash")
                    assert not await repo.create_session(user, hashed, expected_hash="wrong")
                    assert await repo.create_session(user, hashed, expected_hash="test-hash")
                    current = await repo.get_current_user(hashed)
                    assert current is not None and current.id == user
                    assert [item.org_id for item in current.organisations] == [org]
                    rotated = token_hash(str(uuid4()))
                    assert await repo.create_session(
                        user, rotated, previous_hash=hashed, expected_hash="test-hash"
                    )
                    assert await repo.get_current_user(hashed) is None
                    assert await repo.get_current_user(rotated) is not None
                    await repo.revoke_session(rotated)
                    assert await repo.get_current_user(rotated) is None
                finally:
                    await transaction.rollback()
        finally:
            await engine.dispose()

    asyncio.run(check())
