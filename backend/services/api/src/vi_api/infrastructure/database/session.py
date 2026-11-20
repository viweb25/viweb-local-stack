from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from vi_api.config.settings import Settings

engine = create_async_engine(Settings().database_url, pool_pre_ping=True)
Session = async_sessionmaker(engine, expire_on_commit=False)
