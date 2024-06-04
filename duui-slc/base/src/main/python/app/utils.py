import logging
from dataclasses import dataclass, field
from typing import Final

from spacy.tokens import Token

logger = logging.getLogger(__name__)


EOS_MARKERS: Final[set[str]] = set(".?!")


@dataclass
class TokenToId:
    mapping: dict[int, int] = field(default_factory=dict)

    def __getitem__(self, token: Token):
        return self.mapping[hash(token)]

    def __setitem__(self, token: Token, value: int):
        if hash(token) in self.mapping:
            raise ValueError(f"Token {token} already exists in the mapping.")
        if value != len(self.mapping):
            raise ValueError(f"Value {value} is not the next value in the mapping.")
        self.mapping[hash(token)] = value

    def add(self, token: Token) -> int:
        _hash = hash(token)
        self.mapping[_hash] = len(self.mapping)
        return self.mapping[_hash]
