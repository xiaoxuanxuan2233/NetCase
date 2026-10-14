import os
from pathlib import Path

from sqlalchemy import JSON, String, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class Record(Base):
    __tablename__ = "records"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[str] = mapped_column(String(40), index=True)
    target: Mapped[str] = mapped_column(String(2048), index=True)
    payload: Mapped[dict] = mapped_column(JSON)


class Favorite(Base):
    __tablename__ = "favorites"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    target: Mapped[str] = mapped_column(String(2048), unique=True)
    label: Mapped[str] = mapped_column(String(60))


class Draft(Base):
    __tablename__ = "drafts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict] = mapped_column(JSON)


class Preference(Base):
    __tablename__ = "preferences"
    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)


def default_data_path() -> Path:
    override = os.getenv("NETCASE_DATA_DIR")
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        return Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "NetCase"
    return Path(os.getenv("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "netcase"


def make_database(url: str | None = None):
    if url is None:
        directory = default_data_path()
        directory.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{(directory / 'netcase.db').as_posix()}"
    engine = create_engine(url, connect_args={"check_same_thread": False, "timeout": 10})

    @event.listens_for(engine, "connect")
    def configure_connection(connection, _):
        cursor = connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=10000")
        cursor.close()

    return engine, sessionmaker(engine, expire_on_commit=False)
