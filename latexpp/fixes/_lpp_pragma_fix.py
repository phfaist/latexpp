
import re
import shlex
import logging

logger = logging.getLogger(__name__)


from pylatexenc import latexwalker

from ._basefix import BaseFix


# node.comment does not contain first '%' comment char
rx_lpp_pragma = re.compile(
    r'^%!(?P<nospace>\s*)lpp\s*(?P<instruction>[\}a-zA-Z_-]+)\s*(?P<rest>.*)$'
)


class PragmaFix(BaseFix):
    def __init__(self):
        super().__init__()
    
    def fix_nodelist(self, nodelist):

        newnodelist = list(nodelist)

        for n in newnodelist:
            self.preprocess_child_nodes(n)

        self._do_pragmas(newnodelist)

        return newnodelist
    
    # override these to implement interesting functionality

    def fix_pragma_scope(self, nodelist, jstart, jend, instruction, args):
        # do not do anything interesting, continue after pragma block. jstart
        # points on start pragma node and jend points *ONE PAST* the closing
        # pragma brace (like a Python range)
        return jend

    def fix_pragma_simple(self, nodelist, j, instruction, args):
        # do not do anything interesting, continue after pragma
        return j+1


    def _do_pragmas(self, nodelist, jstart=0, stop_at_close_scope=False):

        j = jstart

        # we can modify nodelist in place.
        while j < len(nodelist):
            n = nodelist[j]
            md = self._parse_pragma(n)
            if md is None:
                j += 1
                continue

            instruction, rest = md

            args = shlex.split(rest)
            if instruction == '}':
                if stop_at_close_scope:
                    return j
                raise ValueError("Invalid closing pragma ‘%%!lpp }’ encountered "
                                 "at line {}, col {}"
                                 .format(*n.parsing_state.lpp_latex_walker
                                         .pos_to_lineno_colno(n.pos)))
            if args and args[-1] == '{':
                # this is a scope pragma
                j = self._do_scope_pragma(nodelist, j, instruction, args[:-1])
                continue
            else:
                # this is a single simple pragma
                j = self._do_simple_pragma(nodelist, j, instruction, args)
                continue

            j += 1

        if stop_at_close_scope:
            raise ValueError(
                "Cannot find closing ‘%%!lpp }’ to match ‘%%!lpp {}’ on line {}, col {}"
                .format(instruction,
                        *nodelist[jstart].parsing_state.lpp_latex_walker
                        .pos_to_lineno_colno(nodelist[jstart].pos))
            )

        return


    def _parse_pragma(self, node):
        if not node:
            return None
        if not node.isNodeType(latexwalker.LatexCommentNode):
            return None
        m = rx_lpp_pragma.match(node.comment)
        if not m:
            return None
        if m.group('nospace'):
            raise ValueError("LPP Pragmas should start with the exact string '%%!lpp': "
                             "‘{}’ @ line {}, col {}".format(
                                 n.to_latex(),
                                 *n.parsing_state.lpp_latex_walker
                                 .pos_to_lineno_colno(n.pos)
                             ))
        return m.group('instruction'), m.group('rest')
        
    def _do_scope_pragma(self, nodelist, j, instruction, args):
        
        # scan for closing pragma, parsing other pragmas on the way.
        jclose = self._do_pragmas(nodelist, j+1, stop_at_close_scope=True)

        # then fix this scope pragma
        jnew = self.fix_pragma_scope(nodelist, j, jclose+1, instruction, args)

        if jnew is None:
            raise RuntimeError(
                "Fix dealing with scope pragma ‘%%!lpp {}’ did not report new j position"
                .format( instruction )
            )

        return jnew

    def _do_simple_pragma(self, nodelist, j, instruction, args):

        jnew = self.fix_pragma_simple(nodelist, j, instruction, args)

        if jnew is None:
            raise RuntimeError(
                "Fix dealing with simple pragma ‘%%!lpp {}’ did not report new j position"
                .format( instruction )
            )

        return jnew



class ReportRemainingPragmas(PragmaFix):
    
    def fix_pragma_scope(self, nodelist, jstart, jend, instruction, args):
        n = nodelist[jstart]
        ne = nodelist[jend-1]
        logger.warning(
            "Found unconsumed pragma ‘%s’, did you forget to invoke a fix? "
            "on lines %d--%d (?)",
            n.comment,
            n.parsing_state.lpp_latex_walker.pos_to_lineno_colno(n.pos)[0],
            ne.parsing_state.lpp_latex_walker.pos_to_lineno_colno(ne.pos)[0]
        )

    def fix_pragma_simple(self, nodelist, j, instruction, args):
        n = nodelist[j]
        logger.warning(
            "Found unconsumed pragma ‘%s’, did you forget to invoke a fix? "
            "on line %d (?)",
            n.comment,
            n.parsing_state.lpp_latex_walker.pos_to_lineno_colno(n.pos)[0]
        )

