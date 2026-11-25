"""Nightly backups of the database, the uploaded files and the PIN key, and restoring one."""

import datetime as dt
import fcntl
import os
import shutil
import sqlite3
from pathlib import Path
from zoneinfo import ZoneInfo

from learnmate.files import FILES_DIRNAME, files_dir
from learnmate.sessions.pins import KEY_FILE

DB_NAME = "learnmate.db"  # same file name as Settings.database_path
PIN_KEY_NAME = KEY_FILE
NAME_FORMAT = "%Y%m%d-%H%M%S"
PREFIX = "learnmate-"  # backup folder name: learnmate-<UTC time>
PARTIAL_SUFFIX = ".partial"
LOCK_NAME = ".lock"
# Moved aside on restore; a stale WAL next to a restored database would corrupt it.
LIVE_NAMES = (DB_NAME, DB_NAME + "-wal", DB_NAME + "-shm", FILES_DIRNAME, PIN_KEY_NAME)


def backup_name(at: dt.datetime) -> str:
    return PREFIX + at.strftime(NAME_FORMAT)


def parse_backup_name(name: str) -> dt.datetime | None:
    """Time of a finished backup folder, None for anything else (partials, unrelated files)."""
    if not name.startswith(PREFIX):
        return None
    try:
        return dt.datetime.strptime(name[len(PREFIX) :], NAME_FORMAT)
    except ValueError:
        return None


def list_backups(backup_dir: Path) -> list[tuple[dt.datetime, Path]]:
    """Finished backups, oldest first. Missing backup_dir -> []."""
    if not backup_dir.is_dir():
        return []
    found = []
    for child in backup_dir.iterdir():
        at = parse_backup_name(child.name)
        if at is not None and child.is_dir():
            found.append((at, child))
    return sorted(found)


def copy_database(src: Path, dst: Path) -> None:
    """Consistent copy of a live SQLite database with the online backup API."""
    source = sqlite3.connect(src)
    try:
        target = sqlite3.connect(dst)
        try:
            source.backup(target)  # default pages=-1: one step, from one read snapshot
        finally:
            target.close()
    finally:
        source.close()


def copy_files(src: Path, dst: Path) -> int:
    """Copy every file under src to dst, keeping the layout. Files deleted mid-copy are skipped. Returns files copied."""
    dst.mkdir(parents=True, exist_ok=True)
    copied = 0
    if not src.is_dir():
        return copied

    def fail(error: OSError) -> None:
        # A folder deleted mid-copy is fine; any other unreadable folder would leave files out.
        if not isinstance(error, FileNotFoundError):
            raise error

    for root, _dirs, names in os.walk(src, onerror=fail):
        target_dir = dst / Path(root).relative_to(src)
        target_dir.mkdir(parents=True, exist_ok=True)
        for name in names:
            try:
                shutil.copy2(Path(root) / name, target_dir / name)
            except FileNotFoundError:
                continue
            copied += 1
    return copied


def run_backup(
    data_dir: Path, backup_dir: Path, now: dt.datetime, keep_days: int
) -> Path:
    """Make one backup, then remove old ones. Returns the new backup folder."""
    if not (data_dir / DB_NAME).is_file():
        raise FileNotFoundError(data_dir / DB_NAME)
    backup_dir.mkdir(parents=True, exist_ok=True)
    # One run at a time across processes (the nightly loop and the `now` command), so a run
    # never deletes another run's .partial folder. The lock is released when the file closes.
    with (backup_dir / LOCK_NAME).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return _run_locked(data_dir, backup_dir, now, keep_days)


def _run_locked(
    data_dir: Path, backup_dir: Path, now: dt.datetime, keep_days: int
) -> Path:
    for child in backup_dir.iterdir():
        if child.is_dir() and child.name.endswith(PARTIAL_SUFFIX):
            shutil.rmtree(child)
    final = backup_dir / backup_name(now)
    if final.exists():
        raise FileExistsError(final)
    work = backup_dir / (final.name + PARTIAL_SUFFIX)
    work.mkdir()
    try:
        copy_database(data_dir / DB_NAME, work / DB_NAME)
        copy_files(files_dir(data_dir), work / FILES_DIRNAME)
        if (data_dir / PIN_KEY_NAME).exists():
            shutil.copy2(data_dir / PIN_KEY_NAME, work)
        work.rename(final)
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise
    prune(backup_dir, now, keep_days)
    return final


def prune(backup_dir: Path, now: dt.datetime, keep_days: int) -> list[Path]:
    """Delete finished backups older than keep_days. Returns what was deleted."""
    limit = dt.timedelta(days=keep_days)
    removed = []
    for at, path in list_backups(backup_dir):
        if now - at > limit:
            shutil.rmtree(path)
            removed.append(path)
    return removed


def restore(backup: Path, data_dir: Path, now: dt.datetime) -> Path:
    """Replace the live data with a backup. The server must be stopped. Returns where the replaced data was moved."""
    if not (backup / DB_NAME).is_file():
        raise ValueError(f"{backup} is not a finished backup")
    aside = data_dir / ("replaced-" + now.strftime(NAME_FORMAT))
    aside.mkdir(parents=True)
    for name in LIVE_NAMES:
        if (data_dir / name).exists():
            shutil.move(data_dir / name, aside / name)
    shutil.copy2(backup / DB_NAME, data_dir / DB_NAME)
    copy_files(backup / FILES_DIRNAME, files_dir(data_dir))
    if (backup / PIN_KEY_NAME).exists():
        shutil.copy2(backup / PIN_KEY_NAME, data_dir / PIN_KEY_NAME)
    return aside


def next_run_at(now: dt.datetime, hour: int, timezone: str) -> dt.datetime:
    """Next time it is <hour>:00 in timezone, strictly after now. Naive UTC in, naive UTC out."""
    zone = ZoneInfo(timezone)
    local = now.replace(tzinfo=dt.UTC).astimezone(zone)
    candidate = local.replace(hour=hour, minute=0, second=0, microsecond=0)
    if candidate <= local:
        candidate = (candidate.replace(tzinfo=None) + dt.timedelta(days=1)).replace(
            tzinfo=zone
        )
    return candidate.astimezone(dt.UTC).replace(tzinfo=None)


def is_overdue(backup_dir: Path, now: dt.datetime) -> bool:
    """True when there is no finished backup from the last 24 hours (the computer was off at backup time)."""
    backups = list_backups(backup_dir)
    return not backups or now - backups[-1][0] > dt.timedelta(hours=24)
