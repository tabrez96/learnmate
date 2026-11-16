"""Delete all material and results, keeping the family settings and the AI usage history."""

import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import delete
from sqlalchemy.orm import Session

from learnmate.api.deps import AppSettings, DbSession
from learnmate.models import Base, Family
from learnmate.passwords import verify_password

KEPT_TABLES = frozenset({"family", "llm_usage"})

router = APIRouter(prefix="/api/v1")


class DeleteDataIn(BaseModel):
    password: str


def delete_all_data(db: Session, data_dir: Path) -> None:
    # Reverse dependency order keeps foreign keys happy; the chunk_fts_ad
    # trigger clears the search index. Rows go first so a failed file removal
    # never leaves rows pointing at missing files.
    for table in reversed(Base.metadata.sorted_tables):
        if table.name not in KEPT_TABLES:
            db.execute(delete(table))
    db.commit()
    files_dir = data_dir / "files"
    try:
        shutil.rmtree(files_dir)
    except FileNotFoundError:
        pass
    files_dir.mkdir(parents=True, exist_ok=True)


@router.delete("/data", status_code=204)
def delete_data(body: DeleteDataIn, db: DbSession, settings: AppSettings) -> Response:
    family = db.get(Family, 1)
    if family is None or not verify_password(body.password, family.fallback_hash):
        raise HTTPException(403, "Wrong password")
    delete_all_data(db, settings.data_dir)
    return Response(status_code=204)
