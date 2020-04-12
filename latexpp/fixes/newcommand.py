import re
import yaml
import logging

logger = logging.getLogger(__name__)

from pylatexenc.macrospec import MacroSpec, SpecialsSpec, \
    ParsedMacroArgs, MacroStandardArgsParser, LatexContextDb
from pylatexenc import latexwalker

from latexpp.macro_subst_helper import MacroSubstHelper

from latexpp.fix import BaseFix

from .._lpp_parsing import LatexCodeRecomposer


# ==============================================================================


# special identifiers to use as tokens in ncargspec -- internal actually
class NCArgMacroName:
    pass

class NCArgBracedTokens:
    pass

class NCDefArgsSignature:
    pass


class NCNewMacroDefinition(ParsedMacroArgs):
    def __init__(self, ncmacroname, ncargspec, argnlist, **kwargs):
        self.ncmacroname = ncmacroname
        self.ncargspec = ncargspec

        self.new_defined_macrospec = None
        self.body_replacement_toknode = None

        super().__init__(argspec="".join('?' for x in argnlist),
                         argnlist=argnlist,
                         **kwargs)
        
    def __repr__(self):
        return "{}(ncmacroname={!r}, ncargspec={!r}, argnlist={!r})".format(
            self.__class__.__name__, self.ncmacroname, self.ncargspec, self.argnlist
        )

    def args_to_latex(self, recomposer):
        return "".join(self._arg_to_latex(at, an, recomposer)
                       for at, an in zip(self.ncargspec, self.argnlist))

    def _arg_to_latex(self, argt, argn, recomposer):
        if argn is None:
            return ''

        if argt in ('{','[','*'):
            return recomposer.node_to_latex(argn)
        elif argt is NCArgMacroName:
            # should be the simple macro name, no macro args of course
            return recomposer.node_to_latex(argn)
        elif argt is NCArgBracedTokens:
            return recomposer.node_to_latex(argn)
        elif argt is NCDefArgsSignature:
            return recomposer.node_to_latex(argn) # stored as a group node w/ no delimiters
        
        raise RuntimeError("Invalid argt={!r} (argn={!r})".format(argt, argn))
    

# class DefToksArgsParser(MacroStandardArgsParser):
#     """
#     Parse arguments according to a sequence of tokens specified in a ``\def``
#     instruction.
#     """
#     def __init__(self, def_toks):
#         self.def_toks = def_toks
#         super().__init__(argspec=None)
#
#     def parse_args(self, w, pos, parsing_state=None):
#
#         orig_pos = pos
#
#         argnlist = []
#
#         for dtok in def_toks:
#
#             if dtok.tok == 'specials' and dtok.arg.specials_chars == '#':
#
#                 # argument placeholder -- read argument
#
#                 (n, p2, l2) = w.get_latex_expression(pos, parsing_state=parsing_state)
#
#                 pos = p2 + l2
#                 argnlist.append(n)
#
#             else:
#
#                 ........ need to read *DELIMITED ARGUMENT* ...............
#
#                 while True: # might have to skip comments
#
#                     tok = w.get_token(pos, environments=False, parsing_state=parsing_state)
#                     p = tok.pos + tok.len
#
#                     if tok.tok == 'comment':
#                         continue
#
#                     break
#
#                 if tok.tok != dtok.tok:
#                     raise latexwalker.LatexWalkerParseError(
#                         "Parse error in macro arguments: expected ‘{}’, got ‘{}’"
#                         .format(dtok.tok, tok.tok)
#                     )
#
#                 if tok.tok in ('char', 'macro', 'mathmode_inline', 'mathmode_inline'):
#                     if tok.arg != dtok.arg:
#                         raise latexwalker.LatexWalkerParseError(
#                             "Parse error in macro arguments: expected ‘{}’ but got ‘{}’"
#                             .format(dtok.arg, tok.arg)
#                         )
#                 elif tok.tok == 'specials':
#                     if tok.arg.specials_chars != dtok.arg.specials_chars:
#                         raise latexwalker.LatexWalkerParseError(
#                             "Parse error in macro arguments: expected ‘{}’, got ‘{}’ instead"
#                             .format(dtok.arg.specials_chars, tok.arg.specials_chars)
#                         )
#
#         parsed.args_to_latex = lambda (self): ...........\
#                 return "".join(self._arg_to_latex(at, an)
#                        for at, an in zip(self.ncargspec, self.argnlist))




