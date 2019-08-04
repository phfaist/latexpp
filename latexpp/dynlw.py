
import functools

from pylatexenc import latexwalker


......... DO NOT USE ................



def node_update_changes(n, dosetattr=setattr):

    def add_args(n):
        if n.nodeargd is None or n.nodeargd.argspec is None or n.nodeargd.argnlist is None:
            # no arguments or unknown argument structure
            return ''
        return ''.join( (n.latex_verbatim() if n else '') for n in argnlist )

    if n.isNodeType(latexwalker.LatexGroupNode):
        latex = n.delimiters[0] + "".join(n.latex_verbatim() for n in nodelist) \
            + n.delimiters[1]

    elif n.isNodeType(latexwalker.LatexCharsNode):
        latex = n.chars

    elif n.isNodeType(latexwalker.LatexCommentNode):
        latex = '%' + n.comment + n.comment_post_space

    elif n.isNodeType(latexwalker.LatexMacroNode):
        # macro maybe with arguments
        latex = '\\'+n.macroname+n.macro_post_space + add_args(n)

    elif n.isNodeType(latexwalker.LatexEnvironmentNode):
        # get environment behavior definition.
        latex = (r'\begin{' + n.environmentname + '}' + add_args(n) +
                 "".join( n.verbatim_latex() for n in nodelist ) +
                 r'\end{' + n.environmentname + '}')

    elif n.isNodeType(latexwalker.LatexSpecialsNode):
        # specials maybe with arguments
        latex = n.specials_chars + add_args(n)

    elif n.isNodeType(latexwalker.LatexMathNode):
        latex = n.delimiters[0] + "".join( n.verbatim_latex() for n in nodelist ) \
            + n.delimiters[1]

    else:
        raise ValueError("Unknown node type: {}".format(n.__class__.__name__))

    dosetattr(n, 'parsed_context',
              latexwalker.ParsedContext(
                  s=latex,
                  latex_context=n.parsed_context.latex_context
              ))
    dosetattr(n, 'pos', 0)
    dosetattr(n, 'len', len(latex))
    return

    
def _node_setattr(n, attname, value):
    print('*** {} node attribute {} -> {}, updating node info'
          .format(n.__class__.__name__, attname, value))
    object.__setattr__(n, attname, value)
    node_update_changes(n, dosetattr=object.__setattr__)


class DynNodesLatexWalker(latexwalker.LatexWalker):
    r"""
    A `LatexWalker` that creates nodes that can be modified while still
    retaining valid latex representations.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def make_node(self, node_class, pos, len, **kwargs):
        r"""
        Create and return a node of type `node_class` which holds a representation
        of the latex code at position `pos` and of length `len` in the parsed
        string.

        The node class should be a :py:class:`LatexNode` subclass.

        Keyword arguments are supplied directly to the constructor of the node
        class.

        .. versionadded:: 2.0
        
           This method was introduced in `pylatexenc 2.0` to make it easier to
           ensure that additional fields like `parsed_context` are set correctly
           on the node object.
        """
        print("*** make_node({})".format(node_class))
        node = node_class(parsed_context=self.parsed_context, pos=pos, len=len, **kwargs)
        if self.debug_nodes:
            logger.debug("New node: %r", node)

        # add provision to auto-update latex context if an attribute is modified.
        node.__setattr__ = functools.partial(_node_setattr, node)

        return node

