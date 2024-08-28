import logging
from typing import Self, TypeVar, Final

from app.abc import ModelProxyABC, ProcessorABC, SentenceValidatorABC
from app.model import DuuiRequest, DuuiResponse, Offset, UimaDependency, UimaToken
from app.utils import EOS_MARKERS

from supar import Parser
from supar.utils.data import Dataset
from supar.models.dep.biaffine.transform import CoNLLSentence


from stanza import Pipeline
from stanza.models.common.doc import Document

import warnings
warnings.filterwarnings("ignore", message=".*weights_only=False.*", category=FutureWarning)
logger = logging.getLogger(__name__)

Language = TypeVar("Language")

model_map = {
    "en": 'en',
    "en_US": 'en',
    "en_GB": 'en',
    "en_AU": 'en',
    "en_CA": 'en',
    "de": 'de',
    "de_DE": 'de',
    "de_AT": 'de',
    "de_CH": 'de',
}

POS_VERBS: Final = {"VERB", "AUX"}

class CRF2oModelProxy(ModelProxyABC[Language]):
    def __init__(self):
        self.models = {}

    def __getitem__(self, lang: str):
        lang = model_map.get(lang.replace("-", "_"), lang)
        if self.models.get(lang) is None:
            logger.info(f"CRF2o: Initiate a dependency parser for '{lang}'")
            nlp = Parser.load(
                f'./app/parser/models/crf2o/{lang}/model.pt'
            )
            logger.info(
                f"CRF2o: Loaded a Dependency Parser ({lang})\n"
            )
            
            logger.info(f"CRF2o: Initiate a stanza preprocessing pipeline for '{lang}'")
            preprocessor = Pipeline(
                lang=lang,
                processors='tokenize,pos,lemma',
                tokenize_no_ssplit=True
            )
            logger.info(
                f"CRF2o: Loaded a stanza preprocessing pipeline ({lang})\n"
            )
            
            self.models[lang] = {
                "parser": nlp,
                "preprocessor": preprocessor
            }
            
        return self.models[lang]

class CRF2oSentenceValidator(SentenceValidatorABC[CoNLLSentence]):
    @classmethod
    def check(cls, sentence: CoNLLSentence):
        if not sentence.words[0][0].isupper():
            logger.info("CRF2o: Sentence does not start with a capitalized character")
            return cls(False)
        if sentence.words[-1][-1] not in EOS_MARKERS:
            logger.info("CRF2o: Sentence does not end with a period, question mark, or exclamation mark")
            return cls(True, False)
        if not any(pos in POS_VERBS for pos in sentence.upos):
            logger.info("CoreNLP: Sentence does not contain a verb")
            return cls(True, True, False)
        if ' '.join(sentence.words).count('"') % 2 != 0:
            logger.info("CRF2o: The number of quotation marks is not even")
            return cls(True, True, True, False)
        if ' '.join(sentence.words).count("(") != ' '.join(sentence.words).count(")"):
            logger.info("CRF2o: The number of left brackets is not equal to that of right brackets")
            return cls(True, True, True, True, False)
        
        return cls(True, True, True, True, True)

class CRF2oProcessor(ProcessorABC[Dataset]):
    def __init__(self, proxy: CRF2oModelProxy) -> None:
        super().__init__()
        self.proxy = proxy

    @classmethod
    def with_proxy(cls, proxy: ModelProxyABC) -> Self:
        return cls(proxy)

    def process(self, request: DuuiRequest):
        if request.sentences is None:
            raise ValueError("Sentences offsets are required for CRF2o")

        nlp = self.proxy[request.language]['parser']
        preprocessor = self.proxy[request.language]['preprocessor']

        annotations = []
        offsets = request.sentences
        for offset in offsets:
            document: Document = preprocessor(request.text[offset.begin : offset.end])
            annotation: CoNLLSentence = nlp.predict(
                    [word.text for word in document.sentences[0].words], 
                    lang=None, 
                    prob=False, 
                    verbose=False
                    )[0]
            annotation.upos = [word.upos for word in document.sentences[0].words]
            annotation.xpos = [word.xpos for word in document.sentences[0].words]
            annotation.feats = [word.feats for word in document.sentences[0].words]
            annotation.lemma = [word.lemma for word in document.sentences[0].words]
            annotation.start_char = [word.start_char for word in document.sentences[0].words]
            annotation.end_char = [word.end_char for word in document.sentences[0].words]
            
            annotations.append(annotation)
            
        return self.post_process(
            annotations,
            offsets,
        )

    @staticmethod
    def post_process(annotations: list[CoNLLSentence], offsets: list[Offset]):

        results = DuuiResponse(sentences=None, tokens=[], dependencies=[])
        tokens_indices = 0
        for annotation, offset in zip(annotations, offsets):
            
            if not bool(CRF2oSentenceValidator.check(annotation).is_standalone()):
                logger.info("CRF2o: Sentence is not standalone. Skipping.")
                continue
                        
            sentence_begin_index = tokens_indices
            
            for token, head, rel, start_char, end_char, upos, xpos, lemma, feats in \
                zip(annotation.words, annotation.arcs, annotation.rels, annotation.start_char, annotation.end_char, annotation.upos, annotation.xpos, annotation.lemma, annotation.feats):
                
                token_idx = tokens_indices
                tokens_indices += 1
                
                begin = start_char + offset.begin
                end = end_char + offset.begin
                
                if head == 0:
                    head_index = token_idx
                    dep_rel = "root"
                else:
                    head_index = sentence_begin_index + head - 1
                    dep_rel = rel

                
                results.tokens.append(
                    UimaToken(
                        begin=begin,
                        end=end,
                        idx=token_idx,
                        pos=upos,
                        tag=xpos,
                        lemma=lemma,
                        morph=(
                            {
                                k.lower(): v
                                for k, v in (
                                    feat.split("=")
                                    for feat in feats.split("|")
                                    if "=" in feat
                                )
                            }
                            if feats
                            else None
                        ),
                    )
                )
            
                results.dependencies.append(
                    UimaDependency(
                        begin=begin,
                        end=end,
                        governor=head_index,
                        dependent=token_idx,
                        type=dep_rel,
                        flavor="basic",
                    )
            )
                
        return results