import sys
import os.path
import logging

from . import LatexPreprocessor

from pylatexenc.macrospec import MacroSpec, EnvironmentSpec, SpecialsSpec , std_macro
from pylatexenc.latexwalker import LatexNode, LatexMacroNode, LatexEnvironmentNode, \
    LatexSpecialsNode, LatexCommentNode, LatexMathNode
from pylatexenc import latexwalker

logger = logging.getLogger(__name__)


from .fixes.pkg import phfparen
from .fixes.pkg import phfqit
from .fixes import removecomments
from .fixes import figures
from .fixes import input_replace


class LatexPP_phfstd(LatexPreprocessor):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.install_fix(removecomments.Fixes())
        self.install_fix(input_replace.Fixes())
        self.install_fix(figures.Fixes())
        self.install_fix(phfqit.QitObjectFixes())
        self.install_fix(phfqit.MacrosFixes())
        self.install_fix(phfparen.Fixes())



if __name__ == "__main__":

    try:

        logging.basicConfig(level=logging.DEBUG)

        import argparse

        parser = argparse.ArgumentParser()

        parser.add_argument('file', help='input file name')

        parser.add_argument('-o', '--output-dir',
                            dest='output_dir',
                            default='_latexpp_output',
                            help='output directory')

        parser.add_argument('--output-fname', dest='output_fname',
                            default='main.tex',
                            help='output file name (in output directory)')

        args = parser.parse_args()

        pp = LatexPP_phfstd(output_dir=args.output_dir)

        pp.execute(fname=args.file, output_fname=args.output_fname)


    except Exception as e:
        import traceback
        traceback.print_exc()
        import pdb
        pdb.post_mortem()
        sys.exit(255)
