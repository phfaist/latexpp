import os
import os.path
import re
import sys
import importlib
import argparse
import logging
logger = logging.getLogger(__name__)

import yaml

from . import __version__ as version_str


_LPPCONFIG_DOC_URL = 'https://github.com/phfaist/latexpp/blob/master/README.rst'
_LATEXPP_QUICKSTART_DOC_URL = 'https://github.com/phfaist/latexpp/blob/master/README.rst'


from .preprocessor import LatexPreprocessor


_lppconfig_template = r"""
# latexpp config file template.
#
# This is YAML syntax -- google "YAML tutorial" to get a quick intro.  Careful
# with spaces, correct indentation is important.

# the master LaTeX document -- this file will not be modified, all output will
# be produced in the output_dir
fname: 'MyDocument.tex'

# output file(s) will be created in this directory, originals will not be
# modified
output_dir: 'latexpp_output'

# specify list of fixes to apply, in the given order
fixes:

  # remove all comments
  - 'latexpp.fixes.comments.RemoveCommentsFixes'

  # replace \input{...} directives by the contents of the included file
  - 'latexpp.fixes.input.EvalInputFixes'

  # copy any style files (.sty) that are used in the document and that
  # are present in the current directory to the output directory
  - 'latexpp.fixes.usepackage.CopyLocalPkgsFixes'

  # copy figure files to the output directory and rename them fig-1.xxx,
  # fig-2.xxx, etc.
  - 'latexpp.fixes.figures.CopyNumberFigsFixes'

  # Replace \bibliography{...} by \input{xxx.bbl} and copy the bbl file to the
  # output directory.  Make sure you run (pdf)latex on the main docuemnt
  # before running latexpp
  - 'latexpp.fixes.bib.CopyBblFixes'

  # Expand some macros. Instead of trying to infer the exact expansion that
  # (pdf)latex would itself perform, you specify here a custom string that the
  # macro will be expanded to. If the macro has arguments, specify the nature
  # of the arguments here in the 'argspec:' key (a '*' is an optional *
  # character, a '[' one optional square-bracket-delimited argument, and a '{'
  # is a mandatory argument). The argument values are available via the
  # placeholders %(1)s, %(2)s, etc. Make sure to use single quotes for strings
  # that contain \ backslashes.
  - name: 'latexpp.fixes.macro_subst.Fixes'
    config:
      macros:
        # \tr         -->  \operatorname{tr}
        tr: '\operatorname{tr}'
        # \ket{\psi}  -->  \lvert{\psi}\rangle
        ket:
          argspec: '{'
          repl: '\lvert{%(1)s}\rangle'
        # \braket{\psi}{\phi}  -->  \langle{\psi}\vert{\phi}\rangle
        braket:
          argspec: '{{'
          repl: '\langle{%(1)s}\vert{%(2)s}\rangle'
""".lstrip() # strip leading '\n'


class NewLppconfigTemplate(argparse.Action):
    def __init__(self, **kwargs):
        super().__init__(help='create a new template lppconfig.yml file and exit',
                         nargs=0,
                         **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        # create new YaML template and exit
        cfgfile = 'lppconfig.yml'
        if os.path.exists(cfgfile):
            raise ValueError("The file {} already exists. I won't overwrite it.".format(cfgfile))
        with open(cfgfile, 'w') as f:
            f.write(_lppconfig_template)
        print("Wrote template config file ", cfgfile,
              ".  Please edit to your liking and then run latexpp.", sep='')
        sys.exit(0)


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog='latexpp',
        epilog='See {} for a quick introduction on how to use latexpp.'.format(
            _LATEXPP_QUICKSTART_DOC_URL
        ),
        add_help=False # custom help option
        )

    # this is an optional argument, fname can be specified in lppconfig.yml
    parser.add_argument('fname', metavar='file', nargs='?',
                        help='input file name, master LaTeX document file')

    parser.add_argument('-c', '--lppconfig', dest='lppconfig',
                        action='store', default='lppconfig.yml',
                        help='lpp config file (YAML) to use instead of lppconfig.yml')

    parser.add_argument('-o', '--output-dir',
                        dest='output_dir',
                        default=None,
                        help='output directory (overrides setting from config file)')

    parser.add_argument('-f', '--output-fname', dest='output_fname',
                        default=None,
                        help='output file name in output directory (overrides '
                        'setting from config file)')

    parser.add_argument('-v', '--verbose', dest='verbosity', default=logging.INFO,
                        action='store_const', const=logging.DEBUG,
                        help='verbose mode, see what\'s going on in more detail')

    parser.add_argument('--new', action=NewLppconfigTemplate)

    parser.add_argument('--version', action='version', version='%(prog)s {}'.format(version_str))
    parser.add_argument('--help', action='help', help='show this help message and exit')

    args = parser.parse_args(argv)

    logging.basicConfig(level=args.verbosity)


    try:
        with open(args.lppconfig) as f:
            lppconfig = yaml.load(f, Loader=yaml.FullLoader)
    except FileNotFoundError:
        logger.error("Can't file config file %s.  See %s for instructions to create a lppconfig file.",
                     args.lppconfig, _LPPCONFIG_DOC_URL)
        sys.exit(1)

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
