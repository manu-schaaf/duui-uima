import sys

import stanza

__meta__ = {
    "sys.version": sys.version,
    "stanza.__version__": stanza.__version__,
}


from app.specific.stanza import StanzaModelProxy as SpecificModelProxy
from app.specific.stanza import StanzaProcessor as SpecificProcessor
from app.specific.stanza import StanzaSentenceValidator as SpecificSentenceValidator

__all__ = [
    "SpecificModelProxy",
    "SpecificProcessor",
    "SpecificSentenceValidator",
]
