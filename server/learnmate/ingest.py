"""Reads uploaded material into chapters, chunks and figures. A no-op until the ingest pipeline is built."""

from sqlalchemy.orm import Session, sessionmaker

from learnmate.config import Settings


def ingest(
    session_factory: sessionmaker[Session], settings: Settings, material_id: int
) -> None:
    # Placeholder: the material stays in status "reading".
    return None
