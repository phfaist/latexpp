
from pylatexenc.macrospec import MacroSpec
from pylatexenc.latexwalker import LatexMacroNode



class Fixes(object):
    def __init__(self, macros):
        self.macros = macros

    def specs(self):
        # declare any macros that have arguments
        mlist = []
        for m, mconfig in self.macros.items():
            if isinstance(mconfig, dict) and mconfig.get('argspec', None):
                mlist.append( MacroSpec(m, mconfig['argspec']) )

        return dict(macros=mlist)

    def fix_node(self, n, lpp):

        if n.isNodeType(LatexMacroNode) and n.macroname in self.macros:
            c = self.macros[n.macroname]
            if isinstance(c, str):
                repl = c
            else:
                repl = c.get('repl')
            
            return repl % dict(
                (str(1+k), v)
                for k, v in enumerate(
                        lpp.latexpp_group_contents(n) if n is not None else ''
                        for n in n.nodeargd.argnlist
                )
            )

        return None
