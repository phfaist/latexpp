
import re

from pylatexenc import latexwalker


# node.comment does not contain first '%' comment char
rx_lpp_pragma = re.compile(r'^%!lpp\s*(?P<instruction>.*?)(?P<open-brace>\s*\{)?$')
rx_lpp_pragma_close = re.compile(r'^%!lpp\s*(?P<close-brace>\}\s*)$')

def do_pragmas(nodelist, lpp):
    # we can modify nodelist in place.
    j = 0
    while j < len(nodelist):
        if n is not None and n.isNodeType(latexwalker.LatexCommentNode):
            m = rx_lpp_pragma_n.match(n.comment)
            if m:
                instruction = m.group('instruction')
                if instruction not in pragmas:
                    raise ValueError("Invalid %%!lpp pragma: ‘{}’".format(instruction))
                pragma = pragmas[instruction]
                if pragma.requires_block():
                    if m.group('open-brace').strip() != '{':
                        raise ValueError("Expected open brace after ‘%%!lpp {}’".format(instruction))
                    # scan until we find the matching '}'
                    jstart = j
                    while j < len(nodelist):
                        if n is not None and n.isNodeType(latexwalker.LatexCommentNode):
                            if rx_lpp_pragma_close.match(n.comment):
                                # found closing '}'
                                break
                            if rx_lpp_pragma.match(n.comment):
                                raise ValueError("Nested %%!lpp pragmas are not yet implemented")
                        j += 1
                    else:
                        raise ValueError(
                            "Cannot find closing ‘%%!lpp }’ to match %%!lpp {} on line {}, col {}"
                            .format(instruction,
                                    *nodelist[j].parsed_context.lpp_latex_walker
                                    .pos_to_lineno_colno(nodelist[j].pos))
                        )
                    j = pragma.execute(nodelist, jstart, j, lpp=lpp)
                    continue
                else:
                    j = pragma.execute(nodelist, j, lpp=lpp)
                    continue
        j += 1


class SkipPragma:

    def requires_block(self):
        return True

    def execute(self, nodelist, jstart, jend, lpp=lpp):
        nodelist[jstart:jend] = []
        return jstart



pragmas = {
    'skip': SkipPragma
}
