import asyncio
import datetime as dt
import fcntl
import sqlite3
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from learnmate.backup import job, service
from learnmate.backup.__main__ import main
from learnmate.backup.job import backup_loop
from learnmate.backup.service import (
    copy_database,
    copy_files,
    is_overdue,
    list_backups,
    next_run_at,
    prune,
    restore,
    run_backup,
)
from learnmate.clock import FakeClock
from learnmate.config import Settings, get_settings
from learnmate.main import create_app

NOW = dt.datetime(2026, 1, 5, 3, 0)
HEADERS = {"Authorization": "Bearer test-device-token"}


def _make_backup_dir(root: Path, at: dt.datetime, suffix: str = "") -> Path:
    folder = root / (service.backup_name(at) + suffix)
    folder.mkdir(parents=True)
    return folder


def _subject_names(client: TestClient) -> list[str]:
    return [s["name"] for s in client.get("/api/v1/subjects").json()]


def _write_file(settings: Settings, relative: str, data: bytes) -> Path:
    path = settings.data_dir / "files" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def test_backup_is_consistent_while_server_writes(tmp_path: Path) -> None:
    src = tmp_path / "live.db"
    pad = b"x" * 1024
    setup = sqlite3.connect(src)
    setup.execute("PRAGMA journal_mode=WAL")
    setup.execute("CREATE TABLE t (batch INTEGER, n INTEGER, pad BLOB)")
    setup.executemany("INSERT INTO t VALUES (0, 0, ?)", [(pad,)] * 5000)
    setup.commit()
    setup.close()

    stop = threading.Event()
    last = [0]

    def writer() -> None:
        conn = sqlite3.connect(src, timeout=5, isolation_level=None)
        i = 0
        while not stop.is_set():
            i += 1
            conn.execute("BEGIN")
            conn.execute("INSERT INTO t VALUES (?, 1, ?)", (i, pad))
            conn.execute("INSERT INTO t VALUES (?, 2, ?)", (i, pad))
            conn.execute("COMMIT")
            last[0] = i
        conn.close()

    thread = threading.Thread(target=writer)
    thread.start()
    copies = [tmp_path / f"copy{n}.db" for n in range(5)]
    try:
        for copy in copies:
            copy_database(src, copy)
    finally:
        stop.set()
        thread.join()

    assert last[0] > 1
    for copy in copies:
        conn = sqlite3.connect(copy)
        assert conn.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        torn = conn.execute(
            "SELECT batch FROM t WHERE batch > 0 GROUP BY batch HAVING COUNT(*) != 2"
        ).fetchall()
        conn.close()
        assert torn == []


def test_run_backup_copies_database_files_and_pin_key(
    client: TestClient, settings: Settings, tmp_path: Path
) -> None:
    assert client.post("/api/v1/subjects", json={"name": "Science"}).status_code == 201
    pdf = _write_file(settings, "7/01.pdf", b"%PDF-1.4\nhello")
    (settings.data_dir / "pin.key").write_bytes(b"secret-key")

    path = run_backup(settings.data_dir, tmp_path / "backups", NOW, 14)

    assert path.name == "learnmate-20260105-030000"
    conn = sqlite3.connect(path / "learnmate.db")
    assert ("Science",) in conn.execute("SELECT name FROM subject").fetchall()
    conn.close()
    assert (path / "files" / "7" / "01.pdf").read_bytes() == pdf.read_bytes()
    assert (path / "pin.key").read_bytes() == b"secret-key"


def test_run_backup_without_database_raises_and_leaves_nothing(
    tmp_path: Path,
) -> None:
    data = tmp_path / "data"
    data.mkdir()
    backups = tmp_path / "backups"
    with pytest.raises(FileNotFoundError):
        run_backup(data, backups, NOW, 14)
    assert not backups.exists() or list(backups.iterdir()) == []


