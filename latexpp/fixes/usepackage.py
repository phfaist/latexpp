
import os.path as os_path # allow tests to monkey-patch this

import logging
logger = logging.getLogger(__name__)

from pylatexenc.latexwalker import LatexMacroNode
from pylatexenc.macrospec import std_macro

from latexpp.fix import BaseFix


def node_get_usepackage(n, fix):
    """
    If `n` is a macro node that is a 'usepackage' directive, then this function
    returns a string with the package name.  Otherwise we return `None`.
    """
    if (n.isNodeType(LatexMacroNode) and n.macroname in ("usepackage", "RequirePackage") 
        and n.nodeargd is not None and n.nodeargd.argnlist is not None):
        # usepackage has signature '[{'
        return fix.preprocess_arg_latex(n, 1).strip()
    return None


class RemovePkgs(BaseFix):
    r"""
    Remove some instances of ``\usepackage[..]{...}`` for some selected pacage
    names.
    
    Arguments:

    - `pkglist`: List of package names for which we should remove any
      ``\usepackage`` directives.

    .. warning::

       [FIXME]: This does not work if you have ``\usepackage`` directives with
       several packages.  This should be easy to fix...
    """
    def __init__(self, pkglist):
        super().__init__()
        self.pkglist = set(pkglist)

    def fix_node(self, n, **kwargs):

        pkgname = node_get_usepackage(n, self)
        if pkgname is not None and pkgname in self.pkglist:
            logger.debug(r"Removing instruction ‘%s’", n.to_latex())
            return [] # kill entire node

        return None

    def specs(self):
        return {
            "macros": [std_macro("RequirePackage", True, 1)]
        }


class CopyLocalPkgs(BaseFix):
    r"""
    Copy package style files that are present in the current directory and that
    are included with ``\usepackage{...}``.

    .. warning::

       [FIXME]: This does not work if you have ``\usepackage`` directives with
       several packages.  This should be easy to fix...

    Arguments:

    - `blacklist`: a list of package names (without the '.sty' extension) for
      which we should *not* copy the style file, even if found in the current
      working directory.
    """
    def __init__(self, blacklist=None):
        super().__init__()
        self.blacklist = frozenset(blacklist) if blacklist else frozenset()

    def fix_node(self, n, **kwargs):

        pkgname = node_get_usepackage(n, self)
        if pkgname is not None and pkgname not in self.blacklist:
            pkgnamesty = pkgname + '.sty'
            if os_path.exists(pkgnamesty):
                self.lpp.copy_file(pkgnamesty)
                return None # keep node the same

        return None

    def specs(self):
        return {
            "macros": [std_macro("RequirePackage", True, 1)]
        }


class InputLocalPkgs(BaseFix):
    r"""
    Include the contents of specified package style files that are present in
    the current directory and that are included with ``\usepackage{...}``.

    .. warning::

       [FIXME]: This does not work if you have ``\usepackage`` directives with
       several packages.  This should be easy to fix...

    .. warning::

       [FIXME]: This will most probably not work if your package processes
       package options.

    The copied local packages can also have their own set of "fixes" applied,
    too, as if you had run a separate instance of LatexPP on the pacakge file.

    Arguments:

    - `packages`: a list of package names (without the '.sty' extension) for
      which we should include the style file contents into the file.  The style
      file must reside in the current working directory.

    - `fixes`: a set of fixes to run on the local package files.  There is no
      artificial limit to the recursion :)
    """
    def __init__(self, packages=None, fixes=None):
        super().__init__()
        self.packages = frozenset(packages) if packages else frozenset()
        self.fixes = fixes if fixes else []
        self.subpp = None

    def initialize(self):

        # local import to make sure we avoid cyclic imports at import-time
        import latexpp.fixes.macro_subst

        self.subpp = self.lpp.create_subpreprocessor()
        self.subpp.install_fix(
            latexpp.fixes.macro_subst.Subst(
                macros={
                    'NeedsTeXFormat': {'argspec': '{[', 'repl': ''},
                    'ProvidesPackage': {'argspec': '{[', 'repl': ''},
                }
            )
        )
        if self.fixes:
            self.subpp.install_fixes_from_config(self.fixes)

        self.subpp.initialize()

    def fix_node(self, n, **kwargs):

        pkgname = node_get_usepackage(n, self)
        if pkgname is not None and pkgname in self.packages:
            pkgnamesty = pkgname + '.sty'
            if os_path.exists(pkgnamesty):
                logger.debug("Processing input package ‘%s’", pkgnamesty)
                with self.lpp.open_file(pkgnamesty) as f:
                    pkgcontents = f.read()
                if self.subpp:
                    pkgcontents = \
                        self.subpp.execute_string(pkgcontents,
                                                  omit_processed_by=True,
                                                  input_source=pkgnamesty)
                pkgcontents = r"\makeatletter" + pkgcontents + r"\makeatother" + "\n"
                return pkgcontents

        return None

    def finalize(self):
        self.subpp.finalize()

    def specs(self):
        return {
            "macros": [std_macro("RequirePackage", True, 1)]
        }
