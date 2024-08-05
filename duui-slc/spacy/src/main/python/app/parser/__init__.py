import sys

import spacy

__meta__ = {
    "sys.version": sys.version,
    "spacy.__version__": spacy.__version__,
}


from app.parser.spacy_ import SpaCyModelProxy as ParserProxy
from app.parser.spacy_ import SpaCyProcessor as DependencyParser
from app.parser.spacy_ import SpaCySentenceValidator as SentenceValidator

__all__ = [
    "ParserProxy",
    "DependencyParser",
    "SentenceValidator",
]
