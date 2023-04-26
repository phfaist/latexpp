import re
import logging

logger = logging.getLogger(__name__)

from pylatexenc.macrospec import MacroSpec, EnvironmentSpec, SpecialsSpec, \
    ParsedMacroArgs, MacroStandardArgsParser, LatexContextDb
from pylatexenc import latexwalker

#from latexpp.macro_subst_helper import MacroSubstHelper

from latexpp.fix import BaseFix

from .._lpp_parsing import LatexCodeRecomposer





# FIXME: This module should be COMPLETELY REWRITTEN WITH THE NEW PYLATEXENC 3
# PARSING FEATURES !!!!




# ==============================================================================


# special identifiers to use as tokens in ncargspec -- internal actually
class NCArgMacroName:
    pass

class NCArgBracedTokens:
    pass

class NCDefArgsSignature:
    pass


class NCNewMacroDefinition(ParsedMacroArgs):
    def __init__(self, nc_what, ncmacrotype, ncargspec, argnlist, **kwargs):
        self.nc_what = nc_what # 'macro' or 'environment'
        self.ncmacrotype = ncmacrotype
        self.ncargspec = ncargspec

        self.new_defined_macrospec = None
        self.new_defined_environmentospec = None
        self.macro_replacement_toknode = None
        self.endenv_replacement_toknode = None

        super().__init__(argspec="".join('?' for x in argnlist),
                         argnlist=argnlist,
                         **kwargs)
        
    def __repr__(self):
        return "{}(ncmacrotype={!r}, ncargspec={!r}, argnlist={!r})".format(
            self.__class__.__name__, self.ncmacrotype, self.ncargspec, self.argnlist
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




def _get_string_arg(arg_node, msg):
    if arg_node.isNodeType(latexwalker.LatexCharsNode):
        return arg_node.chars
    if arg_node.isNodeType(latexwalker.LatexGroupNode):
        if len(arg_node.nodelist) == 1 and \
           arg_node.nodelist[0].isNodeType(latexwalker.LatexCharsNode):
            return arg_node.nodelist[0].chars
    #
    raise ValueError(msg)


class MacroStandardArgsParserForNewcommand(MacroStandardArgsParser):
    def __init__(self, nc_defined_command, macroname, num_args,
                 optional_first_arg_default_node):
        self.num_args = num_args
        self.optional_first_arg_default_node = optional_first_arg_default_node
        argspec = '{' * num_args
        if self.optional_first_arg_default_node is not None:
            # default first argument
            argspec = '[' + argspec[1:]
        # instantiate superclass with this argspec.
        super().__init__(argspec)

        self.nc_defined_command = nc_defined_command
        self.nc_macroname = macroname

    def parse_args(self, w, pos, parsing_state=None):
        logger.debug("encountered custom-defined %s", self.nc_macroname)
        ptuple = super().parse_args(w, pos, parsing_state=parsing_state)

        parsed_args_instance = ptuple[0]

        parsed_args_instance.nc_defined_command = self.nc_defined_command
        # use default first value, if applicable, but then also instruct the
        # parsed_args not to include it in recomposed LaTeX code
        if self.argspec[0:1] == '[' and parsed_args_instance.argnlist and \
           parsed_args_instance.argnlist[0] is None:
            #
            parsed_args_instance.argnlist[0] = self.optional_first_arg_default_node
            parsed_args_instance.nc_is_default_first_arg = True

            def new_args_to_latex(recomposer):
                # do the node-to-latex for argnlist[1:], skipping the first
                # optional, non-specified parameter (see "if" above)
                return ''.join( (recomposer.node_to_latex(n) if n else '')
                                for n in parsed_args_instance.argnlist[1:] )

            parsed_args_instance.args_to_latex = new_args_to_latex
            
        return ptuple



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

    - `ncmacrotype` should be the newcommand-type macro name.  One of
    'newcommand', 'newenvironment', [TODO: add more, e.g. DeclareDocumentCommand
    ?, DeclareMathDelimiters ?, etc.]
    """
    def __init__(self, ncmacrotype):
        self.ncmacrotype = ncmacrotype
        super().__init__(argspec=None)

    def parse_args(self, w, pos, parsing_state=None):

        orig_pos = pos

        new_add_context_defs = {}

        if self.ncmacrotype == 'newcommand':
            (new_macro_def, pos, len_) = \
                self.nc_parse_args(
                    'macro',
                    ['*', NCArgMacroName, '[', '[', NCArgBracedTokens],
                    w, pos, parsing_state=parsing_state
                )
            pos = pos + len_

            # Note: We treat all 'newcommand'-type macros the same way
            # (\newcommand, \renewcommand, \providecommand).  E.g., if the macro
            # was \providecommand, we don't check if the command is already
            # defined.  This would be way too sketchy; how would we know if the
            # command was already defined in some obscure section of some random
            # package?  I say, let the user explicitly specify they want
            # replacement of \providecommand definitions, and they can blacklist
            # any ones which are in fact already defined.
            
            num_args = 0
            if new_macro_def.argnlist[2] is not None:
                num_args = int(_get_string_arg(new_macro_def.argnlist[2],
                                               "Expected number of arguments ‘[X]’ for argument of {}"
                                               .format(self.ncmacrotype)))
            first_default_value_node = new_macro_def.argnlist[3]

            macroname = new_macro_def.argnlist[1]._ncarg_the_macro_name

            args_parser = MacroStandardArgsParserForNewcommand(new_macro_def, macroname,
                                                               num_args, first_default_value_node)

            new_macro_def.new_defined_macrospec = MacroSpec(macroname, args_parser=args_parser)
            new_macro_def.macro_replacement_toknode = new_macro_def.argnlist[4]

            # update the parsing state --- FIXME NEED BETTER INTERFACE IN
            # PYLATEXENC.  Should be able to modify in place the LatexContextDb....right?
            m = new_macro_def.new_defined_macrospec
            #parsing_state.latex_context.d['_lpp-custom-newcommands']['macros'][m.macroname] = m

            new_add_context_defs['macros'] = [ m ]

            logger.debug("New command defined: {} {} -> {}"
                         .format(m.macroname,
                                 new_macro_def.args_to_latex(LatexCodeRecomposer()),
                                 new_macro_def.macro_replacement_toknode.to_latex()))

            new_def = new_macro_def

        elif self.ncmacrotype == 'newenvironment':

            (new_env_def, pos, len_) = \
                self.nc_parse_args(
                    'environment',
                    ['*', '{', '[', '[', NCArgBracedTokens, NCArgBracedTokens],
                    w, pos, parsing_state=parsing_state
                )
            pos = pos + len_

            num_args = 0
            if new_env_def.argnlist[2] is not None:
                num_args = int(_get_string_arg(new_env_def.argnlist[2],
                                               "Expected number of arguments ‘[X]’ for argument of {}"
                                               .format(self.ncmacrotype)))
            first_default_value_node = new_env_def.argnlist[3]

            environmentname = _get_string_arg(new_env_def.argnlist[1],
                                              "Expected simple environment name ‘{{environment}}’ "
                                              "for argument of {}".format(self.ncmacrotype))

            args_parser = MacroStandardArgsParserForNewcommand(
                new_env_def, r'\begin{%s}'%(environmentname),
                num_args, first_default_value_node
            )

            new_env_def.new_defined_environmentspec = EnvironmentSpec(environmentname,
                                                                      args_parser=args_parser)
            new_env_def.macro_replacement_toknode = new_env_def.argnlist[4]
            new_env_def.endenv_replacement_toknode = new_env_def.argnlist[5]

            # update the parsing state --- FIXME NEED BETTER INTERFACE IN
            # PYLATEXENC.  Should be able to modify in place the LatexContextDb....right?
            e = new_env_def.new_defined_environmentspec
            #ddcat = parsing_state.latex_context.d['_lpp-custom-newcommands']
            #ddcat['environments'][e.environmentname] = e
            new_add_context_defs['environments'] = [ e ]

            logger.debug("New environment defined: {} / {}"
                         .format(e.environmentname,
                                 new_env_def.args_to_latex(LatexCodeRecomposer())))

            new_def = new_env_def

        else:

            raise ValueError("Unknown macro definition command type: {}".format(self.ncmacrotype))

        #logger.debug("latex context is now\n%r", parsing_state.latex_context.d)

        # tag on the new parsing state modification in the returned information
        new_parsing_state = parsing_state.sub_context(
            latex_context=parsing_state.latex_context.extended_with(
                **new_add_context_defs
            )
        )

        mdic = {
            'new_parsing_state': new_parsing_state
        }

        return (new_def, orig_pos, pos - orig_pos, mdic)

    def nc_parse_args(self, nc_what, ncargspec, w, pos, parsing_state=None):

        if parsing_state is None:
            parsing_state = w.make_parsing_state()

        # prepare a parsing state where no macros are known, they are all to be
        # kept as single tokens.  The argument placeholder # is recognized as
        # "special".
        toks_latex_context = LatexContextDb() # completely empty context.
        toks_latex_context.set_unknown_macro_spec(MacroSpec(''))
        toks_latex_context.set_unknown_environment_spec(EnvironmentSpec(''))
        toks_latex_context.set_unknown_specials_spec(SpecialsSpec(''))
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

        new_def = NCNewMacroDefinition(
            nc_what=nc_what,
            ncmacrotype=self.ncmacrotype,
            ncargspec=ncargspec,
            argnlist=argnlist,
        )

        return (new_def, pos, p-pos)




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
    Detect custom macro and environment definitions in the preamble and apply
    them throughout the document.

    This fix detects custom macros and environments, for instance:

    .. code-block:: latex
    
        \newcommand\calE{\mathcal{E}}
        \newcommand\mycomments[1]{\textcolor{red}{#1}}
        \newcommand\myket[2][\big]{#1|{#2}#1\rangle} % \ket{\psi}, \ket[\Big]{\psi}
        \newenvironment{boldtext}{\bfseries}{}

    This fix then detects their use throughout the LaTeX document and replaces
    them with their respective substitutions.  Macro and environment arguments
    are processed as you would expect.

    By default, the corresponding ``\newcommand`` instructions are removed from
    the preamble.  If you'd like to keep them even though they have been
    substituted throughout the document, specify `leave_newcommand=True`.

    You can blacklist some macro name patterns and environment name patterns, so
    that any macro or environment whose name matches a pattern does not get
    expanded (and its definition is not removed from the preamble).  Use the
    arguments `macro_blacklist_patterns` and `environment_blacklist_patterns`
    for this.

    By default, the instructions ``\newcommand`` and ``\newenvironment`` are
    detected, while the instructions ``\renewcommand``, ``\providecommand``,
    ``\renewenvironment`` are ignored.  If you would like to also replace
    commands re-defined with those instructions, specify `newcommand_cmds` (see
    below).

    .. note::

       The rationale for not substituting commands defined with
       ``\renewcommand`` and ``\providecommand`` (and same for environments) is
       that such commands are often used to redefined LaTeX special commands,
       such as counters or formatting instructions.  For instance:

       .. code-block:: latex

           \renewcommand{\thepage}{- \roman{page} -} % page numbering format
           \renewcommand{\familydefault}{\sfdefault} % sans serif font
           \providecommand{\selectlanguage}[1]{} % babel dummy drop-in

       These (re-)defined commands should generally not be substituted by this
       fix, because they are not used in the document main text but rather, they
       are used by the LaTeX engine.  Especially, if we removed their
       (re-)definition their effect would disappear entirely (page numbers would
       revert to defaults, etc.).  This is certainly not the intended effect.

    .. warning::

       If you opt to add ``renewcommand`` and/or ``providecommand`` to the
       argument `newcommand_cmds`, be aware that they are treated exactly like
       ``\newcommand``.  That is, they do not check whether the macro is already
       defined (`latexpp` cannot know if a macro was defined somewhere deep in a
       package).  In particular, ``\providecommand`` *always* defines the
       command if this command is enabled via `newcommand_cmds`.

    When substituting environments, the full environment is further enclosed
    within a LaTeX group delimited by braces '{' ... '}' (this is because LaTeX
    actually does create a TeX group for the environment contents).  But you can
    change this if you like using the arguments `envbody_begin` and
    `envbody_end`.

    Arguments:

    - `leave_newcommand`: Set this to True to leave all macro and environment
      definition instructions (e.g., ``\newcommand``) in the preamble even if we
      substituted their replacements throughout the document.  If False (the
      default), then we remove macro and environment definitions in the preamble
      for which we have carried out substitutions throughout the document.

      Definitions of blacklisted macros/environments and to definitions using
      instructions that are not in `newcommand_cmds` are always left in place,
      regardless of the `leave_newcommand` argument.

    - `newcommand_cmds`: The type of LaTeX command definition instructions to
      pay attention to.  This should be a list containing one or more elements
      in `('newcommand', 'renewcommand', 'providecommand', 'newenvironment',
      'renewenvironment')`
    
      (In the future, I might add support for other definition instructions such
      as ``\DeclareRobustCommand``, or ``\DeclarePairedDelimiter`` [from the
      `mathtools` package].  Adding support for ``\def`` would be more involved,
      let's see.)

      By default, only ``\newcommand`` and ``\newenvironment`` are observed.
      (See rationale and warning above for ignoring ``\renewcommand`` etc. by
      default)

    - `macro_blacklist_patterns`, `environment_blacklist_patterns`: These
      arguments may be set to a list of regular expressions that specify which
      macro definitions and environment definitions should not be acted upon by
      this fix.  Any regular expressions recognized by python's `re` module may
      be employed.  If a macro (respectively an environment) matches any of the
      patterns in the respective blacklist, then they are left unchanged in the
      document and the definitions are left in the preamble unaltered.

      For instance, if you use the fix configuration:

      .. code-block:: yaml

           - name: 'latexpp.fix.newcommand'
             config:
               newcommand_cmds: ['newcommand', 'renewcommand', 'newenvironment']
               macro_blacklist_patterns: ['^the', 'blablabla$']

      then instructions such as
      ``\renewcommand{\theequation}{\roman{equation}}`` (or any definition of a
      macro whose name starts with "the" or that ends with "blablabla") would be
      left as-is in the output, and similarly any occurrences of
      ``\theequation`` in the document (should there be any) would be left
      unaltered.

      (You could use the blacklist pattern ``^the`` as in this particular
      example to identify redefinitions of formatting of LaTeX counters, but
      then all macros that begin with "the" would not be substituted, and for
      instance ``\newcommand{\therefore}{...}`` would not be replaced.)

    - `envbody_begin`, `envbody_end`: When expanding environments, the entire
      replacement LaTeX code is wrapped by these two strings.  By default,
      `envbody_begin='{'` and `envbody_end='}'`, such that all expansions of
      environments are enclosed within a LaTeX group.  You may specify any other
      prefixes and postfixes here (e.g. ``\begingroup`` and ``\endgroup`` or
      empty strings to avoid creating a LaTeX group).

      Placing the environment contents in a group imitates what LaTeX itself
      does.  If you don't put the contents in a group, you might change the
      resulting document output (for instance, if you have an ``\itshape``
      inside the environment, the group would ensure the italic text doesn't
      continue outside of the environment).
    """
    
    def __init__(self, *,
                 leave_newcommand=False, newcommand_cmds=None,
                 macro_blacklist_patterns=None,
                 environment_blacklist_patterns=None,
                 envbody_begin='{', envbody_end='}'):
        self.leave_newcommand = leave_newcommand
        if newcommand_cmds is None:
            self.newcommand_cmds = ('newcommand', 'newenvironment',)
        else:
            self.newcommand_cmds = newcommand_cmds
        if macro_blacklist_patterns:
            self.macro_blacklist_patterns = [
                re.compile(x) for x in macro_blacklist_patterns
            ]
        else:
            self.macro_blacklist_patterns = [ ]
        if environment_blacklist_patterns:
            self.environment_blacklist_patterns = [
                re.compile(x) for x in environment_blacklist_patterns
            ]
        else:
            self.environment_blacklist_patterns = [ ]

        self.envbody_begin = envbody_begin
        self.envbody_end = envbody_end

        super().__init__()

    def specs(self, **kwargs):
        mm = [
            MacroSpec('newcommand', args_parser=NCArgsParser('newcommand')),
            MacroSpec('renewcommand', args_parser=NCArgsParser('newcommand')),
            MacroSpec('providecommand', args_parser=NCArgsParser('newcommand')),
            MacroSpec('newenvironment', args_parser=NCArgsParser('newenvironment')),
            MacroSpec('renewenvironment', args_parser=NCArgsParser('newenvironment')),
        ]

        return dict(macros=(m for m in mm if m.macroname in self.newcommand_cmds))


    def fix_node(self, n, **kwargs):

        if n.isNodeType(latexwalker.LatexMacroNode):
            #logger.debug("Fixing node %s, its context is %r", n, n.parsing_state.latex_context.d)

            if n.macroname in self.newcommand_cmds:
                if self.leave_newcommand:
                    return None
                if not isinstance(n.nodeargd, NCNewMacroDefinition):
                    logger.warning("Encountered ‘%s’ but it wasn't parsed correctly by us ...",
                                   n.macroname)
                    logger.debug("n.nodeargd = %r", n.nodeargd)
                    return None
                # see if macro name was blacklisted by an exclusion pattern
                if (n.nodeargd.nc_what == 'macro' and
                    self._is_name_blacklisted(n.nodeargd.new_defined_macrospec.macroname,
                                              self.macro_blacklist_patterns)) or \
                   (n.nodeargd.nc_what == 'environment' and
                    self._is_name_blacklisted(n.nodeargd.new_defined_environmentspec.environmentname,
                                              self.environment_blacklist_patterns)):
                    # blacklisted -- leave unchanged
                    return None
                logger.debug("Removing ‘%s’ for %s ‘%s’", n.macroname, n.nodeargd.nc_what,
                             getattr(n.nodeargd, 'new_defined_'+n.nodeargd.nc_what+'spec'))
                return [] # remove new macro definition -- won't need it any longer
                          # after all text replacements :)

            if n.nodeargd is not None and hasattr(n.nodeargd, 'nc_defined_command'):
                # this command was parsed by a MacroSpec generated automatically
                # by a \newcommand (or sth).  If it's not blacklisted, replace
                # it with its body substitution
                if self._is_name_blacklisted(n.macroname, self.macro_blacklist_patterns):
                    return None
                return self.subst_macro(n)


        if n.isNodeType(latexwalker.LatexEnvironmentNode):
            #logger.debug("Fixing node %s, its context is %r", n, n.parsing_state.latex_context.d)

            if n.nodeargd is not None and hasattr(n.nodeargd, 'nc_defined_command'):
                # this command was parsed by a EnvironmentSpec generated
                # automatically by a \newenvironment (or sth).  If it's not
                # blacklisted, replace it with its body substitution
                if self._is_name_blacklisted(n.environmentname, self.environment_blacklist_patterns):
                    return None
                return self.subst_environment(n)
            

        return  None

    def _is_name_blacklisted(self, name, blacklist_patterns):
        m = next(filter(lambda x: x is not None,
                        (rx.search(name) for rx in blacklist_patterns)), None)
        if m is not None:
            # matched one blacklist pattern
            return True
        return False


    def subst_environment(self, n):
        
        logger.debug("subst_environment: %r", n)

        new_env_definition = n.nodeargd.nc_defined_command # the NCNewMacroDefinition instance

        # strategy : recurse only *after* having recomposed & expanded values,
        # so that fixes get applied to the macro body definition and that any
        # interplay between body defs and arguments might even work.  (And it's
        # closer to what LaTeX does.)

        beginenv = new_env_definition.macro_replacement_toknode
        endenv = new_env_definition.endenv_replacement_toknode
        recomposer = \
            LatexMacroReplacementRecomposer([
                self._arg_contents_to_latex(x)
                for x in n.nodeargd.argnlist
            ])

        replacement_latex = \
            self.envbody_begin + \
            "".join(recomposer.node_to_latex(n) for n in beginenv.nodelist) + \
            "".join(nn.to_latex() for nn in n.nodelist) + \
            "".join(recomposer.node_to_latex(n) for n in endenv.nodelist) + \
            self.envbody_end

        # now, re-parse into nodes and re-run fix (because the macro was
        # expanded, we're not risking infinite recursion unless the environment
        # expanded into itself)

        logger.debug("Got environment replacement_latex = %r", replacement_latex)

        nodes = self.parse_nodes(replacement_latex, n.parsing_state)
        #logger.debug("Got new nodes = %r", nodes)

        return self.preprocess(nodes)


    def subst_macro(self, n):
        
        logger.debug("subst_macro: %r", n)

        # generate some warnings if we're substituting a macro name that looks
        # like we shouldn't be -- e.g., a counter
        if n.macroname.startswith("the"):
            logger.warning("Substituting macro ‘{}’ (replacement LaTeX ‘{}’); it looks like "
                           "a LaTeX counter though — if you don't mean to substitute it use "
                           "the `macro_blacklist_patterns` argument to blacklist it.")
        
        new_macro_definition = n.nodeargd.nc_defined_command # the NCNewMacroDefinition instance

        # strategy : recurse only *after* having recomposed & expanded values,
        # so that fixes get applied to the macro body definition and that any
        # interplay between body defs and arguments might even work.  (And it's
        # closer to what LaTeX does.)

        body = new_macro_definition.macro_replacement_toknode
        recomposer = \
            LatexMacroReplacementRecomposer([
                self._arg_contents_to_latex(x)
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

    def _arg_contents_to_latex(self, x):
        if x is None:
            return ""
        if x.isNodeType(latexwalker.LatexGroupNode):
            return "".join(y.to_latex() for y in x.nodelist)
        return x.to_latex()
        


