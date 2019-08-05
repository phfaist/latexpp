import os
import os.path as os_path # allow tests to monkey-patch this

import logging
logger = logging.getLogger(__name__)

from pylatexenc.latexwalker import LatexMacroNode

from latexpp.fixes import BaseFix


exts = ['', '.tex', '.latex']

class EvalInput(BaseFix):
    r"""
    Evaluate ``\input`` and ``\include`` routines by replacing the corresponding
    instruction by the contents of the included file.

    The contents of the included file will be processed with the rules that are
    declared *after* the `EvalInput` rule.  Any rules that have already been
    applied do not affect the contents pasted in place of the
    ``\input``/``\include`` directives.

    .. note::

       You most likely want to have this rule first in your `lppconfig.yml` fix
       list.
    """

    def fix_node(self, n, **kwargs):

        if n.isNodeType(LatexMacroNode) and n.macroname in ('input', 'include'):
        
            if not n.nodeargd.argnlist:
                logger.warning(r"Invalid \input/\include directive: ‘%s’, skipping.",
                               n.to_latex())
                return None

            infname = self.preprocess_arg_latex(n, 0)

            ext = ''
            for e in exts:
                if os_path.exists(infname+e):
                    infname = infname+e
                    ext = e
                    break
            else:
                logger.warning("File not found: %s. Tried extensions %r", infname, exts)
                return None # keep the node as it is

            # open that file and go through it, too

            infdata = self._read_file_contents(infname)

            res = ''
            # for \include, we need to issue \clearpage.  See
            # https://tex.stackexchange.com/a/32058/32188
            if n.macroname == 'include':
                res = r'\clearpage' + '\n'

            res += infdata

            return res # replace the input node by the content of the input file

        return None

    def _read_file_contents(self, infname):
        with open(infname) as f:
            return f.read()



class CopyInputDeps(BaseFix):
    r"""
    Copy files referred to by ``\input`` and ``\include`` routines to the output
    directory, and run the full collection of fixes on them.
    """

    def fix_node(self, n, **kwargs):

        if n.isNodeType(LatexMacroNode) and n.macroname in ('input', 'include'):
        
            if not n.nodeargd.argnlist:
                logger.warning(r"Invalid \input/\include directive: ‘%s’, skipping.",
                               n.to_latex())
                return None

            infname = self.preprocess_arg_latex(n, 0)

            ext = ''
            for e in exts:
                if os_path.exists(infname+e):
                    infname = infname+e
                    ext = e
                    break
            else:
                logger.warning("File not found: %s. Tried extensions %r", infname, exts)
                return None # keep the node as it is

            # copy file to output while running our whole selection of fixes on
            # it!  Recurse into a full instantiation of lpp.execute_file().
            self.lpp.execute_file(infname, output_fname=infname)

            return None # don't change the \input directive

        return None