def test_failed_backup_removes_partial_and_keeps_old_backups(
    app: FastAPI,
    settings: Settings,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backups = tmp_path / "backups"
    old = _make_backup_dir(backups, NOW - dt.timedelta(days=20))

    def boom(src: Path, dst: Path) -> int:
        raise OSError("disk full")

    monkeypatch.setattr(service, "copy_files", boom)
    with pytest.raises(OSError):
        run_backup(settings.data_dir, backups, NOW, 14)

    assert [p.name for p in backups.iterdir() if p.name.endswith(".partial")] == []
    assert old.exists()


def test_leftover_partial_is_removed_by_next_run(
    app: FastAPI, settings: Settings, tmp_path: Path
) -> None:
    backups = tmp_path / "backups"
    partial = _make_backup_dir(backups, dt.datetime(2026, 1, 4, 3, 0), ".partial")

    path = run_backup(settings.data_dir, backups, NOW, 14)

    assert not partial.exists()
    assert path.is_dir()


def test_copy_files_skips_file_deleted_mid_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = tmp_path / "src"
    for name in ("a.txt", "b.txt", "sub/c.txt"):
        (src / name).parent.mkdir(parents=True, exist_ok=True)
        (src / name).write_text(name)
    real = service.shutil.copy2

    def flaky(source, target, *args, **kwargs):
        if Path(source).name == "b.txt":
            raise FileNotFoundError(source)
        return real(source, target, *args, **kwargs)

    monkeypatch.setattr(service.shutil, "copy2", flaky)
    assert copy_files(src, tmp_path / "dst") == 2
    assert (tmp_path / "dst" / "sub" / "c.txt").read_text() == "sub/c.txt"
    assert not (tmp_path / "dst" / "b.txt").exists()


def test_copy_files_without_source_makes_empty_folder(tmp_path: Path) -> None:
    assert copy_files(tmp_path / "missing", tmp_path / "dst") == 0
    assert list((tmp_path / "dst").iterdir()) == []


def test_copy_files_raises_when_a_folder_cannot_be_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = tmp_path / "src"
    src.mkdir()

    def walk(top, onerror=None, **kwargs):
        onerror(PermissionError("denied"))
        return iter(())

    monkeypatch.setattr(service.os, "walk", walk)
    with pytest.raises(PermissionError):
        copy_files(src, tmp_path / "dst")


def test_copy_files_ignores_folder_deleted_mid_walk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = tmp_path / "src"
    src.mkdir()

    def walk(top, onerror=None, **kwargs):
        onerror(FileNotFoundError("gone"))
        return iter(())

    monkeypatch.setattr(service.os, "walk", walk)
    assert copy_files(src, tmp_path / "dst") == 0


def test_run_backup_waits_for_another_run_and_keeps_its_partial(
    app: FastAPI, settings: Settings, tmp_path: Path
) -> None:
    backups = tmp_path / "backups"
    backups.mkdir()
    other_run_partial = backups / "learnmate-20260105-020000.partial"
    other_run_partial.mkdir()
    results: list[Path] = []
    with (backups / service.LOCK_NAME).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)  # another run is in progress
        worker = threading.Thread(
            target=lambda: results.append(
                run_backup(settings.data_dir, backups, NOW, 14)
            )
        )
        worker.start()
        worker.join(timeout=0.5)
        assert worker.is_alive()
        assert other_run_partial.exists()
    worker.join(timeout=10)

    assert not worker.is_alive()
    assert len(results) == 1
    assert not other_run_partial.exists()


def test_prune_removes_backups_older_than_14_days(tmp_path: Path) -> None:
    now = dt.datetime(2026, 1, 20, 3, 0)
    for day in range(1, 20):
        _make_backup_dir(tmp_path, dt.datetime(2026, 1, day, 3, 0))
    notes = tmp_path / "notes"
    notes.mkdir()
    partial = _make_backup_dir(tmp_path, dt.datetime(2026, 1, 1, 3, 0), ".partial")

    removed = prune(tmp_path, now, 14)

    assert sorted(p.name for p in removed) == [
        f"learnmate-202601{day:02d}-030000" for day in range(1, 6)
    ]
    kept = [at for at, _ in list_backups(tmp_path)]
    assert kept == [dt.datetime(2026, 1, day, 3, 0) for day in range(6, 20)]
    assert notes.exists()
    assert partial.exists()


def test_nightly_runs_keep_14_backups(app: FastAPI, settings: Settings, tmp_path: Path):
    clock = FakeClock(dt.datetime(2026, 1, 1, 3, 0))
    backups = tmp_path / "backups"
    for _ in range(30):
        run_backup(settings.data_dir, backups, clock.now(), 14)
        clock.advance(seconds=86400)

    found = list_backups(backups)
    assert len(found) == 15
    assert found[-1][0] - found[0][0] == dt.timedelta(days=14)


