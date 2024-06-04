import sys

import spacy

__meta__ = {
    "sys.version": sys.version,
    "spacy.__version__": spacy.__version__,
}


from app.specific.spacy import SpaCyModelProxy as SpecificModelProxy
from app.specific.spacy import SpaCyProcessor as SpecificProcessor
from app.specific.spacy import SpaCySentenceValidator as SpecificSentenceValidator

__all__ = [
    "SpecificModelProxy",
    "SpecificProcessor",
    "SpecificSentenceValidator",
]
