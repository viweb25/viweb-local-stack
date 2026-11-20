# Jobs and messaging

Owner: Siva. Compose starts a Celery worker consuming the `platform` queue from
Redis. `make docker-ping` submits the existing infrastructure smoke task. Check
`docker compose logs worker` for execution. There is no training or customer job
endpoint and no durable job table yet. A Celery task ID is not a durable job record.

JSON-only messages, bounded task times, one reserved task per worker slot and broker
startup retry are configured. Redis AOF and no-eviction policy are development
safeguards, not an exactly-once delivery guarantee. Do not enable late acknowledgement
on a side-effecting task until idempotency is implemented. Reloading API code does
not restart a worker; use `docker compose restart worker` after task changes.

The durable job/outbox design, retry policy and GPU queue split are in
`docs/architecture/DISTRIBUTED_SYSTEM.md`. RabbitMQ is an alternative future broker;
this foundation intentionally operates one messaging system. Redis is not a source
of truth for training status. Never enqueue raw images, secrets or model weights.
