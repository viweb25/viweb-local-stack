from redis import ConnectionError
from vi_api.domain.catalogue.model import FunctionTemplate
from vi_api.infrastructure.cache.catalogue import CachedCatalogueRepository


class Catalogue:
    def __init__(self):
        self.reads = 0

    def list_templates(self):
        self.reads += 1
        return [FunctionTemplate("test", "Test", "planned: test", {})]


class Cache:
    value = None

    def get(self, key):
        assert key == "catalogue"
        return self.value

    def set(self, key, value, *, ex):
        assert (key, ex) == ("catalogue", 60)
        self.value = value


def test_public_catalogue_reads_source_on_cache_miss_and_uses_cache_on_hit():
    source = Catalogue()
    repository = CachedCatalogueRepository(source, Cache(), "catalogue")
    assert repository.list_templates() == repository.list_templates()
    assert source.reads == 1


def test_public_catalogue_remains_available_when_redis_is_down():
    class UnavailableCache:
        def get(self, key):
            raise ConnectionError("Redis unavailable")

        def set(self, key, value, *, ex):
            raise ConnectionError("Redis unavailable")

    repository = CachedCatalogueRepository(Catalogue(), UnavailableCache(), "catalogue")
    assert repository.list_templates()[0].id == "test"
