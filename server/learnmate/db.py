"""Database engine and sessions. SQLite in WAL mode, one file under the data directory."""

from sqlalchemy import Engine, create_engine, event, inspect
from sqlalchemy.orm import Session, sessionmaker

from learnmate.clock import Clock, SystemClock


def create_db_engine(url: str) -> Engine:
    engine = create_engine(url)
    event.listen(engine, "connect", _set_sqlite_pragmas)
    return engine


def _set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


def make_session_factory(
    engine: Engine, clock: Clock | None = None
) -> sessionmaker[Session]:
    factory = sessionmaker(
        engine, expire_on_commit=False, info={"clock": clock or SystemClock()}
    )
    event.listen(factory, "before_flush", _fill_clock_columns)
    return factory


def _fill_clock_columns(session: Session, _flush_context, _instances) -> None:
    # Columns marked info={"clock": True} take the injected time on insert
    # unless the caller set them; server_default covers raw SQL.
    now = session.info["clock"].now()
    for obj in session.new:
        for attr in inspect(obj).mapper.column_attrs:
            if attr.columns[0].info.get("clock") and getattr(obj, attr.key) is None:
                setattr(obj, attr.key, now)
