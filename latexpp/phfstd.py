import sys
import os.path
import logging
import importlib

import yaml

from . import LatexPreprocessor

from pylatexenc.macrospec import MacroSpec, EnvironmentSpec, SpecialsSpec, std_macro
from pylatexenc.latexwalker import LatexNode, LatexMacroNode, LatexEnvironmentNode, \
    LatexSpecialsNode, LatexCommentNode, LatexMathNode
from pylatexenc import latexwalker

logger = logging.getLogger(__name__)


class LatexPP_phfstd(LatexPreprocessor):

    def __init__(self, lppconfig, **kwargs):
        super().__init__(**kwargs)

        for fixconfig in lppconfig['fixes']:
            if isinstance(fixconfig, str):
                fixconfig = {'name': fixconfig}

            modname, clsname = fixconfig['name'].rsplit('.', maxsplit=1)

            mod = importlib.import_module(modname)
            cls = mod.__dict__[clsname]

            self.install_fix(cls(**fixconfig.get('config', {})))


if __name__ == "__main__":

    try:

        logging.basicConfig(level=logging.DEBUG)

        import argparse

        parser = argparse.ArgumentParser()

        parser.add_argument('fname', metavar='file',
                            help='input file name, master LaTeX document file')

        parser.add_argument('-o', '--output-dir',
                            dest='output_dir',
                            default=None,
                            help='output directory (overrides setting from config file)')

        parser.add_argument('--output-fname', dest='output_fname',
                            default=None,
                            help='output file name in output directory (overrides '
                            'setting from config file)')

        args = parser.parse_args()


        with open('lppconfig.yml') as f:
            lppconfig = yaml.load(f, Loader=yaml.FullLoader)

        output_dir = lppconfig.get('output_dir', '_latexpp_output')
        if args.output_dir:
            output_dir = args.output_dir

        fname = lppconfig.get('fname', None)
        if args.fname:
            fname = args.fname

        output_fname = lppconfig.get('output_fname', 'main.tex')
        if args.output_fname:
            output_fname = args.output_fname

        pp = LatexPP_phfstd(
            lppconfig=lppconfig,
            output_dir=output_dir,
            main_doc_fname=fname,
            main_doc_output_fname=output_fname
        )

        pp.execute_main()


    except Exception as e:
        import traceback
        traceback.print_exc()
        import pdb
        pdb.post_mortem()
        sys.exit(255)
