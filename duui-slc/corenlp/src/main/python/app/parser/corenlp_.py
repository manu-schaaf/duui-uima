import logging
from typing import Final, Self, TypeVar

from app.abc import ModelProxyABC, ProcessorABC, SentenceValidatorABC
from app.model import DuuiRequest, DuuiResponse, Offset, UimaDependency, UimaToken
from app.utils import EOS_MARKERS
from stanza.server import CoreNLPClient

from cassis.cas import Utf16CodepointOffsetConverter

import socket

logger = logging.getLogger(__name__)

CoreNLPDocument = TypeVar("CoreNLP_pb2.Document")
CoreNLPToken = TypeVar("CoreNLP_pb2.Token")

POS_VERBS: Final = {"VB", "VBD", "VBG", "VBN", "VBP", "VBZ", "VERB", "AUX"}

model_map = {
    "en": 'english',
    "en_US": 'english',
    "en_GB": 'english',
    "en_AU": 'english',
    "en_CA": 'english',
    "de": 'german',
    "de_DE": 'german',
    "de_AT": 'german',
    "de_CH": 'german',
}

class CoreNLPModelProxy(ModelProxyABC[CoreNLPClient]):
    def __init__(self):
        self.models = {}

    def __getitem__(self, lang: str):
        lang = model_map.get(lang.replace("-", "_"), lang)
        if self.models.get(lang) is None:
            logger.info(f"corenlp: Initiate a CoreNLPClient for '{lang}')")
            nlp = CoreNLPClient(
                annotators=['tokenize','ssplit','pos', 'lemma', 'mwt', 'depparse'],
                timeout=30000,
                properties=lang,
                endpoint=f'http://localhost:{CoreNLPModelProxy.find_free_port()}',
                preload=True,
            )
            logger.info(
                f"corenlp: Loaded\nCoreNLP Client ({lang})\n"
                + f"annotators: {nlp.annotators}\n"
            )
            self.models[lang] = nlp
        return self.models[lang]

    @staticmethod
    def find_free_port():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('localhost', 0))
        port = s.getsockname()[1]
        s.close()
        return port

class CoreNLPSentenceValidator(SentenceValidatorABC[CoreNLPDocument]):
    @classmethod
    def check(cls, doc: CoreNLPDocument):
        if not doc.text.strip()[0].isupper():
            logger.info("CoreNLP: Sentence does not start with a capitalized character")
            return cls(False)
        if doc.text.strip()[-1] not in EOS_MARKERS:
            logger.info("CoreNLP: Sentence does not end with a period, question mark, or exclamation mark")
            return cls(True, False)
        tokens = doc.sentence[0].token
        if not any(token.pos in POS_VERBS for token in tokens):
            logger.info("CoreNLP: Sentence does not contain a verb")
            return cls(True, True, False)
        if doc.text.count('"') % 2 != 0:
            logger.info("CoreNLP: The number of quotation marks is not even")
            return cls(True, True, True, False)
        if doc.text.count("(") != doc.text.count(")"):
            logger.info("CoreNLP: The number of left brackets is not equal to that of right brackets")
            return cls(True, True, True, True, False)
        return cls(True, True, True, True, True)

class CoreNLPProcessor(ProcessorABC[CoreNLPDocument]):
    def __init__(self, proxy: CoreNLPModelProxy) -> None:
        super().__init__()
        self.proxy = proxy

    @classmethod
    def with_proxy(cls, proxy: ModelProxyABC) -> Self:
        return cls(proxy)

    def process(self, request: DuuiRequest):
        if request.sentences is None:
            raise ValueError("Sentences offsets are required for CoreNLP")

        nlp = self.proxy[request.language]

        annotations = []
        offsets = request.sentences
        text = request.text
        
        # Encode text to utf-16 to handle surrogate pairs
        # and create offset mapping for utf-16 text
        text_utf16 = text.encode('utf-16', 'surrogatepass').decode('utf-16', 'surrogateescape')
        converter = Utf16CodepointOffsetConverter()
        converter.create_offset_mapping(text_utf16)
        adjusted_offsets = []
        for offset in offsets:
            new_begin = converter.external_to_python(offset.begin)
            new_end = converter.external_to_python(offset.end)
            adjusted_offsets.append(Offset(begin=new_begin, end=new_end))
        
        for offset in adjusted_offsets:
            try:
                annotations.append(nlp.annotate(text_utf16[offset.begin : offset.end], properties={'ssplit.isOneSentence': 'true'}))
                logger.info(f"CoreNLP: Processed a sentence 1: {text_utf16[offset.begin : offset.end]}")
            except Exception as e:
                logger.error(f"CoreNLP Parsing Error: {e}")

        return self.post_process(
            annotations,
            offsets,
        )

    @staticmethod
    def post_process(annotations: list[CoreNLPDocument], offsets: list[Offset]):
        tokens_indices = 0
        results = DuuiResponse(sentences=None, tokens=[], dependencies=[])
        
        for annotation, offset in zip(annotations, offsets):
            sentences = annotation.sentence
            if len(sentences) != 1:
                raise ValueError("CoreNLP split a single sentence into multiple sentences")
            
            sentence = sentences[0]
            if not bool(CoreNLPSentenceValidator.check(annotation).is_standalone()):
                logger.info("CoreNLP: Sentence is not standalone. Skipping.")
                continue
            
            tokens: list[CoreNLPToken] = sentence.token
            
            dependency_annotations = {}
            sentence_begin_index = tokens_indices
            for dep in sentence.basicDependencies.edge:
                parent_index = sentence_begin_index + dep.source - 1
                child_index = sentence_begin_index + dep.target - 1
                dependency_annotations[child_index] = (parent_index, dep.dep)
                
            for token in tokens:
                token_idx = tokens_indices
                tokens_indices += 1

                begin = token.beginChar + offset.begin
                end = token.endChar + offset.begin
                
                results.tokens.append(
                    UimaToken(
                        begin=begin,
                        end=end,
                        idx=token_idx,
                        pos=token.pos,
                        lemma=token.lemma,
                    )
                )
            
                if token_idx in dependency_annotations:
                    head_index = dependency_annotations[token_idx][0]
                    dep_rel = dependency_annotations[token_idx][1]
                else:
                    head_index = token_idx
                    dep_rel = "root"
                
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