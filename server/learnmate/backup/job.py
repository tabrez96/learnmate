"""The nightly backup loop, started from the server's lifespan."""

import asyncio
import logging

from learnmate.backup.service import is_overdue, next_run_at, run_backup
from learnmate.clock import Clock
from learnmate.config import Settings

log = logging.getLogger(__name__)


def _run(settings: Settings, clock: Clock) -> None:
    path = run_backup(
        settings.data_dir, settings.backup_dir, clock.now(), settings.backup_keep_days
    )
    log.info("Backup written to %s", path)


async def _attempt(settings: Settings, clock: Clock) -> None:
    try:
        await asyncio.to_thread(_run, settings, clock)
    except Exception:
        log.exception("Backup failed")


async def _catch_up(settings: Settings, clock: Clock) -> None:
    try:
        overdue = await asyncio.to_thread(is_overdue, settings.backup_dir, clock.now())
    except OSError:
        log.exception("Could not check for recent backups")
        return
    if overdue:
        await _attempt(settings, clock)


async def backup_loop(settings: Settings, clock: Clock) -> None:
    await _catch_up(settings, clock)
    while True:
        now = clock.now()
        wait = (
            next_run_at(now, settings.backup_hour, settings.timezone) - now
        ).total_seconds()
        await asyncio.sleep(max(wait, 0))
        await _attempt(settings, clock)
