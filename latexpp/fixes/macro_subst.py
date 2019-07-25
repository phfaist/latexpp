
from pylatexenc.latexwalker import LatexMacroNode, LatexEnvironmentNode

from latexpp.macro_subst_helper import MacroSubstHelper


class Fixes(object):
    def __init__(self, macros={}, environments={}):
        self.helper = MacroSubstHelper(macros, environments)

    def specs(self):
        return dict(**self.helper.get_specs())

    def fix_node(self, n, lpp):

        c = self.helper.get_node_cfg(n)
        if c is not None:
            return self.helper.eval_subst(c, n, lpp)

        return None
