
from pylatexenc.latexwalker import LatexMacroNode, LatexEnvironmentNode

from latexpp.macro_subst_helper import MacroSubstHelper

from latexpp.fixes import BaseFix


class Subst(BaseFix):
    r"""
    Define custom macros and environments that will be replaced by associated
    LaTeX code.

    Arguments:
    
      - `macros`: a dictionary of macro substitution rules ``{macroname: minfo,
        ...}``.  The key `macroname` is the macro name without the leading backslash.

        The value `minfo` is a dictionary ``{'argspec': argspec, 'repl':
        repl}``, where `argspec` specifies the argument structure of the macro
        and `repl` is the replacement string.  If `minfo` is a string, then the
        string is interpreted as the `repl` and 'argspec' is set to an empty
        string (no macro arguments).

        The `argspec` is a string of characters '*', '[', or '{' which indicate
        the nature of the macro arguments.  A '*' indicates a corresponding
        optional * in the LaTeX source (starred macro variant); a '[' indicates
        an optional argument delimited in square brackets, and a '{' indicates a
        mandatory argument.  The argument values can be referred to in the
        replacement string `repl` using the syntax '%(n)s' where `n` is the
        argument number, i.e., the index in the argspec string.

        For instance::

              macros={ 'includegraphics': {'argspec': '[{', 'repl': '<%(2)s>'} }

        would replace all ``\includegraphics`` calls by the string
        ``<(filename)>``.  (``\includegraphics`` has an optional argument and a
        mandatory argument.)

        You can also use ``%(macroname)s`` in the `repl` string, which will
        expand to the name of the macro without the leading backslash.

      - `environments`: a dictionary of environment substitution rules
        ``{environmentname: einfo, ...}``.  The key `environmentname` is the
        name of the environment, i.e., what goes as argument to ``\begin{...}``
        and ``\end{...}``.

        The `einfo` is a dictionary ``{'argspec': argspec, 'repl': repl}`` where
        `argspec` specifies the structure of the arguments accepted immediately
        after ``\begin{<environment>}`` (as for ``{ccrl}`` in
        ``\begin{tabular}{ccrl}``).  The `argspec` works exactly like for
        macros.

        The replacement string `repl` works exactly like for macros, with the
        additional substitution key ``%(body)s`` and that can be used to include
        the body of the environment in the replacement string.  (The body is
        itself also preprocessed by latexpp.)

        You can also use ``%(environmentname)s`` in the `repl` string, which
        will expand to the name of the environment.
    """

    def __init__(self, macros={}, environments={}):
        self.helper = MacroSubstHelper(macros, environments)

    def specs(self, **kwargs):
        return dict(**self.helper.get_specs())

    def fix_node(self, n, lpp, **kwargs):

        c = self.helper.get_node_cfg(n)
        if c is not None:
            return self.helper.eval_subst(c, n, lpp)

        return None
