
from pylatexenc.latexwalker import LatexCommentNode, LatexMacroNode

from latexpp.fixes import PragmaFix


class SkipPragma(PragmaFix):
    r"""
    Remove all sections in the LaTeX source marked by the LPP-pragma::

      %%!lpp skip {
      ...
      %%!lpp }

    """
    def __init__(self):
        super().__init__()

    def fix_pragma_scope(self, nodelist, jstart, jend, instruction, args):

        if instruction != 'skip':
            return jend

        nodelist[jstart:jend] = []

        return jstart
