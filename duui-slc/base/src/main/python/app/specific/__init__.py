import sys
from typing import Final

from app.abc import ModelProxyABC, ProcessorABC, SentenceValidatorABC


__meta__: Final[dict[str, str]] = {
    "sys.version": sys.version,
}


class SpecificModelProxy(ModelProxyABC):
    pass


class SpecificSentenceValidator(SentenceValidatorABC):
    pass


class SpecificProcessor(ProcessorABC):
    pass


__all__ = [
    "SpecificModelProxy",
    "SpecificSentenceValidator",
    "SpecificProcessor",
]
