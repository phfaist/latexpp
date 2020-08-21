
#from pylatexenc.latexwalker import LatexCommentNode, LatexMacroNode

from latexpp.pragma_fix import PragmaFix


class SkipPragma(PragmaFix):
    r"""
    This fix remove all sections in the LaTeX source marked by the LPP-pragma::

      %%!lpp skip {
      ...
      %%!lpp }

    .. note::

       You should NOT invoke this fix directly, it is automatically
       included for you!
    """
    def __init__(self):
        super().__init__()

    def fix_pragma_scope(self, nodelist, jstart, jend, instruction, args):

        if instruction != 'skip':
            return jend

        nodelist[jstart:jend] = []

        return jstart
