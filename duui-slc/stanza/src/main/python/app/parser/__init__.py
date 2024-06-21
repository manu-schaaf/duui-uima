import sys

import stanza

__meta__ = {
    "sys.version": sys.version,
    "stanza.__version__": stanza.__version__,
}


from app.parser.stanza import StanzaModelProxy as ParserProxy
from app.parser.stanza import StanzaProcessor as DependencyParser
from app.parser.stanza import StanzaSentenceValidator as SentenceValidator

__all__ = [
    "ParserProxy",
    "DependencyParser",
    "SentenceValidator",
]
