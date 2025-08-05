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
        r"""
        Return the specs that we need to declare to the latex walker
        """
        macros = [
            MacroSpec(m, args_parser=self.args_parser_class(
                self._cfg_argspec_repl(mconfig)[0]
            ))
            for m, mconfig in self.macros.items()
        ]
        return dict(
            macros=macros,
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
        r"""
        Return the config associated with the macro named `macroname`, or `None`.

        You can use this function to test whether a given macro can be
        handled by us, testing the return value for non-`None` and using the
        return value directly as the relevant config for
        :py:meth:`eval_subst()`.
        """
        if macroname not in self.macros:
            return None
        return dict(zip([self.argspecfldname, 'repl'],
                        self._cfg_argspec_repl(self.macros[macroname])))

    def get_environment_cfg(self, environmentname):
        r"""
        Return the config associated with the environment named `environmentname`,
        or `None`.

        You can use this function to test whether a given environment can be
        handled by us, testing the return value for non-`None` and using the
        return value directly as the relevant config for
        :py:meth:`eval_subst()`.
        """
        if environmentname not in self.environments:
            return None
        return dict(zip([self.argspecfldname, 'repl'],
                        self._cfg_argspec_repl(self.environments[environmentname])))

    def get_node_cfg(self, n):
        r"""
        Return the config associated with the macro/environment of the given node
        `n`, or `None`.

        You can use this function to test whether a given node can be handled by
        us, testing the return value for non-`None` and using the return value
        directly as the relevant config for :py:meth:`eval_subst()`.
        """
        if n is None:
            return None
        if n.isNodeType(LatexMacroNode):
            return self.get_macro_cfg(n.macroname)
        if n.isNodeType(LatexEnvironmentNode):
            return self.get_environment_cfg(n.environmentname)
        return None


    def eval_subst(self, c, n, *, node_contents_latex, argoffset=0, context={},
                   arg_filters=None):
        r"""
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

        If `arg_filters` is not None and set to a dictionary, then additional
        placeholders of the type ``%(1.xyz)`` are also recognized, where `xyz`
        are keys in the `arg_filters` dictionary.  The values in the
        `arg_filters` dictionary are functions that take the keyword arguments
        `argspec`, `node`, `arg_index` (0-based index), `arg_number`
        (placeholder number), and `arg_contents` (string representing the
        contents of the argument, as would be used if no filter were invoked),
        and return the replacement string should this placeholder and filter be
        used.
        """

        argspec, repl = self._cfg_argspec_repl(c)

        # TODO: use a lazy dictionary that will only evaluate the values if the
        # placeholder is actually used.
            
        q = _LazySubstDict(self.context)

        if argspec and (n.nodeargd is None or n.nodeargd.argnlist is None):
            logger.debug("Node arguments were not set, skipping replacement: %r", n)
            raise fixes.DontFixThisNode

        if n.nodeargd and n.nodeargd.argnlist:
            for k, nn in enumerate(n.nodeargd.argnlist[argoffset:]):
                if nn is None:
                    arg_contents = ''
                else:
                    arg_contents = node_contents_latex(nn)

                q[str(1+k)] = arg_contents

                if arg_filters:
                    for filterkey, filterfn in arg_filters.items():
                        q.register_fn(
                            str(1+k)+'.'+filterkey,
                            filterfn,
                            dict(
                                argspec=argspec[k],
                                arg_index=k,
                                arg_number=1+k,
                                node=nn,
                                arg_contents=arg_contents,
                            ),
                            allow_args=True,
                        )
                            

        if n.isNodeType(LatexMacroNode):
            q.update(macroname=n.macroname)
        if n.isNodeType(LatexEnvironmentNode):
            q.update(environmentname=n.environmentname,
                     body=node_contents_latex(n.nodelist))
        
        q.update(context)

        try:
            text = repl % q
        except KeyError as e:
            logger.error(
                ("Substitution failed (KeyError {}):\n"
                 "    {} -> {}  (with keys {!r})\n"
                 "node = {!r}").format(
                str(e),
                n.to_latex(),
                repl,
                q,
                n)
            )
            raise
                

        #logger.debug(" -- Performing substitution {} -> {}".format(n.to_latex(), text))
        return text



class _LazySubstDict:
    def __init__(self, d):
        self.d = d
        self.fns = []

    def update(self, *args, **kwargs):
        self.d.update(*args, **kwargs)

    def register_fn(self, keyfn, filterfn, argsfn, allow_args=True):
        self.fns.append( (keyfn, filterfn, argsfn, allow_args) )

    def __setitem__(self, key, value):
        self.d[key] = value

    def __getitem__(self, key):
        if key in self.d:
            return self.d[key]

        for keyfn, filterfn, argsfn, allow_args in self.fns:
            if key == keyfn:
                substarg = None
            elif allow_args and key.startswith(keyfn+':'):
                substarg = key[len(keyfn+':'):]
            else:
                continue

            kwargs = dict(argsfn)
            if substarg is not None:
                kwargs['substarg'] = substarg
            return filterfn(**kwargs)
            
        