class NCArgsParser(MacroStandardArgsParser):
    r"""
    Args parser for ``\newcommand/\def`` statements that define new macros.

    This is a bit awkward for `pylatexenc`, because `pylatexenc` is really a
    markup parser that by design isn't meant to dynamically change itself while
    parsing.

    Do this class does more than "parse arguments of ``\newcommand``".  It also
    notifies a parent object of the new macro.  It also tells `pylatexenc` to
    alter the current `parsing_state` to include the newly defined macro.

    Arguments:

    - `ncmacroname` should be the newcommand-type macro name.  One of
    'newcommand', 'renewcommand', 'def', [TODO: add more,
    e.g. DeclareRobustCommand, DeclareMathDelimiters, etc.]
    """
    def __init__(self, ncmacroname):
        self.ncmacroname = ncmacroname
        super().__init__(argspec=None)

    def parse_args(self, w, pos, parsing_state=None):

        orig_pos = pos

        if self.ncmacroname in ('newcommand', 'renewcommand', 'providecommand'):
            (new_macro_def, pos, len_) = \
                self.nc_parse_args(['*', NCArgMacroName, '[', '[', NCArgBracedTokens],
                                   w, pos, parsing_state=parsing_state)
            pos = pos + len_ 
            
            num_args = 0
            if new_macro_def.argnlist[2] is not None:
                if (not new_macro_def.argnlist[2].isNodeType(latexwalker.LatexGroupNode) or \
                    len(new_macro_def.argnlist[2].nodelist) != 1 or \
                    not new_macro_def.argnlist[2].nodelist[0].isNodeType(latexwalker.LatexCharsNode)):
                    #
                    raise ValueError("Expected number of arguments ‘[X]’ for argument of {}"
                                     .format(self.ncmacroname))
                num_args = int(new_macro_def.argnlist[2].nodelist[0].chars)
            argspec = '{' * num_args
            first_default_value = None
            if new_macro_def.argnlist[3] is not None:
                # default first argument
                argspec = '[' + argspec[1:] 
                first_default_value = new_macro_def.argnlist[3].to_latex()

            macroname = new_macro_def.argnlist[1]._ncarg_the_macro_name

            args_parser = MacroStandardArgsParser(argspec)
            args_parser.nc_defined_command = new_macro_def
            old_parse_args = args_parser.parse_args
            def new_parse_args(w, pos, parsing_state=None):
                logger.debug("encountered custom-defined command %s", macroname)
                ptuple = old_parse_args(w, pos, parsing_state=parsing_state)
                ptuple[0].nc_defined_command = new_macro_def
                return ptuple
            args_parser.parse_args = new_parse_args

            new_macro_def.new_defined_macrospec = MacroSpec(macroname, args_parser=args_parser)
            new_macro_def.body_replacement_toknode = new_macro_def.argnlist[4]

        else:
            raise ValueError("Unknown macro definition command type: {}".format(self.ncmacroname))

        # update the parsing state --- FIXME NEED BETTER INTERFACE IN
        # PYLATEXENC.  Should be able to modify in place the LatexContextDb....right?
        if '_lpp-custom-newcommands' not in parsing_state.latex_context.d:
            parsing_state.latex_context.add_context_category('_lpp-custom-newcommands', prepend=True)
        m = new_macro_def.new_defined_macrospec
        parsing_state.latex_context.d['_lpp-custom-newcommands']['macros'][m.macroname] = m

        logger.debug("New command defined: {} {} -> {}"
                     .format(m.macroname,
                             new_macro_def.args_to_latex(LatexCodeRecomposer()),
                             new_macro_def.body_replacement_toknode.to_latex()))

        #logger.debug("latex context is now\n%r", parsing_state.latex_context.d)

        # tag on the new parsing state modification in the returned information
        mdic = {
            'new_parsing_state': parsing_state
        }

        return (new_macro_def, orig_pos, pos - orig_pos, mdic)

    def nc_parse_args(self, ncargspec, w, pos, parsing_state=None):

        if parsing_state is None:
            parsing_state = w.make_parsing_state()

        # prepare a parsing state where no macros are known, they are all to be
        # kept as single tokens.  The argument placeholder # is recognized as
        # "special".
        toks_latex_context = LatexContextDb() # completely empty context.
        #empty_latex_context.set_unknown_macro_spec(MacroSpec(''))
        #empty_latex_context.set_unknown_environment_spec(EnvironmentSpec(''))
        #empty_latex_context.set_unknown_specials_spec(SpecialsSpec(''))
        toks_latex_context.add_context_category(
            'arg_placeholder',
            specials=[
                # single argument, will be 1...9|#
                SpecialsSpec('#', args_parser=MacroStandardArgsParser('{'))
            ]
        )
        toks_parsing_state = parsing_state.sub_context(
            latex_context=toks_latex_context
        )

        argnlist = []

        p = pos

        for argt in ncargspec:

            if argt in ('{', '[', '*'):

                (stdpa, np, nl) = \
                    MacroStandardArgsParser(argt).parse_args(w, p, parsing_state=parsing_state)
                assert len(stdpa.argnlist) == 1
                p = np + nl
                argnlist.append(stdpa.argnlist[0])

            elif argt is NCArgMacroName:

                (node, nodepos, nodelen) = \
                    w.get_latex_expression(p, parsing_state=toks_parsing_state)

                if node.isNodeType(latexwalker.LatexMacroNode):
                    node._ncarg_the_macro_name = node.macroname
                elif node.isNodeType(latexwalker.LatexGroupNode):
                    if len(node.nodelist) != 1 or \
                       not node.nodelist[0].isNodeType(latexwalker.LatexMacroNode):
                        raise latexwalker.LatexWalkerParseError(
                            "Expected single LaTeX command name as argument, got ‘{}’"
                            .format(node.to_latex())
                        )
                    node._ncarg_the_macro_name = node.nodelist[0].macroname
                else:
                    raise latexwalker.LatexWalkerParseError(
                        "Unexpected argument ‘{}’, was expecting a single LaTeX command"
                        .format(node.to_latex())
                    )

                p = nodepos + nodelen
                argnlist.append(node)

            elif argt is NCArgBracedTokens:

                tok = w.get_token(p, environments=False, parsing_state=toks_parsing_state)
                if tok.tok != 'brace_open':
                    raise latexwalker.LatexWalkerError(
                        "Expected open brace ‘{’ for LaTeX definition body, got ‘%s’"
                        %(tok.tok),
                    )

                # ok, we indeed have an open brace s

                (node, nodepos, nodelen) = \
                    w.get_latex_braced_group(tok.pos, brace_type='{',
                                             parsing_state=toks_parsing_state)

                p = nodepos + nodelen
                argnlist.append(node)

            # elif argt is NCDefArgsSignature:

            #     def_args_sig_pos = p

            #     def_toks = []

            #     while True:
            #         tok = w.get_token(p, environments=False, parsing_state=toks_parsing_state)

            #         if tok.tok == 'brace_open':
            #             break

            #         if tok.tok == 'comment':
            #             # still skip comments
            #             continue

            #         p = tok.pos + tok.len
            #         def_toks.append(tok)

            #     # keep the definition string as a chars node-- but that's really
            #     # just a plain placeholder that will only be used when we need
            #     # to convert the argument back to LaTeX code.
            #     node = w.make_node(latexwalker.LatexCharsNode,
            #                        parsing_state=toks_parsing_state,
            #                        chars=w.s[def_args_sig_pos:p],
            #                        pos=def_args_sig_pos, len=p - def_args_sig_pos)
            #     # the real, useful information however is stored in a custom
            #     # attribute that we set on the node
            #     node._ncarg_def_toks = def_toks

            #     argnlist.append( node )

            else:
                raise latexwalker.LatexWalkerError(
                    "Unknown macro argument kind for macro: {!r}".format(argt)
                )

        new_macro_def = NCNewMacroDefinition(
            ncmacroname=self.ncmacroname,
            ncargspec=ncargspec,
            argnlist=argnlist,
        )
        
        # store the newly defined macro into the actual LaTeX context so that it
        # is new_macro_def correctly in the rest of the document.
        

        return (new_macro_def, pos, p-pos)




