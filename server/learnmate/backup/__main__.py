"""Run a backup now, list backups, or restore one: python -m learnmate.backup now | list | restore <name>."""

import argparse
import sys

from learnmate.backup.service import (
    list_backups,
    parse_backup_name,
    restore,
    run_backup,
)
from learnmate.clock import SystemClock
from learnmate.config import get_settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m learnmate.backup")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("now", help="make a backup now")
    commands.add_parser("list", help="list finished backups, oldest first")
    restore_parser = commands.add_parser("restore", help="restore a backup")
    restore_parser.add_argument("name")
    args = parser.parse_args(argv)

    settings = get_settings()
    clock = SystemClock()
    if args.command == "now":
        path = run_backup(
            settings.data_dir,
            settings.backup_dir,
            clock.now(),
            settings.backup_keep_days,
        )
        print(path.name)
        return 0
    if args.command == "list":
        for _at, path in list_backups(settings.backup_dir):
            print(path.name)
        return 0
    backup = settings.backup_dir / args.name
    if parse_backup_name(args.name) is None or not backup.is_dir():
        print(f"No backup named {args.name} in {settings.backup_dir}", file=sys.stderr)
        return 1
    aside = restore(backup, settings.data_dir, clock.now())
    print(f"Restored {args.name}. The replaced data is in {aside}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
