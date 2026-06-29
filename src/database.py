from sqlalchemy import Engine, create_engine as sa_create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker as sa_sessionmaker


class Base(DeclarativeBase):
    pass


def create_engine(database_url: str) -> Engine:
    return sa_create_engine(database_url)


def create_sessionmaker(engine: Engine) -> sa_sessionmaker[Session]:
    return sa_sessionmaker(bind=engine, expire_on_commit=False)
