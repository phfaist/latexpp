
import logging

logger = logging.getLogger(__name__)

from pylatexenc.macrospec import SpecialsSpec, ParsedMacroArgs, MacroStandardArgsParser
from pylatexenc import latexwalker

from latexpp.fix import BaseFix


class Expand(BaseFix):
    r"""
    Expand expressions provided by the {phfparen} package, such as ```*(...)``
    or ```{...}``, into equivalent LaTeX code that does not require the
    {phfparen} package.

    This fix removes the dependency on the
    {phfparen} package.  (That is, unless you defined custom delimiters etc. via
    {phfparen} internals or if you did other weird stuff like that...)

    Arguments:

    - `wrap_in_latex_group`: If set to true (false by default), then the delimited
      math contents is wrapped in a ``{...}`` group.  This prevents line breaks
      within the delimited expression, as is the case when you use the `phfparen`
      latex package.
    """

    def __init__(self, wrap_in_latex_group=False):
        super().__init__()

        self.wrap_in_latex_group = wrap_in_latex_group


    def specs(self, **kwargs):
        return dict(specials=[
            SpecialsSpec('`', args_parser=PhfParenSpecialsArgsParser())
        ])

    def fix_node(self, n, **kwargs):

        if n.isNodeType(latexwalker.LatexSpecialsNode) and n.specials_chars == '`':

            #print("*** `specials-paren node: ", n)
            if not n.nodeargd.in_math_mode:
                # not in math mode, leave as is
                return None

            if n.nodeargd.has_star:
                delims_pc = (r'\mathopen{}\left%s', r'\right%s\mathclose{}')
            elif n.nodeargd.size_arg_node is not None:
                sizemacro = '\\'+n.nodeargd.size_arg_node.macroname
                delims_pc = (sizemacro+r'l%s', sizemacro+r'r%s')
            else:
                delims_pc = ('%s', '%s')

            if n.nodeargd.contents_node is None:
                # this is normal, happens for ` not in math mode
                raise ValueError("`(special) construct does not have contents_node: {!r}"
                                 .format(n.to_latex()))

            delimchars = n.nodeargd.contents_node.delimiters

            if delimchars == ('{', '}'):
                # literal braces if given with curly braces
                delimchars = (r'\{', r'\}')

            inner_replaced_str = self.preprocess_latex(n.nodeargd.contents_node.nodelist)

            if self.wrap_in_latex_group:
                inner_replaced_str = '{' + inner_replaced_str + '}'

            replaced_str = delims_pc[0]%delimchars[0] \
                + inner_replaced_str \
                + delims_pc[1]%delimchars[1]

            return replaced_str

        return None





# parse `(...)  `[...]  `{ ... }
#       `\big(...)  `\big[...]  ...
#       `*(...)  ...

class PhfParenSpecialsParsedArgs(ParsedMacroArgs):
    def __init__(self, check_math_mode_node, star_node, size_arg_node, contents_node, **kwargs):
        self.check_math_mode_node = check_math_mode_node
        self.in_math_mode = check_math_mode_node is not None
        self.has_star = star_node is not None
        self.star_node = star_node # or None
        self.size_arg_node = size_arg_node # or None
        self.contents_node = contents_node

        argnlist = [
            self.check_math_mode_node, # simulate additional macro to remember
                                       # that we had originally detected math
                                       # mode
            self.star_node,
            self.size_arg_node,
            self.contents_node
        ]

        super(PhfParenSpecialsParsedArgs, self).__init__(argspec='[*[{',
                                                         argnlist=argnlist,
                                                         **kwargs)
        

class PhfParenSpecialsArgsParser(MacroStandardArgsParser):
    def __init__(self):
        super(PhfParenSpecialsArgsParser, self).__init__(argspec='[*[{')

    def parse_args(self, w, pos, parsing_state=None):

        if parsing_state is None:
            parsing_state = w.make_parsing_state()

        # check for magic token that tells us that we are in fact, in math mode.
        # Needed for repeated text->nodes->text->nodes->... conversion where the
        # 'in_math_mode' of the parsing_state is not reliable when we are
        # parsing an inner snippet
        #
        # ### UPDATE IN PYLATEXENC: This should no longer be needed
        p = pos
        tok = w.get_token(p)
        force_math_mode = False
        if tok.tok == 'macro' and tok.arg == 'phfparenInMathMode':
            force_math_mode = True
            p = tok.pos + tok.len

        if not force_math_mode and not parsing_state.in_math_mode:
            logger.debug("Ignoring '`' not in math mode: line %d, col %d",
                         *w.pos_to_lineno_colno(pos))
            return (PhfParenSpecialsParsedArgs(None, None, None, None), pos, 0)

        #logger.debug("*** reading specials args at pos=%d", pos)

        include_brace_chars = [('[', ']'), ('(', ')'), ('<', '>')]

        # check for star
        tok = w.get_token(p, include_brace_chars=include_brace_chars)
        if tok.tok == 'char' and tok.arg.lstrip().startswith('*'):
            # has star
            star_node = w.make_node(latexwalker.LatexCharsNode,
                                    parsing_state=parsing_state,
                                    chars='*', pos=tok.pos, len=tok.len)
            p = tok.pos + 1
            tok = w.get_token(p, include_brace_chars=include_brace_chars) # prepare next token
        else:
            star_node = None

        # check for size macro
        #tok = w.get_token(p, include_brace_chars=include_brace_chars) # already in tok
        if tok.tok == 'macro':
            # has size macro
            size_arg_node = w.make_node(latexwalker.LatexMacroNode,
                                        parsing_state=parsing_state,
                                        macroname=tok.arg, nodeargd=None,
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
                                                               parsing_state=parsing_state)

        #logger.debug("*** got phfparen args: %r, %r, %r", star_node, size_arg_node, contents_node)

        check_math_mode_node = w.make_node(latexwalker.LatexMacroNode,
                                           parsing_state=parsing_state,
                                           macroname='phfparenInMathMode',
                                           nodeargd=None,
                                           pos=pos,len=0)

        return (PhfParenSpecialsParsedArgs(check_math_mode_node, star_node,
                                           size_arg_node, contents_node),
                pos, apos+alen-pos)
        
