# VI WebSync database migrations

This repository owns Alembic, SQL functions and schema integration tests.
Revision history 0001 through 0005 is preserved. Set DATABASE_URL to the
migration connection string. The migration runner has no business API dependency.

```bash
docker build -t vi-websync/db:staging .
```

The business backend Compose stack runs this image as its one-shot migration
job. PostgreSQL itself runs on the backend host. Review explicit migrations
and keep schema compatibility with the API and worker for staged releases.
