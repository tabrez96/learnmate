"""The provider factory; the interface lives in `learnmate.llm.types`."""

from learnmate.config import Settings
from learnmate.llm.fake import FakeLlm
from learnmate.llm.types import Llm


def make_llm(settings: Settings) -> Llm:
    if settings.llm_provider == "fake":
        return FakeLlm(settings)
    raise NotImplementedError("the anthropic provider is not available yet")
