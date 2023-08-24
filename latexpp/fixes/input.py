import re
import os.path as os_path # allow tests to monkey-patch this

import logging
logger = logging.getLogger(__name__)

from pylatexenc.latexwalker import LatexMacroNode

from latexpp.fix import BaseFix


input_exts = ['', '.tex', '.latex']

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

    Arguments:
    
    - `usepackage` [optional] specify a list of package names (a ``\usepackage``
      argument) that import a local package file that is assumed to exist in the
      current directory.  The file contents will be included at the location of
      the ``\usepackage`` call.  For example, set
      ``usepacakge=['./mymacros.sty']`` to replace a call to
      ``\usepackage{./mymacros.sty}`` by the contents of ``mymacros.sty``
      (surrounded by ``\makeatletter ... \makeatother``).
    """
    def __init__(self, *, usepackage=None):
        super().__init__()
        self.usepackage = usepackage

    def fix_node(self, n, **kwargs):

        if n.isNodeType(LatexMacroNode) and n.macroname in ('input', 'include'):
        
            if not n.nodeargd.argnlist:
                logger.warning(r"Invalid \input/\include directive: ‘%s’, skipping.",
                               n.to_latex())
                return None

            infname = self.preprocess_arg_latex(n, 0)

            return self.do_input(n, infname, input_exts)

        if (self.usepackage is not None
            and self.usepackage
            and n.isNodeType(LatexMacroNode)
            and n.macroname == 'usepackage'):
            #
            # pick up the usepackage argument
            pkgname = self.preprocess_arg_latex(n, 1) # remember, there's an optional arg
            
            if pkgname in self.usepackage:
                return self.do_input(n, pkgname,
                                     exts=['', '.sty'])

        return None


    def do_input(self, n, infname, exts):

        logger.info("Input ‘%s’", infname)

        for e in exts:
            # FIXME: resolve path relative to main document source
            if os_path.exists(infname+e):
                infname = infname+e
                break
        else:
            logger.warning("File not found: ‘%s’. Tried extensions %r", infname, exts)
            return None # keep the node as it is

        # open that file and go through it, too

        infdata = self._read_file_contents(infname)

        ## we add %\n to the end to avoid having two newlines one after
        ## the other (at end of input file and after \input{}) that could
        ## be misinterpreted as a new paragraph in some settings
        # ### but this is also unreliable. because
        # ### "\\input{foo}\n\\input{bar}" would still include a new
        # ### paragraph.
        #if self.delimit_with_percent:
        #    infdata = '%\n' + infdata + '%\n'

        # for \include, we need to issue \clearpage.  See
        # https://tex.stackexchange.com/a/32058/32188
        if n.macroname == 'include':
            infdata = r'\clearpage' + '\n' + infdata

        # for \usepackage, surround the contents with '\makeatletter
        # .. \makeatother' and remove '\ProvidesPackage'
        if n.macroname == 'usepackage':
            infdata = re.sub(r'\\ProvidesPackage\s*\{[^}]+\}\s*(\[(\{[^}]*\}|[^\]]*)\])?',
                             '', infdata)
            infdata = r'\makeatletter' + '\n' + infdata + r'\makeatother' + '\n'

        # preprocess recursively contents

        try:
            lw = self.lpp.make_latex_walker(infdata)
        except latexwalker.LatexWalkerParseError as e:
            if not e.input_source:
                e.input_source = 'file ‘{}’'.format(infname)
            raise

        nodes = self.preprocess( lw.get_latex_nodes()[0] )
        return nodes # replace the input node by the content of the input file

        #lw = self.lpp.make_latex_walker(infdata)
        #res = self.preprocess_latex( lw.get_latex_nodes()[0] )
        #return res # replace the input node by the content of the input file


    def _read_file_contents(self, infname):
        with self.lpp.open_file(infname) as f:
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

            for e in input_exts:
                if os_path.exists(infname+e):
                    infname = infname+e
                    break
            else:
                logger.warning("File not found: ‘%s’. Tried extensions %r", infname, input_exts)
                return None # keep the node as it is

            logger.info("Preprocessing ‘%s’", infname)

            # copy file to output while running our whole selection of fixes on
            # it!  Recurse into a full instantiation of lpp.execute_file().
            self.lpp.execute_file(infname, output_fname=infname)

            return None # don't change the \input directive

        return None
