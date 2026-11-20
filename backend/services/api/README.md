# Business API

Owner: Siva. The HTTP backend remains Python/FastAPI. Its structure follows
controller -> application operation -> domain repository contract -> infrastructure.
Docker: `make up`. Host: `make api`, after dependencies and migrations are ready.

```text
src/vi_api/
  bootstrap.py                         FastAPI startup and router registration
  container.py                         Dependency composition
  interfaces/http/
    controllers/catalogue.py           CatalogueController
    controllers/health.py              Health probes
    errors.py                          HTTP exception mapping
    schemas/catalogue.py               HTTP response model
  app/
    operation.py                       Sync/async use-case contracts
    catalogue/get_function_templates.py GetFunctionTemplates.execute()
  domain/catalogue/
    model.py                           Framework-independent FunctionTemplate
    repository.py                      CatalogueRepository protocol
  infrastructure/
    repository/catalogue.py            JsonCatalogueRepository
    database/session.py                SQLAlchemy engine/session factory
    database/models/                   ORM persistence models
  config/settings.py                   Environment settings
```

## Working request

`GET /api/v1/function-templates` calls `CatalogueController.templates`, which receives a
request-scoped operation from `container.get_function_templates`. It calls
`GetFunctionTemplates.execute()`. The operation depends only on the domain repository
protocol. The JSON implementation reads/validates public static catalogue data and
returns domain objects. The HTTP response schema serialises them to the existing wire
contract. This endpoint does not query PostgreSQL; it does not access customer data.

The controller owns HTTP status and serialization. The operation owns the use case and
future transaction boundary. The domain owns business models/rules and repository
contracts. Infrastructure owns storage, SQL, messaging and external integrations.
The composition root is allowed to import implementations and wire dependencies.

Unlike the TypeScript EventEmitter example, operations return values or raise exceptions.
There are no shared SUCCESS/ERROR listeners. This keeps responses associated with the
request that executed the operation and avoids accumulating event handlers.
`Operation[Result]` and `AsyncOperation[Result]` provide synchronous/asynchronous
`execute()` contracts without mutable output state. Database readiness follows the
same pattern: HealthController -> CheckReadiness -> ReadinessRepository ->
DatabaseReadinessRepository. The SQL and timeout handling stay in infrastructure.

## Adding a feature

1. Define the domain model and repository protocol under `domain/<feature>/`.
2. Implement one operation per use case under `app/<feature>/` (get/create/update).
3. Implement storage under `infrastructure/repository/`; parameterise all SQL values.
4. Register dependency factories in `container.py`. Use request-scoped dependencies.
5. Add HTTP schemas/controllers under `interfaces/http/`; register the router in bootstrap.
6. Add operation, repository and HTTP tests; regenerate/check OpenAPI with consumers.

Before customer resources, implement verified identity, membership and roles. Pass
verified tenant context into operations and require it in every tenant repository query.
Never trust a request-supplied organisation ID alone. Add cross-tenant rejection tests.
Customer repositories do not commit independently; the operation owns the unit of work.
Do not put GPU execution in the business API. Durable customer jobs and training remain
future work. HTTP routes remain under `/api/v1` (health probes are separate).

Alembic imports ORM metadata from `vi_api.infrastructure.database.models`. Docker and
host commands launch `vi_api.bootstrap:app` with `services/api/src` on PYTHONPATH.
The frontend's service calls and public endpoint URL are unchanged.
