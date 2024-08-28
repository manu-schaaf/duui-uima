import sys
import supar

__meta__ = {
    "sys.version": sys.version,
    "supar.__version__": supar.__version__,
}


from app.parser.crf2o_ import CRF2oModelProxy as ParserProxy
from app.parser.crf2o_ import CRF2oProcessor as DependencyParser
from app.parser.crf2o_ import CRF2oSentenceValidator as SentenceValidator

__all__ = [
    "ParserProxy",
    "DependencyParser",
    "SentenceValidator",
]
