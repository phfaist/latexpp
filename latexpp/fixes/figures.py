import os
import os.path
import shutil

from pylatexenc.latexwalker import LatexMacroNode


exts = ['', '.pdf', '.png', '.jpg', '.jpeg', '.eps']

class CopyNumberFigsFixes(object):
    def __init__(self):
        self.fig_counter = 1 # start at Fig #1 because journals like separate
                             # files with numbered figures starting at 1

    def fix_node(self, n, lpp):

        if n.isNodeType(LatexMacroNode) and n.macroname == 'includegraphics':
            # note, argspec is '[{'

            # find file and copy it

            # arg is a group necessarily (unlikely to have single-char file name...)
            picfname = "".join(nn.latex_verbatim() for nn in n.nodeargd.argnlist[1].nodelist)
            ext = ''
            for e in exts:
                if os.path.exists(picfname+e):
                    picfname = picfname+e
                    ext = e
                    break
            else:
                logger.warning("File not found: %s. Tried extensions %r", picfname, exts)
                return None # keep the node as it is

            figcntname = 'fig-%d%s'%(self.fig_counter, ext)

            shutil.copy2(picfname, os.path.join(lpp.output_dir, figcntname))

            return r'\includegraphics' + \
                (n.nodeargd.argnlist[0].latex_verbatim() if n.nodeargd.argnlist[0] else '') + \
                '{' + figcntname + '}'

        return None

