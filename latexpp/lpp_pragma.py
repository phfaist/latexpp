# The MIT License (MIT)
#
# Copyright (c) 2019 Philippe Faist
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

r"""
The API design for this module is far from final, don't rely on it.  This
whole module could change without notice.
"""

ERROR---ENTIRE FILE IS OBSOLETE


import logging
logger = logging.getLogger(__name__)

import re

from pylatexenc import latexwalker


# node.comment does not contain first '%' comment char
rx_lpp_pragma = re.compile(r'^%!(?P<nospace>\s*)lpp\s*(?P<instruction>[a-z]+)\s*(?P<pragma_args>.*?)\s*(?P<openbrace>\{)?$')
rx_lpp_pragma_close = re.compile(r'^%!(?P<nospace>\s*)lpp\s*(?P<closebrace>\})\s*$')


## Implemented using fix helpers, *but this is not a proper Fix class!!!*

from .fixes import BaseFix


class _LppPragmaFix(BaseFix):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def fix_nodelist(self, nodelist):
        newnodelist = list(nodelist)
        _do_pragmas(newnodelist, self.lpp)
        for n in newnodelist:
            self.preprocess_child_nodes(n)
        return newnodelist


def _do_pragmas(nodelist, lpp):
    # we can modify nodelist in place.
    j = 0
    while j < len(nodelist):
        n = nodelist[j]
        if n is not None and n.isNodeType(latexwalker.LatexCommentNode):
            m = rx_lpp_pragma.match(n.comment)
            if m:
                if m.group('nospace'):
                    raise ValueError("LPP Pragmas should start with the exact string '%%!lpp': "
                                     "‘{}’ @ line {}, col {}".format(
                                         n.to_latex(),
                                         *n.parsing_state.lpp_latex_walker
                                         .pos_to_lineno_colno(n.pos)
                                     ))
                instruction = m.group('instruction')
                if instruction not in pragmas:
                    raise ValueError("Invalid %%!lpp pragma: ‘{}’".format(instruction))
                pragma = pragmas[instruction](lpp=lpp, pragma_args=m.group('pragma_args'))
                if pragma.requires_block():
                    if m.group('openbrace').strip() != '{':
                        raise ValueError("Expected open brace after ‘%%!lpp {}’"
                                         .format(instruction))
                    # scan until we find the matching '}'
                    jstart = j
                    j += 1
                    while j < len(nodelist):
                        nn = nodelist[j]
                        if nn is not None and nn.isNodeType(latexwalker.LatexCommentNode):
                            if rx_lpp_pragma_close.match(nn.comment):
                                # found closing '}'
                                break
                            if rx_lpp_pragma.match(nn.comment):
                                raise ValueError("Nested %%!lpp pragmas are not yet implemented")
                        j += 1
                    else:
                        raise ValueError(
                            "Cannot find closing ‘%%!lpp }’ to match %%!lpp {} on line {}, col {}"
                            .format(instruction,
                                    *nodelist[j].parsing_state.lpp_latex_walker
                                    .pos_to_lineno_colno(nodelist[j].pos))
                        )
                    # j still points on '}' comment node, pass j+1 like a python range
                    j = pragma.execute(nodelist, jstart, j+1, lpp=lpp)
                    continue
                else:
                    j = pragma.execute(nodelist, j, lpp=lpp)
                    continue

        j += 1


class SkipPragma:

    def __init__(self, **kwargs):
        super().__init__()

    def requires_block(self):
        return True

    def execute(self, nodelist, jstart, jend, *, lpp):
        logger.debug("‘%%%%!lpp skip’ applied from lines %d to %d",
                     nodelist[jstart].parsing_state.lpp_latex_walker
                     .pos_to_lineno_colno(nodelist[jstart].pos)[0],
                     nodelist[jend].parsing_state.lpp_latex_walker
                     .pos_to_lineno_colno(nodelist[jend].pos-1)[0])

        nodelist[jstart:jend] = []
        return jstart



pragmas = {
    'skip': SkipPragma
}
