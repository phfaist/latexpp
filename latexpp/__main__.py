import os
import os.path
import re
import sys
import importlib
import logging
logger = logging.getLogger(__name__)

import yaml


from .preprocessor import LatexPreprocessor


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

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

    parser.add_argument('-v', '--verbose', dest='verbosity', default=logging.INFO,
                        action='store_const', const=logging.DEBUG,
                        help='Verbose mode')

    args = parser.parse_args(argv)

    logging.basicConfig(level=args.verbosity)


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

    pp = LatexPreprocessor(
        output_dir=output_dir,
        main_doc_fname=fname,
        main_doc_output_fname=output_fname
    )

    for fixconfig in lppconfig['fixes']:
        if isinstance(fixconfig, str):
            fixconfig = {'name': fixconfig}

        modname, clsname = fixconfig['name'].rsplit('.', maxsplit=1)

        mod = importlib.import_module(modname)
        cls = mod.__dict__[clsname]

        pp.install_fix(cls(**fixconfig.get('config', {})))

    pp.execute_main()


def run_main():

    try:

        main()

    except Exception as e:
        import traceback
        traceback.print_exc()
        import pdb
        pdb.post_mortem()
        sys.exit(255)


if __name__ == "__main__":

    run_main() # easier to debug

    # main()
