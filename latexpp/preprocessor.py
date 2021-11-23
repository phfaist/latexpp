r"""
This module provides the main preprocessor engine.
"""

import sys
import os
import os.path
import shutil
#import re
import datetime
import importlib

import logging
from typing import Text

from pylatexenc import latexwalker

from . import __version__


logger = logging.getLogger(__name__)



from .fixes.builtin.remaining_pragmas import ReportRemainingPragmas
from .fixes.builtin.skip import SkipPragma



from ._lpp_parsing import _LPPLatexWalker #, LatexCodeRecomposer, _LPPParsingState



def get_datetime_now_tzaware():
    utc_dt = datetime.datetime.now(datetime.timezone.utc)
    return utc_dt.astimezone()



_PROCESSED_BY_HEADING = r"""
% Automatically processed by latexpp v{version} on {today}
% See https://github.com/phfaist/latexpp
""".lstrip()


class _TemporarilySetSysPath:
    def __init__(self, dir):
        self.dir = dir

    def __enter__(self):
        self.oldsyspath = sys.path
        if self.dir:
            sys.path = [self.dir] + sys.path
        return self

    def __exit__(self, typ, value, traceback):
        if self.dir:
            sys.path = self.oldsyspath



class LatexPreprocessor:
    r"""
    Main preprocessor class.

    This class collects together various fixes and applies them to a LaTeX
    document or parts of the document.

    Arguments:

    - `output_dir` is the folder where the resulting processed document should
      be placed.

    - `main_doc_fname` is the main document that we need to process.

    - `main_doc_output_fname` is the name to give to the processed main document
      inside the `output_dir` folder.

    - `config_dir` is the root directory (when using the command-line `latexpp`
      tool, this is where the `lppconfig.yml` resides).  Relative paths
      specified to some helpers such as :py:meth:`copy_file()` are interpreted
      as relative to this directory.

    - `tex_inputs` is a list of search paths, similar to the LaTeX environment 
      varibale `TEXINPUTS`.

    The fixes can be installed directly via a configuration data structure with
    :py:meth:`install_fixes_from_config()` (as extracted from a YaML reader from
    a `lppconfig.yml` file, for instance), or fix instances can be installed
    manually with :py:meth:`install_fix()`.

    Initialization tasks should be run by calling :py:meth:`initialize()` after
    all fixes have been installed, but before :py:meth:`execute_main()` (or
    friends) are called.

    The actual processing is performed by calling one of
    :py:meth:`execute_main()`, :py:meth:`execute_file()`, or
    :py:meth:`execute_string()`.  These parse the corresponding LaTeX code into
    nodes and runs all fixes.

    After calling the `execute_*()` methods as required, you should call
    :py:meth:`finalize()` to finish the processing and carry out final tasks
    that the fixes need to do at the end.  You'll also get a warning for files
    that are in the output directory but that weren't generated by `latexpp`,
    etc.

    This preprocessor class also exposes several methods that are intended for
    individual fixes' convenience.  These are :py:meth:`make_latex_walker()`,
    :py:meth:`create_subpreprocessor()`, :py:meth:`check_autofile_up_to_date()`,
    :py:meth:`register_output_file()`, :py:meth:`copy_file()` and
    :py:meth:`open_file()`.  See their doc below.

    Attributes:

    .. py:attribute:: parent_preprocessor

       This attribute is used for sub-preprocessors.  See
       :py:meth:`create_subpreprocessor()`.

    Methods:
    """
    def __init__(self, *,
                 output_dir='_latexpp_output',
                 main_doc_fname=None,
                 main_doc_output_fname=None,
                 config_dir=".",
                 tex_inputs=(".",)):

        super().__init__()

        self.output_dir = os.path.realpath(os.path.abspath(output_dir))
        self.main_doc_fname = main_doc_fname
        self.main_doc_output_fname = main_doc_output_fname
        # directory relative to which to search for custom python fixes:
        self.config_dir = config_dir
        self.tex_inputs = tex_inputs

        # version of output_dir for displaying purposes
        self.display_output_dir = output_dir.rstrip('/') + '/'

        self.latex_context = latexwalker.get_default_latex_context_db()
        self.latex_context.add_context_category('latexpp-categories-marker-end',
                                                macros=[], prepend=True)

        self.fixes = []

        self.initialized = False
        
        self.output_files = []
        
        self.omit_processed_by = False

        self.add_preamble_comment_start = '\n%%%\n'
        self.add_preamble_comment_end = '\n%%%\n'
        
        # set to non-None if this is a sub-preprocessor of a main preprocessor
        self.parent_preprocessor = None


    def install_fix(self, fix, *, prepend=False):
        r"""
        Register the given fix instance to be run after (respectively before if
        `prepend=True`) the existing list of fixes.

        The type of `fix` must be a subclass of
        :py:class:`latexpp.fix.BaseFix`.
        """

        # sanity check -- make sure custom fix classes don't forget to call
        # their superclass constructor.
        if not getattr(fix, '_basefix_constr_called', False):
            raise RuntimeError("Fix class {}.{} does not call its superclass constructor"
                               .format(fix.__class__.__module__, fix.__class__.__name__))

        if prepend:
            self.fixes.insert(fix, 0)
        else:
            self.fixes.append(fix)

        fix.set_lpp(self)

    def install_fixes_from_config(self, lppconfig_fixes):
        r"""
        Load all the fixes from the given configuration data structure.  The
        `lppconfig_fixes` are a list of dictionaries with keys 'name' and
        'config'.  It's the same as what you specify in the `lppconfig.yml` in
        the `fixes:` configuration.

        This automatically calls `install_fix()` for all the loaded fixes.
        """
        for fixconfig in lppconfig_fixes:
            if isinstance(fixconfig, str):
                fixconfig = {'name': fixconfig}

            fixname = fixconfig['name']

            modname, clsname = fixname.rsplit('.', maxsplit=1)

            # allow package to be in current working directory
            with _TemporarilySetSysPath(dir=self.config_dir):
                mod = importlib.import_module(modname)

            if clsname not in mod.__dict__:
                raise ValueError("Module ‘%s’ does not provide a class named ‘%s’"%(
                    modname, clsname))

            cls = mod.__dict__[clsname]

            self.install_fix(cls(**fixconfig.get('config', {})))


    def initialize(self):
        r"""
        Perform essential initialization tasks.

        Must be called after all fixes are installed, but before
        :py:meth:`execute_main()` is called.
        """

        logger.debug("initializing preprocessor and fixes")

        if not os.path.isdir(self.output_dir):
            self._do_ensure_destdir(self.output_dir, self.display_output_dir)

        if not self.parent_preprocessor:
            self._warn_if_output_dir_nonempty()

        for fix in self.fixes:
            fix.initialize()

        #
        # Now check if the fixes have macro/env/specials specs to add.  Do this
        # after initialize() so that fixes have the opportinity to determine
        # what specs they need.
        #
        for fixn, fix in enumerate(self.fixes):
            specs = fix.specs()
            if specs:
                self.latex_context.add_context_category(
                    'lppfix{:02d}:{}.{}'.format(fixn, fix.__class__.__module__,
                                                fix.__class__.__name__),
                    insert_before='latexpp-categories-marker-end',
                    **specs
                )


        self.initialized = True


    def finalize(self):
        r"""
        Calls the `finalize()` routine on all fixes.  Fixes have the opportunity to
        finish up stuff after the document has been processed.

        Must be called after :py:meth:`execute_main()` is called.
        """

        logger.debug("finalizing preprocessor and fixes")

        for fix in self.fixes:
            fix.finalize()

        if self.parent_preprocessor:
            # report other new files
            self.parent_preprocessor.output_files += self.output_files
        else:
            # produce a warning for alien files in output directory
            self._warn_alien_files()

    def _warn_alien_files(self):
        r"""
        Check for any files that are in the output directory but that haven't been
        generated by us.
        """

        our_files_norm = [
            os.path.relpath(os.path.realpath(os.path.join(self.output_dir, x)),
                            self.output_dir)
            for x in self.output_files
        ] # in case output_files has a structure with symlinks, canonicalize
          # paths relative to output_dir

        logger.debug("Our output files are: %r", our_files_norm)

        alien_files = []
        for (dirpath, dirnames, filenames) in self._os_walk_output_dir():
            for fn in filenames:
                ofn = os.path.relpath(os.path.join(dirpath, fn), self.output_dir)
                if ofn not in our_files_norm:
                    alien_files.append(ofn)

        if alien_files:
            logger.warning("The following files were found in the output directory, "
                           "but they were not generated by latexpp:\n%s\n",
                           "\n".join('    {}'.format(x) for x in alien_files))


    def execute_main(self):
        r"""
        Main execution routine.  Call this to process the main document with all our
        installed fixes.
        """
        self.execute_file(self.main_doc_fname,
                          output_fname=self.main_doc_output_fname)


    def _resolve_source_fname(self, fname):
        return os.path.join(self.config_dir, fname)


    def resolve_tex_fname(self, fname, extensions=('',), issue_warning=False):
        """Resolves a TEX file based on the search paths of tex_inputs, returns a 
        relative path to config_dir."""

        for p in self.tex_inputs:
            for ext in extensions:
                f = os.path.join(p, fname + ext)
                if os.path.exists(f):
                    return os.path.relpath(f, self.config_dir)
        
        if issue_warning:
            logger.warning("File not found: ‘%s’. Tried extensions %r with TEXINPUS='%s'", 
                fname, extensions, ';'.join(self.tex_inputs))

        raise FileNotFoundError()


    def execute_file(self, fname, *, output_fname, omit_processed_by=False):
        r"""
        Process an input file named `fname`, apply all the fixes, and write the
        output to `output_fname`.  The output file name `output_fname` is
        relative to the output directory.

        Unless `omit_processed_by` is set to `True`, the output file will start
        with a brief comment stating that it was the result of preprocessing by
        *latexpp*.
        """

        with open(self._resolve_source_fname(self.resolve_tex_fname(fname)), 'r') as f:
            s = f.read()

        outdata = self.execute_string(s, input_source='file ‘{}’'.format(fname))

        self.register_output_file(output_fname)

        with open(os.path.join(self.output_dir, output_fname), 'w') as f:
            f.write(outdata)

    def execute_string(self, s, *, pos=0, input_source=None, omit_processed_by=False):
        r"""
        Parse the string `s` as LaTeX code, apply all installed fixes, and return
        the preprocessed LaTeX code.

        The `input_source` argument is a short descriptive string of the source
        of the LaTeX content for error messages (e.g., the file name).

        Unless `omit_processed_by` is set to `True`, the output file will start
        with a brief comment stating that it was the result of preprocessing by
        *latexpp*.
        """

        if self.omit_processed_by:
            omit_processed_by = True

        lw = self.make_latex_walker(s)
        
        try:
            (nodelist, pos, len_) = lw.get_latex_nodes(pos=pos)
        except latexwalker.LatexWalkerParseError as e:
            if input_source and not e.input_source:
                e.input_source = input_source
            raise

        newnodelist = self.preprocess(nodelist)

        newstr = ''.join(n.to_latex() for n in newnodelist)
        
        if not omit_processed_by:
            return (
                _PROCESSED_BY_HEADING.format(
                    version=__version__,
                    today=get_datetime_now_tzaware().strftime("%a, %d-%b-%Y %H:%M:%S %Z%z")
                )
                + newstr
            )

        return newstr


    def preprocess(self, nodelist):
        r"""
        Run all the installed fixes on the given list of nodes `nodelist`.
        """

        if not self.initialized:
            raise RuntimeError("You forgot to call LatexPreprocessor.initialize()")

        newnodelist = list(nodelist)

        #
        # Execute %%!lpp skip pragmas as a built-in fix before all other fixes
        #
        skip_pragma_fix = SkipPragma()
        skip_pragma_fix.set_lpp(self)
        newnodelist = skip_pragma_fix.preprocess(newnodelist)

        #
        # do add_preamble if necessary
        #
        for j in range(len(newnodelist)):
            n = newnodelist[j]
            if n is not None and n.isNodeType(latexwalker.LatexEnvironmentNode) \
               and n.environmentname == 'document':
                # here is where we should insert preamble instructions.
                add_preamble = ''
                for fix in self.fixes:
                    p = fix.add_preamble()
                    if p:
                        add_preamble += p

                if not add_preamble.strip():
                    # no preamble to add, all ok
                    break

                add_preamble = self.add_preamble_comment_start + add_preamble  + \
                    self.add_preamble_comment_end

                # and insert preamble before document. TODO: mark nodes with
                # "lpp_ignore" to inhibit further processing; see TODO below.

                try:
                    lw = self.make_latex_walker(add_preamble)
                    preamble_nodes = lw.get_latex_nodes()[0]
                except latexwalker.LatexWalkerParseError as e:
                    logger.error("Internal error: can't parse latex code that "
                                 "fixes want to include:\n%r\n%s", s, e)
                    raise

                newnodelist[j:j] = preamble_nodes

                # finished with preamble business.
                break


        #
        # run all fixes
        #

        # TODO: allow nodes to be marked with an attribute "node.lpp_ignore =
        # True" which would inhibit processing by fixes.  Implement this by
        # passing only chunks at a time to fix.preprocess of contiguous nodes
        # that do not have lpp_ignore set.

        for fix in self.fixes:
            if self.parent_preprocessor is not None:
                logger.debug("*** [sub-preprocessor] Fix: %s", fix.fix_name())
            else:
                logger.info("*** Fix %s", fix.fix_name())
            newnodelist = fix.preprocess(newnodelist)

        # check that all LPP pragmas were consumed & report those remaining
        report_pragma_fix = ReportRemainingPragmas()
        report_pragma_fix.set_lpp(self)
        report_pragma_fix.preprocess(newnodelist)

        return newnodelist


    # def nodelist_to_latex(self, nodelist):
    #     result = ''.join(self.node_to_latex(n) if n else '' for n in nodelist)
    #     #print("*** result(",len(nodelist),") = ", result)
    #     return result
    #
    # def node_to_latex(self, n):
    #     return n.parsing_state.lpp_latex_walker.node_to_latex(n)
    #
    # def node_contents_to_latex(self, node):
    #     if node is None:
    #         return ''
    #     if isinstance(node, list):
    #         return self.nodelist_to_latex(node)
    #     if node.isNodeType(latexwalker.LatexGroupNode):
    #         return self.nodelist_to_latex(node.nodelist)
    #     return self.node_to_latex(node)



    def make_latex_walker(self, s):
        r"""
        Create a :py:class:`pylatexenc.latexwalker.LatexWalker` instance that is
        initialized to parse the string `s`.

        Returns an instance of a customized version of
        :py:class:`pylatexenc.latexwalker.LatexWalker`.  The custom latex walker
        adds some functionality to the node classes generated by the latex
        walker. See :ref:`implementation-notes-pylatexenc` for more information.

        Bottom line is that fix classes should never create
        :py:class:`pylatexenc.latexwalker.LatexWalker`\ s directly, but rather,
        they should use this method to creater a latex walker.
        """
        lw = _LPPLatexWalker(s, latex_context=self.latex_context,
                             tolerant_parsing=False,
                             lpp=self)
        return lw



    def create_subpreprocessor(self, *, lppconfig_fixes=None):
        """
        Create a sub-preprocessor (or child preprocessor) of this preprocessor.

        Sub-preprocessors are used in some fixes in order to apply a separate
        set of fixes for instance to parts of the document.  (See, e.g.,
        :py:class:`latexpp.fixes.regional_fix.Apply` or
        :py:class:`latexpp.fixes.usepackage.InputLocalPkgs`)

        A sub-preprocessor is itself an instance of a
        :py:class:`LatexPreprocessor`.  You install fixes (or load the fixes
        from a config data structure), :py:meth:`initialize()` it, run
        `exec_*()` methods as required, then :py:meth:`finalize()` it.
        """
        pp = LatexPreprocessor(output_dir=self.output_dir,
                               main_doc_fname=self.main_doc_fname,
                               main_doc_output_fname=self.main_doc_output_fname, 
                               config_dir=self.config_dir, 
                               tex_inputs=self.tex_inputs)
        pp.parent_preprocessor = self
        if lppconfig_fixes:
            pp.install_fixes_from_config(lppconfig_fixes)
        return pp






    #
    # More utilities for fixes to call via (fix "self".)lpp.<method>
    #


    def check_autofile_up_to_date(self, autotexfile, *, what_to_run='(pdf)latex'):
        r"""
        autotexfile is a file automatically generated by LaTeX in the original
        directory (e.g., .aux, .bbl).
        
        This function raises an error if `autotexfile` doesn't exist, and
        generates a warning if its modification time stamp is earlier than that
        of the main TeX file.

        Arguments:

        - `what_to_run`.  If the auxiliary file `autotexfile` does not exist,
          then an error is emitted telling that they have to run `what_to_run`
          first.  By default, `what_to_run="(pdf)latex"`.
        """

        autotexfile_resolved = self._resolve_source_fname(autotexfile)

        if not os.path.isfile(autotexfile_resolved):
            raise ValueError(
                "File {} does not exist. Please run {} on the main document first."
                .format(autotexfile, what_to_run)
            )
        if os.path.getmtime(autotexfile_resolved) < os.path.getmtime(self.main_doc_fname):
            logger.warning(
                "File %s might be out-of-date, main tex file %s is more recent",
                autotexfile, self.main_doc_fname
            )
        
    def register_output_file(self, fname):
        r"""
        Take note that the given file `fname` is part of the output of this `latexpp`
        run.  The file name `fname` should be relative to `self.output_dir`.

        The point of this is that the preprocessor will inspect the output
        directory at the end of the whole process and will emit a warning if it
        finds any file that wasn't generated by `latexpp`.  This method is how a
        fix can tell the preprocessor that it is responsible for a specific new
        file in the output and that that file should not be part of the "foreign
        files warning".
        """
        self.output_files.append(fname)

    def copy_file(self, source, destfname=None):
        r"""
        Copy the file specified by `source` (either an absolute path, or a path
        relative to `config_dir`) to the output directory, and rename it
        to `destfname`.  If `destfname` is a path, it must be relative to inside
        the output directory.

        The file is registered as an output file, i.e., you don't need to call
        :py:meth:`register_output_file()` for this file.
        """
        if destfname is not None:
            dest = os.path.join(self.output_dir, destfname)
            destdn, destbn = os.path.split(destfname)
        else:
            dest = self.output_dir
            destfname = os.path.basename(source)
            destdn, destbn = '', destfname

        destdir = os.path.join(self.output_dir, destdn)
        logger.info("Copying file %s -> %s", source,
                    os.path.join(self.display_output_dir, destfname if destfname else ''))
        self._do_ensure_destdir(destdir, destdn)
        self._do_copy_file(self._resolve_source_fname(source), dest)
        
        self.register_output_file(destfname)

    def open_file(self, fname):
        """
        Open the file `fname` for reading and return a handle to the open file.
        Should be used in a context manager as ``with lpp.open_file(xxx) as f:``

        (Use this function instead of ``open()`` directly so that the fixes can
        be integrated more easily in the tests with mock inputs.)
        """
        return open(self._resolve_source_fname(fname))


    # these methods that access the filesystem are separate functions so that
    # they can be monkey-patched for tests with mock files

    def _do_ensure_destdir(self, destdir, destdn):
        if os.path.exists(destdir):
            if not os.path.isdir(destdir):
                raise ValueError(
                    "Cannot create directory {}, file with the same name already exists"
                    .format(destdn)
                )
        else:
            os.makedirs(destdir)

    def _do_copy_file(self, source, dest):
        shutil.copy2(source, dest)

    def _warn_if_output_dir_nonempty(self):
        if len(os.listdir(self.output_dir)):
            # Maybe in the future we'll add a program option --clean-output-dir
            # that removes all before outputting...
            logger.warning("Output directory %s is not empty", self.display_output_dir)

    def _os_walk_output_dir(self):
        return os.walk(self.output_dir)

