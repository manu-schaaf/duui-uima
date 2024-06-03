import logging
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Final, Generic, TypeVar

from app.model import DuuiResponse, Offset
from spacy.tokens import Token

logger = logging.getLogger(__name__)

T = TypeVar("T")
T_co = TypeVar("T_co", contravariant=True)

EOS_MARKERS: Final[set[str]] = set(".?!")

@dataclass
class GenericSentenceValidation(Generic[T_co]):
    first_is_upper: bool | None = None
    last_is_punctuation: bool | None = None
    has_verb: bool | None = None
    even_quotes: bool | None = None
    balanced_brackets: bool | None = None


    def is_standalone(self):
        return all(
            (
                self.first_is_upper,
                self.last_is_punctuation,
                self.has_verb,
                self.even_quotes,
                self.balanced_brackets,
            )
        )

    @classmethod
    @abstractmethod
    def check(cls, sentence: T_co):
        """
        Check if a sentence is a standalone sentence.
        Standalone sentences must meet the following requirements:
        - Sentences must start with a capitalized character.
        - Sentences must end with a period, or a question mark, or an exclamation mark.
        - Sentences must contain a verb based on the part-of-speech tags.
        - The number of (double) quotation marks must be even.
        - The number of left brackets must be equal to that of right brackets.

        Args:
            sent (T_co): The sentence to be checked.

        Returns:
            bool: If the sentence is a standalone sentence.
        """
        pass


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


class GenericModelProxy(Generic[T]):
    @abstractmethod
    def __getitem__(self, lang: str) -> T:
        pass


class GenericPostProcessor(Generic[T_co]):
    @classmethod
    @abstractmethod
    def process(cls, annotations: list[T_co], offsets: list[Offset]) -> DuuiResponse:
        pass
