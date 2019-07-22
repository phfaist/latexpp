
import logging

logger = logging.getLogger(__name__)

from pylatexenc.macrospec import ParsedMacroArgs, MacroStandardArgsParser
from pylatexenc import latexwalker


# parse `(...)  `[...]  `{ ... }
#       `\big(...)  `\big[...]  ...
#       `*(...)  ...

class PhfParenSpecialsParsedArgs(ParsedMacroArgs):
    def __init__(self, in_math_mode, star_node, size_arg_node, contents_node, **kwargs):
        self.in_math_mode = in_math_mode
        self.has_star = star_node is not None
        self.star_node = star_node # or None
        self.size_arg_node = size_arg_node # or None
        self.contents_node = contents_node

        argnlist = [
            self.star_node,
            self.size_arg_node,
            self.contents_node
        ]

        super(PhfParenSpecialsParsedArgs, self).__init__(argspec='*[{',
                                                         argnlist=argnlist,
                                                         **kwargs)
        

class PhfParenSpecialsArgsParser(MacroStandardArgsParser):
    def __init__(self):
        super(PhfParenSpecialsArgsParser, self).__init__(argspec='*[{')

    def parse_args(self, w, pos, parsing_context=None):

        if parsing_context is None:
            parsing_context = latexwalker.ParsingContext()

        if not parsing_context.in_math_mode:
            return (PhfParenSpecialsParsedArgs(False, None, None, None), pos, 0)

        #logger.debug("*** reading specials args at pos=%d", pos)

        p = pos

        include_brace_chars = [('[', ']'), ('(', ')'), ('<', '>')]

        # check for star
        tok = w.get_token(p, include_brace_chars=include_brace_chars)
        if tok.tok == 'char' and tok.arg.lstrip().startswith('*'):
            # has star
            star_node = w.make_node(latexwalker.LatexCharsNode, chars='*', pos=tok.pos, len=tok.len)
            p = tok.pos + 1
            tok = w.get_token(p, include_brace_chars=include_brace_chars) # prepare next token
        else:
            star_node = None

        # check for size macro
        #tok = w.get_token(p, include_brace_chars=include_brace_chars) # already in tok
        if tok.tok == 'macro':
            # has size macro
            size_arg_node = w.make_node(latexwalker.LatexMacroNode, macroname=tok.arg, nodeargd=None,
                                        pos=tok.pos, len=tok.len)
            p = tok.pos+tok.len
            tok = w.get_token(p, include_brace_chars=include_brace_chars) # prepare next token
        else:
            size_arg_node = None

        #logger.debug("\tp=%r, tok=%r", p, tok)

        
        #tok = w.get_token(p, include_brace_chars=include_brace_chars) # already in tok
        if tok.tok != 'brace_open':
            raise latexwalker.LatexWalkerParseError(
                    s=w.s,
                    pos=p,
                    msg=r"Expecting opening brace after '`'"
                )

        (contents_node, apos, alen) = w.get_latex_braced_group(tok.pos, brace_type=tok.arg,
                                                               parsing_context=parsing_context)

        #logger.debug("*** got phfparen args: %r, %r, %r", star_node, size_arg_node, contents_node)

        return (PhfParenSpecialsParsedArgs(True, star_node, size_arg_node, contents_node),
                pos, apos+alen-pos)
        
