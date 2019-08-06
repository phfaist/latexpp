
import re

from pylatexenc import latexwalker


# node.comment does not contain first '%' comment char
rx_lpp_pragma = re.compile(r'^%!lpp\s*(?P<instruction>.*?)\s*(?P<openbrace>\{)?$')
rx_lpp_pragma_close = re.compile(r'^%!lpp\s*(?P<closebrace>\})\s*$')

def do_pragmas(nodelist, lpp):
    # we can modify nodelist in place.
    j = 0
    while j < len(nodelist):
        n = nodelist[j]
        if n is not None and n.isNodeType(latexwalker.LatexCommentNode):
            m = rx_lpp_pragma.match(n.comment)
            if m:
                instruction = m.group('instruction')
                if instruction not in pragmas:
                    raise ValueError("Invalid %%!lpp pragma: ‘{}’".format(instruction))
                pragma = pragmas[instruction]()
                if pragma.requires_block():
                    if m.group('openbrace').strip() != '{':
                        raise ValueError("Expected open brace after ‘%%!lpp {}’".format(instruction))
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

    def requires_block(self):
        return True

    def execute(self, nodelist, jstart, jend, *, lpp):
        nodelist[jstart:jend] = []
        return jstart



pragmas = {
    'skip': SkipPragma
}
