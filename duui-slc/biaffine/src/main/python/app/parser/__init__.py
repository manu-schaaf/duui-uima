import sys
import supar

__meta__ = {
    "sys.version": sys.version,
    "supar.__version__": supar.__version__,
}


from app.parser.biaffine_ import BiaffineModelProxy as ParserProxy
from app.parser.biaffine_ import BiaffineProcessor as DependencyParser
from app.parser.biaffine_ import BiaffineSentenceValidator as SentenceValidator

__all__ = [
    "ParserProxy",
    "DependencyParser",
    "SentenceValidator",
]
