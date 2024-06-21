import sys
from typing import Final

from app.abc import ModelProxyABC, ProcessorABC, SentenceValidatorABC


__meta__: Final[dict[str, str]] = {
    "sys.version": sys.version,
}


class ParserProxy(ModelProxyABC):
    pass


class SentenceValidator(SentenceValidatorABC):
    pass


class DependencyParser(ProcessorABC):
    pass


__all__ = [
    "ParserProxy",
    "SentenceValidator",
    "DependencyParser",
]
