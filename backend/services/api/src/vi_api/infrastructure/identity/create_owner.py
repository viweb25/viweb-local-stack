"""Provision an owner from a trusted administrator's terminal."""

import argparse
import asyncio
import re
from getpass import getpass
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from vi_api.infrastructure.database.session import engine
from vi_api.infrastructure.identity.passwords import hash_password
from vi_api.infrastructure.identity.provision_owner import provision_owner


async def create_owner(email: str, organisation: str | UUID, password_hash: str) -> None:
    try:
        user_id, org_id = await provision_owner(email, organisation, password_hash)
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    except IntegrityError:
        raise SystemExit(
            "Owner could not be created. An account may already use that email."
        ) from None
    finally:
        await engine.dispose()
    print(f"Owner created. User ID: {user_id}. Organisation ID: {org_id}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    company = parser.add_mutually_exclusive_group(required=True)
    company.add_argument("--organisation")
    company.add_argument("--org-id", type=UUID)
    args = parser.parse_args()
    email = args.email.strip().lower()
    if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+", email):
        parser.error("Enter a valid email address.")
    if args.organisation is not None and not 1 <= len(args.organisation.strip()) <= 200:
        parser.error("Organisation names must contain 1 to 200 characters.")
    password = getpass("New password (at least 15 characters): ")
    if not 15 <= len(password) <= 128:
        parser.error("Use 15 to 128 characters.")
    if password != getpass("Confirm password: "):
        parser.error("Passwords do not match.")
    asyncio.run(
        create_owner(email, args.org_id or args.organisation.strip(), hash_password(password))
    )


if __name__ == "__main__":
    main()
