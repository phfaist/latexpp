import os.path
import sys
import argparse
import logging

import colorlog

logger = logging.getLogger('latexpp.__main__')

import yaml

from . import __version__ as version_str

from pylatexenc import latexwalker # catch latexwalker.LatexWalkerParseError

_LPPCONFIG_DOC_URL = 'https://latexpp.readthedocs.io/'
_LATEXPP_QUICKSTART_DOC_URL = 'https://git.io/JerVr' #'https://github.com/phfaist/latexpp/blob/master/README.rst'
_LATEXPP_FIXES_DOC_URL = 'https://latexpp.readthedocs.io/en/latest/fixes/'


from .preprocessor import LatexPreprocessor



def setup_logging(level):
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.TTYColoredFormatter(
        stream=sys.stderr,
        fmt='%(log_color)s%(levelname)-8s: %(message)s' #'  [%(name)s]'
    ))

    root = colorlog.getLogger()
    root.addHandler(handler)

    root.setLevel(level)



_lppconfig_template = r"""
# latexpp config for MyDocument.tex
#
# This is YAML syntax -- google "YAML tutorial" to get a quick intro.
# Be careful with spaces since indentation is important.

# the master LaTeX document -- this file will not be modified, all
# output will be produced in the output_dir
fname: 'MyDocument.tex'

# output file(s) will be created in this directory, originals will
# not be modified
output_dir: 'latexpp_output'

# main document file name in the output directory
output_fname: 'main.tex'

# specify list of fixes to apply, in the given order
fixes:

  # replace \input{...} directives by the contents of the included
  # file
  - 'latexpp.fixes.input.EvalInput'

  # remove all comments
  - 'latexpp.fixes.comments.RemoveComments'

  # copy any style files (.sty) that are used in the document and
  # that are present in the current directory to the output directory
  - 'latexpp.fixes.usepackage.CopyLocalPkgs'

  # copy figure files to the output directory and rename them
  # fig-01.xxx, fig-02.xxx, etc.
  - 'latexpp.fixes.figures.CopyAndRenameFigs'

  # Replace \bibliography{...} by \input{xxx.bbl} and copy the bbl
  # file to the output directory.  Make sure you run (pdf)latex on
  # the main docuemnt before running latexpp
  - 'latexpp.fixes.bib.CopyAndInputBbl'

  # Expand some macros. Latexpp doesn't parse \newcommand's, so you
  # need to specify here the LaTeX code that the macro should be
  # expanded to. If the macro has arguments, specify the nature of
  # the arguments here in the 'argspec:' key (a '*' is an optional
  # * character, a '[' one optional square-bracket-delimited
  # argument, and a '{' is a mandatory argument). The argument values
  # are available via the placeholders %(1)s, %(2)s, etc. Make sure
  # to use single quotes for strings that contain \ backslashes.
  - name: 'latexpp.fixes.macro_subst.Subst'
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
            raise ValueError("The file {} already exists. I won't overwrite it."
                             .format(cfgfile))
        with open(cfgfile, 'w') as f:
            f.write(_lppconfig_template)
        # logger hasn't been set up yet.
        sys.stderr.write(
            ("Wrote template config file {}.  Please edit to your "
             "liking and then run latexpp.\n").format(cfgfile)
        )
        sys.exit(0)


def main(argv=None, omit_processed_by=False):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog='latexpp',
        epilog=('See {} for a quick introduction on how to use latexpp '
                'and {} for a list of available fix classes.').format(
            _LATEXPP_QUICKSTART_DOC_URL,
            _LATEXPP_FIXES_DOC_URL
        ),
        add_help=False # custom help option
        )

    # this is an optional argument, fname can be specified in lppconfig.yml
    parser.add_argument('fname', metavar='file', nargs='?',
                        help='input file name, master LaTeX document file')

    parser.add_argument('-p', '--profile', dest='lppconfig_profile',
                        action='store', default='',
                        help='look for config file lppconfig-<PROFILE>.yml '
                        'instead of lppconfig.yml')

    parser.add_argument('-c', '--lppconfig', dest='lppconfig',
                        action='store', default='',
                        help='lpp config file (YAML) to use instead of lppconfig.yml. '
                        'Overrides -p option.')

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

    parser.add_argument('--version', action='version',
                        version='%(prog)s {}'.format(version_str))
    parser.add_argument('--help', action='help',
                        help='show this help message and exit')

    args = parser.parse_args(argv)


    setup_logging(level=args.verbosity)


    if args.lppconfig:
        lppconfigyml = args.lppconfig
    elif args.lppconfig_profile:
        lppconfigyml = 'lppconfig-{}.yml'.format(args.lppconfig_profile)
    else:
        lppconfigyml = 'lppconfig.yml'

    config_dir = os.path.dirname(os.path.abspath(lppconfigyml))

    try:
        with open(lppconfigyml) as f:
            lppconfig = yaml.load(f, Loader=yaml.FullLoader)
    except FileNotFoundError:
        logger.error("Cannot find configuration file ‘%s’.  "
                     "See %s for instructions to create a lppconfig file.",
                     lppconfigyml, _LPPCONFIG_DOC_URL)
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
        main_doc_output_fname=output_fname,
        config_dir=config_dir
    )

    # for tests
    if omit_processed_by:
        pp.omit_processed_by = omit_processed_by

    pp.install_fixes_from_config(lppconfig['fixes'])

    try:

        pp.initialize()

        pp.execute_main()

        pp.finalize()

    except latexwalker.LatexWalkerParseError as e:
        logger.error("Parse error! %s", e)
        sys.exit(1)



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
