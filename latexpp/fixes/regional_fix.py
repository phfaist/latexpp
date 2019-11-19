
from pylatexenc.latexwalker import LatexCommentNode, LatexMacroNode

from latexpp.fixes import PragmaFix


class Apply(PragmaFix):
    r"""
    Remove all LaTeX comments from the latex document.

    Arguments:

    - `leave_percent`: If `True` (the default), then a full LaTeX comment is
      replaced by an empty comment, i.e., a single percent sign and whatever
      whitespace followed the comment (the whitespace is anyways ignored by
      LaTeX).  If `False`, then the comment and following whitespace is removed
      entirely.
    """
    def __init__(self, region=None, fixes=None):
        super().__init__()
        self.region = region
        self.fixes = fixes if fixes else []
        self.subpp = None


    def initialize(self):
        self.subpp = self.lpp.create_subpreprocessor()
        self.subpp.install_fixes_from_config(self.fixes)
        self.subpp.initialize()

    def fix_pragma_scope(self, nodelist, jstart, jend, instruction, args):

        if instruction != 'regional-fix':
            return jend # skip

        region_name, = args

        if region_name != self.region:
            return jend # skip

        newnodes = self.subpp.preprocess(nodelist[jstart+1:jend-1])

        nodelist[jstart:jend] = newnodes

        return jstart+len(newnodes)
