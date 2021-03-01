
#from pylatexenc.latexwalker import LatexCommentNode, LatexMacroNode

from latexpp.pragma_fix import PragmaFix


class Apply(PragmaFix):
    r"""
    Apply a regional fix, i.e., apply a set of rules to a delimited section of
    your document.

    This fix looks for one or more delimited sections in your document (see
    below) whose name matches the given argument `region`.  On those delimited
    sections, a specified list of custom fixes are executed.  The fixes to run
    are specified in the `fixes` argument, with a format that is exactly the
    same as the global `fixes:` dictionary key in the `lppconfig.yml` file.

    The section of your document that you would like to apply the specified
    fixes to is marked using a ``%%!lpp`` pragma instruction of the form::

      %%!lpp regional-fix My-Region-Name-1 {
      ...
      ...
      %%!lpp }

    Arguments:

    - `region`: is the name of the region that the given extra fixes should be
      applied to.  In your LaTeX code, you should have a ``%%!lpp regional-fix``
      pragma instruction that delimits the sections of code on which these fixes
      should be applied.  In the example above, `region="My-Region-Name-1"`.

    - `fixes`: a data structure of fixes configuration like the main `fixes`
      section of the `latexpp` configuration.  You can specify here any fixes
      that you could specify for the document at the top level.
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
