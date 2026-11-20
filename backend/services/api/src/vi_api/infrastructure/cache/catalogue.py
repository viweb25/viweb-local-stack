from pydantic import TypeAdapter, ValidationError
from redis import Redis, RedisError

from vi_api.domain.catalogue.model import FunctionTemplate
from vi_api.domain.catalogue.repository import CatalogueRepository

TEMPLATES = TypeAdapter(list[FunctionTemplate])


class CachedCatalogueRepository:
    """Cache public catalogue data. Keep the source available if Redis fails."""

    def __init__(self, source: CatalogueRepository, cache: Redis, key: str):
        self.source = source
        self.cache = cache
        self.key = key

    def list_templates(self) -> list[FunctionTemplate]:
        try:
            cached = self.cache.get(self.key)
            if cached is not None:
                return TEMPLATES.validate_json(cached)
        except (RedisError, ValidationError):
            pass

        templates = self.source.list_templates()
        try:
            self.cache.set(self.key, TEMPLATES.dump_json(templates), ex=60)
        except RedisError:
            pass
        return templates
