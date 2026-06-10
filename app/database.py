from __future__ import annotations



from functools import lru_cache



from sqlalchemy import create_engine

from sqlalchemy.engine import Engine

from sqlalchemy.orm import Session, sessionmaker



from app.config import get_settings





def _build_database_url() -> str:

    settings = get_settings()

    return (

        f"postgresql://{settings.db_user}:"

        f"{settings.db_password}@"

        f"{settings.db_host}:"

        f"{settings.db_port}/"

        f"{settings.db_name}"

    )





@lru_cache(maxsize=1)

def get_engine() -> Engine:

    return create_engine(_build_database_url(), pool_pre_ping=True)





@lru_cache(maxsize=1)

def get_session_factory() -> sessionmaker[Session]:

    return sessionmaker(

        autocommit=False,

        autoflush=False,

        bind=get_engine(),

    )





def create_session() -> Session:

    return get_session_factory()()

