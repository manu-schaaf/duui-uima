from dataclasses import dataclass, field
import itertools
import logging
from spacy.tokens import Doc, Span, Token

from app.model import Offset, SpaCyAnnotations, SpaCyDependency, SpaCyToken

logger = logging.getLogger(__name__)


eos_markers = set(".?!")


@dataclass
class SentenceValidation:
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
    def check(cls, sent: Span):
        """
        Check if a sentence is a standalone sentence.
        Standalone sentences must meet the following requirements:
        - Sentences must start with a capitalized character.
        - Sentences must end with a period, or a question mark, or an exclamation mark.
        - Sentences must contain a verb based on the part-of-speech tags.
        - The number of (double) quotation marks must be even.
        - The number of left brackets must be equal to that of right brackets.

        Args:
            sent (Span): The sentence to be checked.

        Returns:
            bool: If the sentence is a standalone sentence.
        """
        if not sent.text.strip()[0].isupper():
            return cls(False)
        if sent.text.strip()[-1] not in eos_markers:
            return cls(True, False)
        if not any((tok.pos_ == "VERB" or tok.pos_ == "AUX" for tok in sent)):
            return cls(True, True, False)
        if sent.text.count('"') % 2 != 0:
            return cls(True, True, True, False)
        if sent.text.count("(") != sent.text.count(")"):
            return cls(True, True, True, True, False)
        return cls(True, True, True, True, True)


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


def post_process(annotations: list[Doc], offsets: list[Offset]):
    token_to_id = TokenToId()
    results = SpaCyAnnotations(sentences=[], tokens=[], dependencies=[])
    for doc, offset in zip(annotations, offsets):
        # Add a None to the end of the iterator to include the last sentence if it ends with a semicolon.
        it = itertools.chain(doc.sents, (None,))

        semicolon_begin = None
        for sentence in it:
            if sentence and sentence.text.strip().endswith(";"):
                semicolon_begin = semicolon_begin or sentence.start
                continue

            # If the previous sentence(s) ends with a semicolon, then the current sentence is a continuation of the previous sentence(s).
            if semicolon_begin is not None:
                # If the very last sentence ended with a semicolon, we include it anyways.
                sentence_end = sentence and sentence.end
                sentence = doc[semicolon_begin:sentence_end]

            if sentence is None:
                continue

            if bool(SentenceValidation.check(sentence).is_standalone()):
                results.sentences.append(
                    Offset(
                        begin=sentence[0].idx + offset.begin,
                        # add one to point to the next character after sentence end
                        end=sentence[-1].idx + offset.begin + 1,
                    )
                )
                for token in sentence:
                    token_idx = token_to_id.add(token)

                    begin = token.idx + offset.begin
                    # No need to add one here: already points to the next character
                    end = begin + len(token)
                    results.tokens.append(
                        SpaCyToken(
                            begin=begin,
                            end=end,
                            pos=doc[token.i].pos_,
                            tag=doc[token.i].tag_,
                            lemma=doc[token.i].lemma_,
                            morph={
                                k.lower(): v for k, v in token.morph.to_dict().items()
                            },
                            idx=token_idx,
                        )
                    )

                for token in sentence:
                    begin = token.idx + offset.begin
                    end = begin + len(token)
                    results.dependencies.append(
                        SpaCyDependency(
                            begin=begin,
                            end=end,
                            governor=token_to_id[token.head],
                            dependent=token_to_id[token],
                            type=token.dep_.upper(),
                            flavor="basic",
                        )
                    )

    return results
