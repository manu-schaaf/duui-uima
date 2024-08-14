import sys

import stanza

__meta__ = {
    "sys.version": sys.version,
    "stanza.__version__": stanza.__version__,
}


from app.parser.corenlp_ import CoreNLPModelProxy as ParserProxy
from app.parser.corenlp_ import CoreNLPProcessor as DependencyParser
from app.parser.corenlp_ import CoreNLPSentenceValidator as SentenceValidator

__all__ = [
    "ParserProxy",
    "DependencyParser",
    "SentenceValidator",
]
