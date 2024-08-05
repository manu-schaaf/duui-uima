import logging
from abc import abstractmethod
from dataclasses import dataclass
from typing import Callable, Final, Generic, Self, TypeVar

from app.model import DuuiRequest, DuuiResponse, Offset

logger = logging.getLogger(__name__)


NlpAnnotation = TypeVar("NlpAnnotation")


class ModelProxyABC(Generic[NlpAnnotation]):
    @abstractmethod
    def __getitem__(self, lang: str) -> Callable[[str], NlpAnnotation]:
        pass


@dataclass
class SentenceValidatorABC(Generic[NlpAnnotation]):
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
    def check(cls, sentence: NlpAnnotation) -> Self:
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


class ProcessorABC(Generic[NlpAnnotation]):
    @classmethod
    @abstractmethod
    def with_proxy(cls, proxy: ModelProxyABC) -> Self:
        pass

    @abstractmethod
    def process(
        self,
        request: DuuiRequest,
    ) -> DuuiResponse:
        pass

    @abstractmethod
    def post_process(
        self,
        annotations: list[NlpAnnotation],
        offsets: list[Offset],
    ) -> DuuiResponse:
        pass


EOS_MARKERS: Final[set[str]] = set(".?!")