# ------------------------------------------------------------------------------

class LatexMacroReplacementRecomposer(LatexCodeRecomposer):
    def __init__(self, replacement_strings):
        super().__init__()
        self.replacement_strings = replacement_strings

    def node_to_latex(self, n):
        if n.isNodeType(latexwalker.LatexSpecialsNode) and \
           n.specials_chars == '#':
            if not n.nodeargd.argnlist[0].isNodeType(latexwalker.LatexCharsNode):
                raise ValueError("Got something other than a character node after #: {}"
                                 .foramt(n.nodeargd.argnlist[0]))
            if n.nodeargd.argnlist[0].chars == '#':
                return '#' # single hash as replacement of "##"
            repl_num = int(n.nodeargd.argnlist[0].chars)
            return self.replacement_strings[repl_num-1] # repl_num counts from 1
        
        return super().node_to_latex(n)



# ==============================================================================

class Expand(BaseFix):
    r"""
    Detect custom macro definitions in the preamble and apply them throughout
    the document.
    """
    
    def __init__(self, leave_newcommand=True):
        self.leave_newcommand = leave_newcommand
        self.newcommand_cmds = ('newcommand',)
        super().__init__()

    def specs(self, **kwargs):
        mm = [
            MacroSpec('newcommand', args_parser=NCArgsParser('newcommand')),
            MacroSpec('renewcommand', args_parser=NCArgsParser('renewcommand')),
        ]

        return dict(macros=(m for m in mm if m.macroname in self.newcommand_cmds))


    def fix_node(self, n, **kwargs):

        if n.isNodeType(latexwalker.LatexMacroNode):

            #logger.debug("Fixing node %s, its context is %r", n, n.parsing_state.latex_context.d)

            if n.macroname in self.newcommand_cmds:
                if self.leave_newcommand:
                    return None
                return [] # remove new macro definition -- won't need it any longer
                          # after all text replacements :)

            if n.nodeargd is not None and hasattr(n.nodeargd, 'nc_defined_command'):
                # this command was parsed by a MacroSpec generated automatically
                # by a \newcommand (or sth) -- try to replace it with body substitution
                return self.subst_macro(n)

        return  None

    def subst_macro(self, n):
        
        logger.debug("subst_macro: %r", n)
        
        new_macro_definition = n.nodeargd.nc_defined_command # the NCNewMacroDefinition instance

        # strategy : recurse only *after* having recomposed & expanded values,
        # so that fixes get applied to the macro body definition and that any
        # interplay between body defs and arguments might even work.  (And it's
        # closer to what LaTeX does.)

        body = new_macro_definition.body_replacement_toknode
        recomposer = \
            LatexMacroReplacementRecomposer([
                ("".join(y.to_latex() for y in x.nodelist)
                 if x.isNodeType(latexwalker.LatexGroupNode)
                 else x.to_latex())
                for x in n.nodeargd.argnlist
            ])
        replacement_latex = "".join(recomposer.node_to_latex(n) for n in body.nodelist)


        # now, re-parse into nodes and re-run fix (because the macro was
        # expanded, we're not risking infinite recursion unless the macro
        # expanded into itself)

        logger.debug("Got replacement_latex = %r", replacement_latex)

        nodes = self.parse_nodes(replacement_latex, n.parsing_state)
        #logger.debug("Got new nodes = %r", nodes)

        return self.preprocess(nodes)

        


