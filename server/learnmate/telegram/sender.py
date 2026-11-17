"""Sending a message to the linked chat: the real bot and a recording fake."""

from dataclasses import dataclass
from typing import Protocol

import telegram
import telegram.error

from learnmate.telegram.templates import OutMessage


class SendError(Exception):
    """The message could not be delivered; it should be retried later."""


class Sender(Protocol):
    async def send(self, chat_id: int, message: OutMessage) -> None: ...


@dataclass
class Sent:
    chat_id: int
    message: OutMessage


class FakeSender:
    def __init__(self) -> None:
        self.sent: list[Sent] = []
        self._failures = 0

    def fail_next(self, times: int = 1) -> None:
        self._failures = times

    async def send(self, chat_id: int, message: OutMessage) -> None:
        if self._failures:
            self._failures -= 1
            raise SendError("fake failure")
        self.sent.append(Sent(chat_id, message))


class BotSender:
    def __init__(self, bot: telegram.Bot) -> None:
        self._bot = bot

    async def send(self, chat_id: int, message: OutMessage) -> None:
        markup = None
        if message.buttons:
            markup = telegram.InlineKeyboardMarkup(
                [
                    [
                        telegram.InlineKeyboardButton(b.text, callback_data=b.data)
                        for b in message.buttons
                    ]
                ]
            )
        # No parse_mode: plain text, so names with * or _ can't break a message.
        try:
            await self._bot.send_message(chat_id, message.text, reply_markup=markup)
        except telegram.error.TelegramError as e:
            raise SendError(str(e)) from e
