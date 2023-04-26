import pylatexenc

try:
    import pylatexenc.latexnodes

    from ._newcommand_pylatexenc3 import Expand
except ImportError:
    
    from ._newcommand_pylatexenc2 import Expand
