r"""
This module provides the main preprocessor engine.
"""

import sys
import os
import os.path
import shutil
import re
import functools
import datetime
import importlib

import logging

from pylatexenc import latexwalker


logger = logging.getLogger(__name__)



from .fixes.builtin.remaining_pragmas import ReportRemainingPragmas
from .fixes.builtin.skip import SkipPragma



def _no_latex_verbatim(*args, **kwargs):
    raise RuntimeError("Cannot use latex_verbatim() because the nodes might change.")

def _to_latex(lpp, n):
    return lpp.node_to_latex(n)

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
        node.to_latex = functools.partial(_to_latex, self.lpp, node)

        return node



def get_datetime_now_tzaware():
    utc_dt = datetime.datetime.now(datetime.timezone.utc)
    return utc_dt.astimezone()



_PROCESSED_BY_HEADING = r"""
% Automatically processed by latexpp on {today}
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

    TODO: Document me ..........
    """
    def __init__(self, *,
                 output_dir='_latexpp_output',
                 main_doc_fname=None,
                 main_doc_output_fname=None,
                 config_dir=None):

        super().__init__()

        self.output_dir = os.path.realpath(os.path.abspath(output_dir))
        self.main_doc_fname = main_doc_fname
        self.main_doc_output_fname = main_doc_output_fname
        # directory relative to which to search for custom python fixes:
        self.config_dir = config_dir

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
        :py:class:`latexpp.fixes.BaseFix`.
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
            self.warn_alien_files()

    def warn_alien_files(self):
        r"""
        Check for any files that are in the output directory but that haven't been
        generated by us
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


    def execute_file(self, fname, *, output_fname, omit_processed_by=False):
        r"""
        Process an input file named `fname`, apply all the fixes, and write the
        output to `output_fname`.  The output file name `output_fname` is
        relative to the output directory.

        Unless `omit_processed_by` is set to `True`, the output file will start
        with a brief comment stating that it was the result of preprocessing by
        *latexpp*.
        """

        with open(fname, 'r') as f:
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

        newstr = ''.join(self.node_to_latex(n) for n in newnodelist)
        
        if not omit_processed_by:
            return (
                _PROCESSED_BY_HEADING.format(
                    today=get_datetime_now_tzaware().strftime("%a, %d-%b-%Y %H:%M:%S %Z%z")
                )
                + newstr
            )

        return newstr

    def make_latex_walker(self, s):
        r"""
        Create a :py:class:`pylatexenc.latexwalker.LatexWalker` instance that is
        initialized to parse the string `s`.

        An instance of a customized version of
        :py:class:`pylatexenc.latexwalker.LatexWalker` is returned, to add some
        functionality to the node classes generated by the latex
        walker. [DOCUMENT THIS SOMEWHERE PROPERLY ........]

        ......nodes returned by this latex-walker have latex_verbatim()
        disabled, but have a to_latex() method that re-constructs the latex
        code.
        """
        lw = _LPPLatexWalker(s, latex_context=self.latex_context,
                             tolerant_parsing=False,
                             lpp=self)
        return lw


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
            logger.info("*** Fix %s", fix.fix_name())
            newnodelist = fix.preprocess(newnodelist)

        # check that all LPP pragmas were consumed & report those remaining
        report_pragma_fix = ReportRemainingPragmas()
        report_pragma_fix.set_lpp(self)
        report_pragma_fix.preprocess(newnodelist)

        return newnodelist


    def nodelist_to_latex(self, nodelist):
        result = ''.join(self.node_to_latex(n) if n else '' for n in nodelist)
        #print("*** result(",len(nodelist),") = ", result)
        return result

    def node_to_latex(self, n):

        def add_args(n):
            if n.nodeargd and hasattr(n.nodeargd, 'args_to_latex'):
                return n.nodeargd.args_to_latex()
            if n.nodeargd is None or n.nodeargd.argspec is None \
               or n.nodeargd.argnlist is None:
                # no arguments or unknown argument structure
                return ''
            return ''.join( (self.node_to_latex(n) if n else '')
                            for n in n.nodeargd.argnlist )

        if n.isNodeType(latexwalker.LatexGroupNode):
            return n.delimiters[0] + "".join(self.node_to_latex(n) for n in n.nodelist) \
                + n.delimiters[1]

        elif n.isNodeType(latexwalker.LatexCharsNode):
            return n.chars

        elif n.isNodeType(latexwalker.LatexCommentNode):
            return '%' + n.comment + n.comment_post_space

        elif n.isNodeType(latexwalker.LatexMacroNode):
            # macro maybe with arguments
            return '\\'+n.macroname+n.macro_post_space + add_args(n)

        elif n.isNodeType(latexwalker.LatexEnvironmentNode):
            # get environment behavior definition.
            return (r'\begin{' + n.environmentname + '}' + add_args(n) +
                     "".join( self.node_to_latex(n) for n in n.nodelist ) +
                     r'\end{' + n.environmentname + '}')

        elif n.isNodeType(latexwalker.LatexSpecialsNode):
            # specials maybe with arguments
            return n.specials_chars + add_args(n)

        elif n.isNodeType(latexwalker.LatexMathNode):
            return n.delimiters[0] + "".join( self.node_to_latex(n) for n in n.nodelist ) \
                + n.delimiters[1]

        else:
            raise ValueError("Unknown node type: {}".format(n.__class__.__name__))


    def node_contents_to_latex(self, node):
        if node is None:
            return ''
        if isinstance(node, list):
            return self.nodelist_to_latex(node)
        if node.isNodeType(latexwalker.LatexGroupNode):
            return self.nodelist_to_latex(node.nodelist)
        return self.node_to_latex(node)



    def create_subpreprocessor(self, *, lppconfig_fixes=None):
        pp = LatexPreprocessor(output_dir=self.output_dir,
                               main_doc_fname=self.main_doc_fname,
                               main_doc_output_fname=self.main_doc_output_fname)
        pp.parent_preprocessor = self
        if lppconfig_fixes:
            pp.install_fixes_from_config(lppconfig_fixes)
        return pp



    #
    # More utilities for fixes to call via (fix "self".)lpp.<method>
    #


    def check_autofile_up_to_date(self, autotexfile):
        r"""
        autotexfile is a file automatically generated by LaTeX in the original
        directory (e.g., .aux, .bbl).
        
        This function raises an error if `autotexfile` doesn't exist, and
        generates a warning if its modification time stamp is earlier than that
        of the main TeX file.
        """
        if not os.path.isfile(autotexfile):
            raise ValueError(
                "File {} does not exist. Please run (pdf)latex on the main document first."
                .format(autotexfile)
            )
        if os.path.getmtime(autotexfile) < os.path.getmtime(self.main_doc_fname):
            logger.warning(
                "File %s might be out-of-date, main tex file %s is more recent",
                autotexfile, self.main_doc_fname
            )
        
    def register_output_file(self, fname):
        r"""
        Record the given file `fname` as being part of the official output of this
        run.  The file name `fname` should be relative to `self.output_dir`.
        """
        self.output_files.append(fname)

    def copy_file(self, source, destfname=None):
        r"""
        Copy the file specified by `source` (absolute or relative to main document
        file) to the output dir and rename it to `destfname`.  If `destfname` is
        a path, it must be relative to inside the output directory.
        """
        #
        # Copy the file `source` to the latexpp output directory.  If
        # `destfname` is not None, rename the file to `destfname`.
        #
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
        self._do_copy_file(source, dest)
        
        self.register_output_file(destfname)



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
            # Maybe in the future we'll add prog option --clean-output-dir that
            # removes all before outputting...
            logger.warning("Output directory %s is not empty", self.display_output_dir)

    def _os_walk_output_dir(self):
        return os.walk(self.output_dir)

