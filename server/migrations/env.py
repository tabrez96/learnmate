from alembic import context

from learnmate import models
from learnmate.config import get_settings
from learnmate.db import create_db_engine

config = context.config
url = config.get_main_option("sqlalchemy.url")
if not url:
    get_settings().data_dir.mkdir(parents=True, exist_ok=True)
    url = get_settings().database_url

target_metadata = models.Base.metadata


def include_object(obj, name, type_, reflected, compare_to) -> bool:
    # FTS5 virtual and shadow tables are not in the models.
    return not (type_ == "table" and name.startswith("chunk_fts"))


def run_migrations_online() -> None:
    engine = create_db_engine(url)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    raise RuntimeError("offline migrations are not supported")
run_migrations_online()
