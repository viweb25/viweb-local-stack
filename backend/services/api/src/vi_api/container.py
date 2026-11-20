from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from redis import Redis

from vi_api.app.catalogue.get_function_templates import GetFunctionTemplates
from vi_api.app.demo_examples.create_demo_example import CreateDemoExample
from vi_api.app.demo_examples.get_demo_example_image import GetDemoExampleImage
from vi_api.app.demo_examples.list_demo_examples import ListDemoExamples
from vi_api.app.health.check_readiness import CheckReadiness
from vi_api.app.identity.sign_in import SignIn
from vi_api.config.settings import Settings
from vi_api.domain.catalogue.repository import CatalogueRepository
from vi_api.domain.demo_examples.repository import DemoExampleRepository
from vi_api.domain.identity.ports import IdentityRepository
from vi_api.infrastructure.cache.catalogue import CachedCatalogueRepository
from vi_api.infrastructure.database.readiness import DatabaseReadinessRepository
from vi_api.infrastructure.database.session import Session, engine
from vi_api.infrastructure.identity.passwords import ScryptPasswordVerifier
from vi_api.infrastructure.repository.catalogue import JsonCatalogueRepository
from vi_api.infrastructure.repository.demo_examples import PostgresDemoExampleRepository
from vi_api.infrastructure.repository.identity import PostgresIdentityRepository
from vi_api.interfaces.http.errors import ApiError, ErrorCode

ROOT = Path(__file__).resolve().parents[4]
CATALOGUE_PATH = ROOT / "packages/schemas/functions/catalogue.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_catalogue_repository() -> CatalogueRepository:
    source = JsonCatalogueRepository(CATALOGUE_PATH)
    url = get_settings().redis_cache_url
    if not url:
        return source
    cache = Redis.from_url(url, socket_connect_timeout=0.2, socket_timeout=0.2)
    version = sha256(CATALOGUE_PATH.read_bytes()).hexdigest()
    return CachedCatalogueRepository(source, cache, f"vi:catalogue:v1:{version}")


def get_function_templates() -> GetFunctionTemplates:
    return GetFunctionTemplates(get_catalogue_repository())


def check_readiness() -> CheckReadiness:
    return CheckReadiness(DatabaseReadinessRepository(engine))


def get_demo_example_repository() -> DemoExampleRepository:
    directory = get_settings().demo_image_dir
    if not directory:
        raise ApiError(404, ErrorCode.DEMO_DISABLED, "Local demo is disabled")
    return PostgresDemoExampleRepository(Session, Path(directory))


DemoRepo = Annotated[DemoExampleRepository, Depends(get_demo_example_repository)]


def get_create_demo_example(repository: DemoRepo) -> CreateDemoExample:
    return CreateDemoExample(repository)


def get_list_demo_examples(repository: DemoRepo) -> ListDemoExamples:
    return ListDemoExamples(repository)


def get_demo_example_image_operation(repository: DemoRepo) -> GetDemoExampleImage:
    return GetDemoExampleImage(repository)


def get_identity_repository() -> IdentityRepository:
    return PostgresIdentityRepository(Session)


def get_sign_in(
    repository: Annotated[IdentityRepository, Depends(get_identity_repository)],
) -> SignIn:
    return SignIn(repository, ScryptPasswordVerifier())