@pytest.fixture
def cli_env(
    monkeypatch: pytest.MonkeyPatch, settings: Settings, tmp_path: Path
) -> Iterator[None]:
    monkeypatch.setenv("DATA_DIR", str(settings.data_dir))
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.setenv("DEVICE_TOKEN", "test-device-token")
    monkeypatch.setenv("BACKUP_ENABLED", "false")
    monkeypatch.setenv("WATCHDOG_ENABLED", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_restore_steps_bring_back_the_data(
    app: FastAPI,
    settings: Settings,
    cli_env: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    original = b"%PDF-1.4\noriginal"
    pdf = _write_file(settings, "7/01.pdf", original)
    with TestClient(app, headers=HEADERS) as client:
        client.post("/api/v1/subjects", json={"name": "Science"})
        assert main(["now"]) == 0
        capsys.readouterr()
        assert main(["list"]) == 0
        name = capsys.readouterr().out.split()[-1]
        client.post("/api/v1/subjects", json={"name": "History"})
        pdf.unlink()
    app.state.engine.dispose()

    assert main(["restore", name]) == 0
    assert f"Restored {name}." in capsys.readouterr().out

    fresh = create_app(settings)
    try:
        with TestClient(fresh, headers=HEADERS) as client:
            assert _subject_names(client) == ["Science"]
    finally:
        fresh.state.engine.dispose()
    assert pdf.read_bytes() == original
    assert list(settings.data_dir.glob("replaced-*/learnmate.db"))


def test_restore_rejects_unknown_or_partial_backup(
    app: FastAPI, settings: Settings, cli_env: None, tmp_path: Path
) -> None:
    assert main(["restore", "learnmate-20990101-000000"]) == 1
    before = settings.database_path.read_bytes()
    empty = _make_backup_dir(tmp_path / "backups", NOW)
    with pytest.raises(ValueError):
        restore(empty, settings.data_dir, NOW)
    assert settings.database_path.read_bytes() == before


@pytest.mark.parametrize(
    ("timezone", "now", "hour", "expected"),
    [
        ("UTC", dt.datetime(2026, 1, 5, 2, 0), 3, dt.datetime(2026, 1, 5, 3, 0)),
        ("UTC", dt.datetime(2026, 1, 5, 3, 0), 3, dt.datetime(2026, 1, 6, 3, 0)),
        (
            "Europe/London",
            dt.datetime(2026, 3, 28, 12, 0),
            3,
            dt.datetime(2026, 3, 29, 2, 0),
        ),
        (
            "Asia/Kolkata",
            dt.datetime(2026, 1, 5, 0, 0),
            3,
            dt.datetime(2026, 1, 5, 21, 30),
        ),
    ],
)
def test_next_run_at(timezone, now, hour, expected) -> None:
    assert next_run_at(now, hour, timezone) == expected


def test_is_overdue(tmp_path: Path) -> None:
    assert is_overdue(tmp_path, NOW)
    _make_backup_dir(tmp_path, NOW - dt.timedelta(hours=25))
    assert is_overdue(tmp_path, NOW)
    _make_backup_dir(tmp_path, NOW - dt.timedelta(hours=23))
    assert not is_overdue(tmp_path, NOW)


def test_backup_loop_runs_overdue_backup_then_sleeps(
    app: FastAPI,
    settings: Settings,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    waits: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        waits.append(seconds)
        raise asyncio.CancelledError

    monkeypatch.setattr(job.asyncio, "sleep", fake_sleep)
    loop_settings = settings.model_copy(
        update={"backup_dir": tmp_path / "backups", "timezone": "UTC", "backup_hour": 3}
    )
    clock = FakeClock(dt.datetime(2026, 1, 5, 9, 0))

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(backup_loop(loop_settings, clock))

    assert len(list_backups(loop_settings.backup_dir)) == 1
    assert waits == [18 * 3600]


def test_backup_loop_survives_error_checking_for_recent_backups(
    app: FastAPI,
    settings: Settings,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    waits: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        waits.append(seconds)
        raise asyncio.CancelledError

    def broken(*args, **kwargs):
        raise OSError("storage unavailable")

    monkeypatch.setattr(job.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(job, "is_overdue", broken)
    loop_settings = settings.model_copy(
        update={"backup_dir": tmp_path / "backups", "timezone": "UTC", "backup_hour": 3}
    )

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            backup_loop(loop_settings, FakeClock(dt.datetime(2026, 1, 5, 9, 0)))
        )

    assert waits == [18 * 3600]
