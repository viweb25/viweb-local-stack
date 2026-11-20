# Database ownership and workflow

Alembic is the only migration authority. `migrations/versions/` records ordered changes;
`functions/` contains migration-owned SQL; `tests/` runs opt-in PostgreSQL integration checks.
Do not edit an applied migration or replay functions manually as a deployment mechanism.
Create a new revision for every change, including replacement of a function body.

From the repository root:

```bash
docker compose run --rm migrate
docker compose exec api alembic -c database/alembic.ini current
make tools
make docker-test
```

If pgAdmin is installed on your computer, register the Docker database with:

- Host: `localhost`
- Port: `15432` (or POSTGRES_PORT from `.env`)
- Maintenance database: POSTGRES_DB from `.env` (default `viws`)
- Username: POSTGRES_USER from `.env` (default `vi`)
- Password: POSTGRES_PASSWORD from `.env` (default `vi_local`)

Local pgAdmin does not need `make tools`. PostgreSQL must be running in Docker.

Alternatively, use the optional containerised pgAdmin below.
Open pgAdmin at http://127.0.0.1:15050. Use the development credentials in `.env`.
Register server `local`, host `postgres`, port `5432`, database `viws`, user/password
matching POSTGRES_USER/POSTGRES_PASSWORD. The container uses the service hostname;
a host SQL client uses `127.0.0.1:15432`. SQLAlchemy URLs are not pgAdmin server names.

Inspect `public.organisations`, `public.alembic_version` and the `platform` schema.
The ten `platform.usp_*()` routines are PostgreSQL **functions**, callable with SELECT:

```sql
SELECT platform.usp_schema_version();
SELECT platform.usp_database_name();
SELECT platform.usp_database_size_bytes();
SELECT platform.usp_server_version();
SELECT platform.usp_connection_count();
SELECT platform.usp_active_connection_count();
SELECT platform.usp_transaction_read_only();
SELECT platform.usp_is_replica();
SELECT * FROM platform.usp_table_sizes();
SELECT platform.usp_migration_table_exists();
```

These are developer diagnostics, not customer CRUD or training procedures. They run
with invoker permissions; PUBLIC has no access. Local development uses the migration
owner. Future deployment must separate the owner/migration role from the runtime role
and grant only the required table/function privileges. Connection statistics reflect
what the caller may see. Do not expose diagnostic functions through customer routes.

PostgreSQL procedures use CALL and may manage transactions in certain contexts;
functions use SELECT and execute within the caller's transaction. Prefer application
services for business policy; use SQL routines for measured database-intensive work.
Parameterise every value. Never trust a caller-supplied organisation ID as identity.

No seeds are needed for this public catalogue. Customer tables, membership, jobs and
outbox are future migrations after the identity/role design. Do not create dummy
tenants or passwords automatically. Validate foreign keys, organisation scope,
uniqueness, concurrency and permission failures with each new migration.

For a destructive migration experiment use a disposable database, not a shared local
volume. Take backups before migrations on persistent environments. Downgrades are a
local recovery aid, not a substitute for a tested production restoration strategy.

To inspect the complete SQL without applying it:

```bash
docker compose run --rm migrate alembic -c database/alembic.ini upgrade head --sql
```

Use this output for review. Alembic remains the deployment authority; do not maintain
a second hand-edited schema.sql with a different version history.

## Identity in pgAdmin

Open the **Query Tool** for `viws`. Alembic applies
[0004_identity.sql](migrations/sql/0004_identity.sql) and
[0005_password_sign_in.sql](migrations/sql/0005_password_sign_in.sql) during backend
startup. Both files show the PostgreSQL DDL statement by statement.

```sql
SELECT version_num FROM public.alembic_version;

SELECT u.id AS user_id, c.email, o.name AS organisation, m.role, m.status
FROM identity.password_credentials AS c
JOIN identity.users AS u ON u.id = c.user_id
JOIN identity.memberships AS m ON m.user_id = u.id
JOIN public.organisations AS o ON o.id = m.org_id
ORDER BY o.name, c.email;
```

Create an owner using the CLI in the [sign-in guide](../docs/guides/SIGN_IN.md).
It prompts for the password and writes its salted hash inside the account transaction.
Periodic database maintenance can delete expired sessions and old sign-in limit buckets.

```sql
DELETE FROM identity.sessions WHERE expires_at <= now();
DELETE FROM identity.sign_in_limits WHERE window_started_at < now() - interval '1 day';
```
