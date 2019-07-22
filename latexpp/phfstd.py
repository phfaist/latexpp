import sys
import os.path
import logging

from . import LatexDocumentPreprocessor

from pylatexenc.macrospec import MacroSpec, EnvironmentSpec, SpecialsSpec , std_macro
from pylatexenc.latexwalker import LatexNode, LatexMacroNode, LatexEnvironmentNode, \
    LatexSpecialsNode, LatexCommentNode, LatexMathNode
from pylatexenc import latexwalker

logger = logging.getLogger(__name__)


from .parsinglib import phfparen
from .parsinglib import phfqit

my_specials = [
    SpecialsSpec('`', args_parser=phfparen.PhfParenSpecialsArgsParser())
]


mathtools_delims_macros = {
    'abs': (r'\lvert ', r'\rvert '),
    'norm': (r'\lVert ', r'\rVert '),
    'avg': (r'\langle ', r'\rangle '),
}
my_macros = [
    std_macro('abs', '*[{'),
    std_macro('norm', '*[{'),
    std_macro('avg', '*[{'),
]


class LatexPP_phfstd(LatexDocumentPreprocessor):

    def __init__(self, **kwargs):

        self.phfqit_fixes = phfqit.Fixes()

        latex_context = latexwalker.get_default_latex_context_db()
        latex_context.add_context_category('phfstd', macros=my_macros, specials=my_specials,
                                           prepend=True)
        latex_context.add_context_category('phfqit', macros=self.phfqit_fixes.iter_macro_specs())
        latexwalker_kwargs = {
            'tolerant_parsing': False,
            'latex_context': latex_context
        }
        super().__init__(latexwalker_kwargs=latexwalker_kwargs, **kwargs)

    def latexpp_node(self, node):

        if node is None:
            return ""

        l = self.phfqit_fixes.fix_node(node, self.latexpp)
        if l is not None:
            return l

        if node.isNodeType(LatexCommentNode):
            # sys.stderr.write("Ignoring comment: '%s'\n"% node.comment)
            return "%"+node.comment_post_space

        if node.isNodeType(LatexSpecialsNode) and node.specials_chars == '`':
            if node.nodeargd.has_star:
                delims_pc = (r'\mathopen{}\left%s', r'\right%s\mathclose{}')
            elif node.nodeargd.size_arg_node is not None:
                sizemacro = '\\'+node.nodeargd.size_arg_node.macroname
                delims_pc = (sizemacro+r'l%s', sizemacro+r'r%s')
            else:
                delims_pc = ('%s', '%s')

            delimchars = node.nodeargd.contents_node.delimiters

            if delimchars == ('{', '}'):
                # literal braces if given with curly braces
                delimchars = (r'\{', r'\}')

            return delims_pc[0]%delimchars[0] + self.latexpp(node.nodeargd.contents_node.nodelist) \
                + delims_pc[1]%delimchars[1]
                
        if node.isNodeType(LatexMacroNode) and node.macroname in mathtools_delims_macros:
            if node.nodeargd.argnlist[0] is not None:
                delims_pc = (r'\mathopen{}\left%s', r'\right%s\mathclose{}')
            elif node.nodeargd.argnlist[1] is not None:
                sizemacro = '\\'+node.nodeargd.argnlist[1].nodelist[0].macroname
                delims_pc = (sizemacro+r'l%s', sizemacro+r'r%s')
            else:
                delims_pc = ('%s', '%s')

            delimchars = mathtools_delims_macros[node.macroname]

            if node.nodeargd.argnlist[2].isNodeType(latexwalker.LatexGroupNode):
                contents_n = node.nodeargd.argnlist[2].nodelist
            else:
                contents_n = node.nodeargd.argnlist[2]

            return delims_pc[0]%delimchars[0] + self.latexpp(contents_n) \
                + delims_pc[1]%delimchars[1]
                

        return super().latexpp_node(node)


if __name__ == "__main__":

    try:

        logging.basicConfig(level=logging.DEBUG)

        import argparse

        parser = argparse.ArgumentParser()

        parser.add_argument('file', help='input file name')

        parser.add_argument('-o',
                            dest='latexpp_output',
                            default='_latexpp_output.tex',
                            help='output directory')

        args = parser.parse_args()

        pp = LatexPP_phfstd(fname=args.file)

        res = pp.execute()

    except Exception as e:
        import traceback
        traceback.print_exc()
        import pdb
        pdb.post_mortem()
        sys.exit(255)

    assert(not os.path.exists(args.latexpp_output))

    with open(args.latexpp_output, 'w') as f:
        f.write(res)
        f.write('\n')
