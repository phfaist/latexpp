import logging
logger = logging.getLogger(__name__)

from pylatexenc.macrospec import MacroSpec, EnvironmentSpec, MacroStandardArgsParser
from pylatexenc.latexwalker import LatexMacroNode, LatexEnvironmentNode


class MacroSubstHelper:
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
        If `argoffset` is nonzero, then the first `argoffset` arguments are skipped
        and the arguments `argoffset+1, argoffset+2, ...` are exposed to the
        replacement string as `%(1)s, %(2)s, ...`.
        """

        _, repl = self._cfg_argspec_repl(c)
            
        q = dict(self.context)

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
        #logger.debug("Performing substitution %s -> %s", n.to_latex(), text)
        return text
