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
Module that provides a helper for writing fixes that perform macro
substitutions with custom replacement strings.
"""


import logging
logger = logging.getLogger(__name__)

from pylatexenc.macrospec import MacroSpec, EnvironmentSpec, MacroStandardArgsParser
from pylatexenc.latexwalker import LatexMacroNode, LatexEnvironmentNode

from latexpp import fixes


class MacroSubstHelper:
    r"""
    Helper class that provides common functionality for fixes that replace
    certain macro invocations by a custom replacement string.

    TODO: Document me. ....
    """
    def __init__(self,
                 macros={},
                 environments={},
                 argspecfldname='argspec',
                 args_parser_class=MacroStandardArgsParser,
                 context={}):
        self.macros = macros
        self.environments = environments

        self.argspecfldname = argspecfldname
        self.args_parser_class = args_parser_class

        self.context = context # additional fields provided to repl text

    def get_specs(self):
        return dict(
            macros=[
                MacroSpec(m, args_parser=self.args_parser_class(
                    self._cfg_argspec_repl(mconfig)[0]
                ))
                for m, mconfig in self.macros.items()
            ],
            environments=[
                EnvironmentSpec(e, args_parser=self.args_parser_class(
                    self._cfg_argspec_repl(econfig)[0]
                ))
                for e, econfig in self.environments.items()
            ]
        )

    def _cfg_argspec_repl(self, meinfo):
        if isinstance(meinfo, str):
            return '', meinfo
        return meinfo.get(self.argspecfldname, ''), meinfo.get('repl', '')

    def get_macro_cfg(self, macroname):
        if macroname not in self.macros:
            return None
        return dict(zip([self.argspecfldname, 'repl'],
                        self._cfg_argspec_repl(self.macros[macroname])))

    def get_environment_cfg(self, environmentname):
        if environmentname not in self.environments:
            return None
        return dict(zip([self.argspecfldname, 'repl'],
                        self._cfg_argspec_repl(self.environments[environmentname])))

    def get_node_cfg(self, n):
        if n is None:
            return None
        if n.isNodeType(LatexMacroNode):
            return self.get_macro_cfg(n.macroname)
        if n.isNodeType(LatexEnvironmentNode):
            return self.get_environment_cfg(n.environmentname)


    def eval_subst(self, c, n, *, node_contents_latex, argoffset=0, context={}):
        """
        Return the replacement string for the given node `n`, where the
        macro/environment config (argspec/repl) is provided in `c` (return value
        of `get_node_cfg()`).

        You need to specify as `node_contents_latex` a callable that will be
        used to transform child nodes (argument nodes) to LaTeX code.  If you're
        calling this from a fix class (:py:class:`latexpp.fixes.BaseFix`
        subclass) then you should most probably specify
        ``node_contents_latex=self.preprocess_contents_latex`` here.

        If `argoffset` is nonzero, then the first `argoffset` arguments are skipped
        and the arguments `argoffset+1, argoffset+2, ...` are exposed to the
        replacement string as `%(1)s, %(2)s, ...`.

        You can specify a dictionary `context` of additional key/value
        replacement strings in the formatting of the `repl` string.  For
        instance, if ``context={'delimsize': r'\big'}``, then ``%(delimsize)s``
        in the replacement string `repl` is expanded to ``\big``.  This is all
        in addition to the argument placeholders ``%(1)s`` etc., to the
        environment body ``%(body)s``, and to
        ``%(macroname)s``/``%(environmentname)s``.
        """

        _, repl = self._cfg_argspec_repl(c)
            
        q = dict(self.context)

        if n.nodeargd is None or n.nodeargd.argnlist is None:
            raise fixes.DontFixThisNode

        q.update(dict(
                (str(1+k), v)
                for k, v in enumerate(
                        node_contents_latex(n) if n is not None else ''
                        for n in n.nodeargd.argnlist[argoffset:]
                )
            ))

        if n.isNodeType(LatexMacroNode):
            q.update(macroname=n.macroname)
        if n.isNodeType(LatexEnvironmentNode):
            q.update(environmentname=n.environmentname,
                     body=node_contents_latex(n.nodelist))
        
        q.update(context)

        text = repl % q
        #print("*** Performing substitution {} -> {}".format(n.to_latex(), text))
        return text
