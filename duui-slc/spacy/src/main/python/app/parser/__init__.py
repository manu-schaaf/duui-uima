import sys

import spacy

__meta__ = {
    "sys.version": sys.version,
    "spacy.__version__": spacy.__version__,
}


from app.parser.spacy import SpaCyModelProxy as ParserProxy
from app.parser.spacy import SpaCyProcessor as DependencyParser
from app.parser.spacy import SpaCySentenceValidator as SentenceValidator

__all__ = [
    "ParserProxy",
    "DependencyParser",
    "SentenceValidator",
]
