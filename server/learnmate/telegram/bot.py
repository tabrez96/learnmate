"""The Telegram bot: long polling plus the outbox sender loop."""

import asyncio
import contextlib
import logging

from sqlalchemy.orm import Session, sessionmaker
from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from learnmate.clock import Clock
from learnmate.config import Settings
from learnmate.telegram.links import TelegramHooks, handle_new_pin, link_chat
from learnmate.telegram.outbox import deliver_due
from learnmate.telegram.sender import BotSender
from learnmate.telegram.templates import (
    LINK_REFUSED,
    LINKED,
    NEW_PIN_PREFIX,
)

log = logging.getLogger(__name__)


class TelegramRunner:
    def __init__(
        self,
        token: str,
        session_factory: sessionmaker[Session],
        clock: Clock,
        hooks: TelegramHooks,
        poll_seconds: float,
    ) -> None:
        self._session_factory = session_factory
        self._clock = clock
        self._hooks = hooks
        self._poll_seconds = poll_seconds
        self._task: asyncio.Task[None] | None = None
        self.application = Application.builder().token(token).build()
        self.application.add_handler(CommandHandler("start", self._on_start))
        self.application.add_handler(
            CallbackQueryHandler(self._on_callback, pattern=f"^{NEW_PIN_PREFIX}")
        )

    async def start(self) -> None:
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        self._task = asyncio.create_task(self._send_loop())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()

    async def _send_loop(self) -> None:
        sender = BotSender(self.application.bot)
        while True:
            try:
                with self._session_factory() as db:
                    await deliver_due(db, sender, self._clock)
            except Exception:
                log.exception("Telegram sender pass failed")
            await asyncio.sleep(self._poll_seconds)

    async def _on_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        code = context.args[0] if context.args else ""
        with self._session_factory() as db:
            user = update.effective_user
            ok = link_chat(
                db, code, update.effective_chat.id, user.username if user else None
            )
        await update.effective_message.reply_text(LINKED if ok else LINK_REFUSED)

    async def _on_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        with self._session_factory() as db:
            reply = handle_new_pin(db, self._hooks, query.message.chat.id, query.data)
        await query.answer(reply)


def make_telegram_runner(
    settings: Settings,
    session_factory: sessionmaker[Session],
    clock: Clock,
    hooks: TelegramHooks,
) -> TelegramRunner | None:
    if not settings.telegram_bot_token:
        return None
    return TelegramRunner(
        settings.telegram_bot_token,
        session_factory,
        clock,
        hooks,
        settings.telegram_poll_seconds,
    )
