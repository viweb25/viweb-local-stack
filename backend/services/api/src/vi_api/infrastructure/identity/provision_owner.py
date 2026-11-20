from uuid import UUID

from sqlalchemy import text

from vi_api.infrastructure.database.session import Session


async def provision_owner(email: str, organisation: str | UUID, password_hash: str):
    async with Session.begin() as session:
        if isinstance(organisation, UUID):
            org_id = await session.scalar(
                text("SELECT id FROM public.organisations WHERE id = :id"), {"id": organisation}
            )
            if org_id is None:
                raise ValueError("Organisation not found.")
        else:
            org_id = await session.scalar(
                text("""
                    INSERT INTO public.organisations (id, name)
                    VALUES (gen_random_uuid(), :name)
                    RETURNING id
                """),
                {"name": organisation},
            )
        user_id = await session.scalar(
            text("INSERT INTO identity.users (email) VALUES (:email) RETURNING id"),
            {"email": email},
        )
        await session.execute(
            text("""
                INSERT INTO identity.password_credentials (user_id, email, password_hash)
                VALUES (:user_id, :email, :password_hash)
            """),
            {"user_id": user_id, "email": email, "password_hash": password_hash},
        )
        await session.execute(
            text("""
                INSERT INTO identity.memberships (org_id, user_id, role)
                VALUES (:org_id, :user_id, 'owner')
            """),
            {"org_id": org_id, "user_id": user_id},
        )
    return user_id, org_id
