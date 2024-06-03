import itertools
import logging

import spacy
from app.model import DuuiResponse, Offset, UimaDependency, UimaToken
from app.utils import (
    EOS_MARKERS,
    GenericModelProxy,
    GenericPostProcessor,
    GenericSentenceValidation,
    TokenToId,
)
from spacy.language import Language
from spacy.tokens import Doc, Span

logger = logging.getLogger(__name__)

# model_en = "en_core_web_trf"
model_en = "en_core_web_sm"
# model_de = "de_dep_news_trf"
model_de = "de_core_news_sm"
model_map = {
    "en": model_en,
    "en_US": model_en,
    "en_GB": model_en,
    "en_AU": model_en,
    "en_CA": model_en,
    "de": model_de,
    "de_DE": model_de,
    "de_AT": model_de,
    "de_CH": model_de,
}


class SpecificModelProxy(GenericModelProxy[Language]):
    def __init__(self):
        self.models = {}

    def __getitem__(self, lang: str):
        lang = model_map.get(lang.replace("-", "_"), lang)
        if self.models.get(lang) is None:
            logger.info(f"load({lang})")
            nlp = spacy.load(
                lang,
                disable=[
                    "ner",
                ],
            )
            nlp.add_pipe("sentencizer")
            self.models[lang] = nlp
            logger.info(f"load({lang}): done")
        return self.models[lang]


class SpecificSentenceValidtion(GenericSentenceValidation[Span]):
    @classmethod
    def check(cls, sentence: Span):
        if not sentence.text.strip()[0].isupper():
            return cls(False)
        if sentence.text.strip()[-1] not in EOS_MARKERS:
            return cls(True, False)
        if not any((tok.pos_ == "VERB" or tok.pos_ == "AUX" for tok in sentence)):
            return cls(True, True, False)
        if sentence.text.count('"') % 2 != 0:
            return cls(True, True, True, False)
        if sentence.text.count("(") != sentence.text.count(")"):
            return cls(True, True, True, True, False)
        return cls(True, True, True, True, True)


class SpecificPostProcessor(GenericPostProcessor[Doc]):
    @classmethod
    def process(cls, annotations: list[Doc], offsets: list[Offset]):
        token_to_id = TokenToId()
        results = DuuiResponse(sentences=[], tokens=[], dependencies=[])
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

                if bool(SpecificSentenceValidtion.check(sentence).is_standalone()):
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
                            UimaToken(
                                begin=begin,
                                end=end,
                                pos=doc[token.i].pos_,
                                tag=doc[token.i].tag_,
                                lemma=doc[token.i].lemma_,
                                morph={
                                    k.lower(): v
                                    for k, v in token.morph.to_dict().items()
                                },
                                idx=token_idx,
                            )
                        )

                    for token in sentence:
                        begin = token.idx + offset.begin
                        end = begin + len(token)
                        results.dependencies.append(
                            UimaDependency(
                                begin=begin,
                                end=end,
                                governor=token_to_id[token.head],
                                dependent=token_to_id[token],
                                type=token.dep_.upper(),
                                flavor="basic",
                            )
                        )

        return results
