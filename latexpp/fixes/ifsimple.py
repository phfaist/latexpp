import logging
logger = logging.getLogger(__name__)

from pylatexenc.macrospec import MacroSpec
from pylatexenc.latexwalker import LatexMacroNode

from latexpp.fix import BaseFix


class ApplyIf(BaseFix):
    r"""
    Very simplistic parser for `\ifXXX...\else...\fi` structures in a document.

    .. note::

       This "parser" is much more rudimentary than TeX's offering.  Your
       document might compile fine but this fix might choke on it.

       The main difference is that here, all if-else-fi commands must occur
       within the same logical block (e.g., group or environment).  The code
       ``\iftrue {\bfseries \else {\itshape \fi contents}`` will not work for
       instance, even if it works in TeX, because it interleaves braced groups
       with the if structure.

    This fix is aware of a few built-in ``\ifXXX`` commands (``\iftrue``,
    ``\iffalse``, etc.) and attempts to detect custom ifs declared with
    ``\newif``.  Provide any additional ``\ifXXX`` command names using the
    `ifnames` argument.
    """
    def __init__(self, ifnames=None):
        super().__init__()
        self.ifnames = {'iftrue': True, 'iffalse': False}
        if ifnames:
            self.ifnames.update(ifnames)
        self.ifswitchnames = {}

    def specs(self):
        return dict(macros=[
            MacroSpec('newif', '{')
        ])

    def fix_nodelist(self, nodelist, **kwargs):

        newnodelist = []

        # walk through node list and apply and if-else-fi's
        pos = 0
        while pos < len(nodelist):

            n = nodelist[pos]
            if n.isNodeType(LatexMacroNode) and n.macroname == 'newif':
                # remember new if declaration
                ifbasename = get_newif_ifbasename(n)
                if ifbasename is not None:
                    self.ifnames['if'+ifbasename] = False
                    self.ifswitchnames[ifbasename+'true'] = ('if'+ifbasename, True)
                    self.ifswitchnames[ifbasename+'false'] = ('if'+ifbasename, False)
                    logger.debug(r"new conditional: ‘\if{}’".format(ifbasename))

                # drop the 'newif' node itself.
                pos += 1
                continue

            if n.isNodeType(LatexMacroNode) and n.macroname in self.ifnames:
                # apply if!
                try:
                    poselse, posfi = self.find_matching_elsefi(nodelist, pos+1)
                except ValueError as e:
                    logger.warning(r"Can't find matching ‘\else’/‘\fi’ for ‘\{}’: {!r}: {}"
                                   .format(n.macroname, n, e))
                    continue

                if self.ifnames[n.macroname]:
                    # keep "If" branch, recurse to apply any inner "if"'s
                    posend = poselse if poselse is not None else posfi
                    newnodelist += self.preprocess(nodelist[pos+1:posend])
                elif poselse is not None:
                    # keep "Else" branch, recurse to apply any inner "if"'s
                    newnodelist += self.preprocess(nodelist[poselse+1:posfi])
                #else: drop this entire if block.

                pos = posfi + 1
                continue

            if n.isNodeType(LatexMacroNode) and n.macroname in self.ifswitchnames:
                
                (ifname, value) = self.ifswitchnames[n.macroname]
                self.ifnames[ifname] = value

                pos += 1
                continue

            # copy any other node as is to the new node list.  Make sure to
            # process its children.
            self.preprocess_child_nodes(nodelist[pos])
            newnodelist.append(nodelist[pos])
            pos += 1

        return newnodelist


    def find_matching_elsefi(self, nodelist, p):
        stack_if_counter = 0
        pos_else = None
        while p < len(nodelist):
            if nodelist[p].isNodeType(LatexMacroNode):
                if nodelist[p].macroname in self.ifnames:
                    stack_if_counter += 1
                    p += 1
                    continue
                if nodelist[p].macroname == 'else':
                    if stack_if_counter == 0:
                        pos_else = p
                        p += 1
                        continue
                elif nodelist[p].macroname == 'fi':
                    if stack_if_counter > 0:
                        stack_if_counter -= 1
                        p += 1
                        continue
                    return pos_else, p
            p += 1

        raise ValueError("No matching ‘\fi’ found")


def get_newif_ifbasename(n):
    if not n.nodeargd or not n.nodeargd.argnlist or len(n.nodeargd.argnlist) < 1:
        logger.warning(r"Cannot parse ‘\newif’ declaration, no argument: {!r}".format(n))
        return None
                    
    narg = n.nodeargd.argnlist[0]
    if not narg.isNodeType(LatexMacroNode):
        logger.warning(r"Cannot parse ‘\newif’ declaration, expected single "
                       r"macro argument: {!r}".format(n))
        return None

    ifname = narg.macroname
    if not ifname.startswith('if'):
        logger.warning(r"Cannot parse ‘\newif’ declaration, new \"if\" name "
                       r"does not begin with ‘if’: {!r}".format(n))
        return None

    return ifname[2:]
