
import os
import os.path as os_path # allow tests to monkey-patch this

import logging
logger = logging.getLogger(__name__)

from pylatexenc.latexwalker import LatexMacroNode

from latexpp.fixes import BaseFix


def node_get_usepackage(n, fix):
    """
    If `n` is a macro node that is a 'usepackage' directive, then this function
    returns a string with the package name.  Otherwise we return `None`.
    """
    if n.isNodeType(LatexMacroNode) and n.macroname == 'usepackage' and \
       n.nodeargd is not None and n.nodeargd.argnlist is not None:
        # usepackage has signature '[{'
        return fix.node_contents_to_latex(n.nodeargd.argnlist[1]).strip()

    return None


class RemovePkgs(BaseFix):
    r"""
    Remove some instances of ``\usepackage[..]{...}`` for some selected pacage
    names.
    
    Arguments:

    - `pkglist`: List of package names for which we should remove any
      ``\usepackage`` directives.

    .. warning::

       [FIXME]: This does not work if you have ``\usepackage`` directives with
       several packages.  This should be easy to fix...
    """
    def __init__(self, pkglist):
        super().__init__()
        self.pkglist = set(pkglist)

    def fix_node(self, n, **kwargs):

        pkgname = node_get_usepackage(n, self)
        if pkgname is not None and pkgname in self.pkglist:
            logger.debug(r"Removing instruction ‘%s’", n.latex_verbatim())
            return [] # kill entire node

        return None


class CopyLocalPkgs(BaseFix):
    r"""
    Copy package style files that are present in the current directory and that
    are included with ``\usepackage{...}``.

    .. warning::

       [FIXME]: This does not work if you have ``\usepackage`` directives with
       several packages.  This should be easy to fix...
    """
    def __init__(self):
        super().__init__()

    def fix_node(self, n, **kwargs):

        pkgname = node_get_usepackage(n, self)
        if pkgname is not None:
            pkgnamesty = pkgname + '.sty'
            if os_path.exists(pkgnamesty):
                self.lpp.copy_file(pkgnamesty)
                return None # keep node the same

        return None
