
import logging
logger = logging.getLogger(__name__)

from pylatexenc.latexwalker import LatexMacroNode


def node_get_usepackage(n, lpp):
    """
    If `n` is a macro node that is a 'usepackage' directive, then this function
    returns a string with the package name.  Otherwise we return `None`.
    """
    if n.isNodeType(LatexMacroNode) and n.macroname == 'usepackage' and \
       n.nodeargd is not None and n.nodeargd.argnlist is not None:
        # usepackage has signature '[{'
        return lpp.latexpp_group_contents(n.nodeargd.argnlist[1]).strip()

    return None


class Fixes(object):
    def __init__(self, pkglist):
        self.pkglist = set(pkglist)

    def fix_node(self, n, lpp):

        pkgname = node_get_usepackage(n, lpp)
        if pkgname is not None and pkgname in self.pkglist:
            #logger.debug(r"Removing \usepackage{%s}", pkgname)
            return '' # kill entire node

        return None
