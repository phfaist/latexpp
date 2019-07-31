
import os.path
from pylatexenc.latexwalker import LatexMacroNode

from latexpp.fixes import BaseFix


exts = ['', '.tex', '.latex']

class EvalInput(BaseFix):
    r"""
    Evaluate ``\input`` and ``\include`` routines by replacing the corresponding
    instruction by the contents of the included file.
    """

    def fix_node(self, n, lpp, **kwargs):

        if n.isNodeType(LatexMacroNode) and n.macroname in ('input', 'include'):
            # arg is a group necessarily (unlikely to have single-char file name...)
            infname = "".join(nn.latex_verbatim() for nn in n.nodeargd.argnlist[0].nodelist)

            ext = ''
            for e in exts:
                if os.path.exists(infname+e):
                    infname = infname+e
                    ext = e
                    break
            else:
                logger.warning("File not found: %s. Tried extensions %r", infname, exts)
                return None # keep the node as it is

            # open that file and go through it, too

            with open(infname) as f:
                infdata = f.read()


            res = ''
            # for \include, we need to issue \clearpage.  See
            # https://tex.stackexchange.com/a/32058/32188
            if n.macroname == 'include':
                res = r'\clearpage\n'

            res += lpp.execute_string(infdata)

            return res

        return None

