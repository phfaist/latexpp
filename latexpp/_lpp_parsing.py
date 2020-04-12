import re
import functools

import logging

from pylatexenc import latexwalker


logger = logging.getLogger(__name__)


def _no_latex_verbatim(*args, **kwargs):
    raise RuntimeError("Cannot use latex_verbatim() because the nodes might change.")


class LatexCodeRecomposer:
    def __init__(self):
        super().__init__()

    def node_to_latex(self, n):
        if n.isNodeType(latexwalker.LatexGroupNode):
            return n.delimiters[0] + "".join(self.node_to_latex(n) for n in n.nodelist) \
                + n.delimiters[1]

        elif n.isNodeType(latexwalker.LatexCharsNode):
            return n.chars

        elif n.isNodeType(latexwalker.LatexCommentNode):
            return '%' + n.comment + n.comment_post_space

        elif n.isNodeType(latexwalker.LatexMacroNode):
            # macro maybe with arguments
            return '\\'+n.macroname+n.macro_post_space + self.args_to_latex(n)

        elif n.isNodeType(latexwalker.LatexEnvironmentNode):
            # get environment behavior definition.
            return (r'\begin{' + n.environmentname + '}' + self.args_to_latex(n) +
                     "".join( self.node_to_latex(n) for n in n.nodelist ) +
                     r'\end{' + n.environmentname + '}')

        elif n.isNodeType(latexwalker.LatexSpecialsNode):
            # specials maybe with arguments
            return n.specials_chars + self.args_to_latex(n)

        elif n.isNodeType(latexwalker.LatexMathNode):
            return n.delimiters[0] + "".join( self.node_to_latex(n) for n in n.nodelist ) \
                + n.delimiters[1]

        else:
            raise ValueError("Unknown node type: {}".format(n.__class__.__name__))
        
    def args_to_latex(self, n):
        if n.nodeargd and hasattr(n.nodeargd, 'args_to_latex'):
            return n.nodeargd.args_to_latex(recomposer=self)
        if n.nodeargd is None or n.nodeargd.argspec is None \
           or n.nodeargd.argnlist is None:
            # no arguments or unknown argument structure
            return ''
        return ''.join( (self.node_to_latex(n) if n else '')
                        for n in n.nodeargd.argnlist )




class _LPPParsingState(latexwalker.ParsingState):
    def __init__(self, lpp_latex_walker, **kwargs):
        super().__init__(**kwargs)
        self.lpp_latex_walker = lpp_latex_walker
        self._fields = tuple(list(self._fields)+['lpp_latex_walker'])



class _LPPLatexWalker(latexwalker.LatexWalker):
    def __init__(self, *args, **kwargs):
        self.lpp = kwargs.pop('lpp')
        super().__init__(*args, **kwargs)

        # for severe debugging
        #self.debug_nodes = True
        
        # add back-reference to latexwalker in all latex nodes, for convenience
        self.default_parsing_state = _LPPParsingState(
            lpp_latex_walker=self,
            **self.default_parsing_state.get_fields()
        )


    def make_node(self, *args, **kwargs):
        node = super().make_node(*args, **kwargs)

        # forbid method latex_verbatim()
        node.latex_verbatim = _no_latex_verbatim

        # add method to_latex() that reconstructs the latex dynamically from the
        # node structure
        node.to_latex = functools.partial(self.node_to_latex, node)

        return node


    def node_to_latex(self, n):
        return LatexCodeRecomposer().node_to_latex(n)


    def pos_to_lineno_colno(self, pos, **kwargs):
        if pos is None:
            return {} if kwargs.get('as_dict', False) else None
        return super().pos_to_lineno_colno(pos, **kwargs)

