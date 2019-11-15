import re
import os
import os.path
import logging

logger = logging.getLogger(__name__)

from pylatexenc.macrospec import MacroSpec
from pylatexenc.latexwalker import LatexMacroNode

from latexpp.fixes import BaseFix


class CopyAndInputBbl(BaseFix):
    r"""
    Copy the (latex-generated) BBL file from the current directory into the
    output directory, and replace a ``\bibliography`` call by
    ``\input{<BBLFILE>}``.

    .. note::

       Multiple bibliographies are not supported.

    Arguments:

    - `bblname`: the name of the BBL file to include.  If `None` or not
      provided, the bbl name is derived from the main latex file name.
   
    - `outbblname`: the bbl file is copied to the output directory and renamed
      to `outbblname`.  By default this derived from the main output latex file
      name.

    - `eval_input`: Paste the BBL file contents into the TeX file rather than
      issuing a '\input{XXX.bbl}' directive.
    """

    def __init__(self, bblname=None, outbblname=None, eval_input=False):
        super().__init__()
        self.bblname = bblname
        self.outbblname = outbblname
        self.eval_input = eval_input
    
    def specs(self, **kwargs):
        return dict(macros=[
            MacroSpec('bibliographystyle', '{'),
            MacroSpec('bibliography', '{'),
        ])

    def fix_node(self, n, **kwargs):

        if n.isNodeType(LatexMacroNode) and n.macroname == 'bibliographystyle':
            # remove \bibliographystyle{} command
            return ''

        if n.isNodeType(LatexMacroNode) and n.macroname == 'bibliography':

            if self.bblname:
                bblname = self.bblname
            else:
                bblname = re.sub(r'(\.(la)?tex)$', '', self.lpp.main_doc_fname) + '.bbl'
            if self.outbblname:
                outbblname = self.outbblname
            else:
                outbblname = re.sub(r'(\.(la)?tex)$', '', self.lpp.main_doc_output_fname) \
                    + '.bbl'

            self.lpp.check_autofile_up_to_date(bblname)

            if self.eval_input:
                # input BBL contents
                with open(bblname, 'r') as f:
                    bbl_contents = f.read()
                return bbl_contents
            else:
                # copy BBL file
                self.lpp.copy_file(bblname, outbblname)
                return r'\input{%s}'%(outbblname)

        return None


class ApplyAliases(BaseFix):
    r"""
    Scans the files `bibalias_def_search_files` for bibalias commands
    ``\bibalias{alias}{target}`` (or whatever macro is given to `bibaliascmd`),
    and applies the aliases to all known citation commands (from the natbib
    doc).  Any bibalias commands are encountered in the input they are stored as
    aliases. Further manual aliases can be specified using the `aliases={...}`
    argument.
    """
    def __init__(self,
                 bibaliascmd='bibalias',
                 bibalias_defs_search_files=[],
                 aliases={}):
        super().__init__()
        self.bibaliascmd = bibaliascmd
        self.bibalias_defs_search_files = bibalias_defs_search_files

        # which argument has the keys is obtained from the argspec as the first
        # mandatory argument
        self.cite_macros = set(('cite', 'citet', 'citep', 'citealt', 'citealp',
                               'citeauthor', 'citefullauthor', 'citeyear', 'citeyearpar',
                               'Citet', 'Citep', 'Citealt', 'Citealp', 'Citeauthor',
                               'citenum',))

        self._bibaliases = {}
        self._bibaliases.update(aliases)

        self.bibalias_defs_search_files = bibalias_defs_search_files


    def initialize(self):
        # right away, populate bib aliases with search through given tex files.
        # Hmmm, should we use a latexwalker here in any way? ...?  Not sure it's
        # worth it
        rx_bibalias = re.compile(
            r'^([^%]|\\%)*?\\' + self.bibaliascmd
            + r'\s*\{(?P<alias>[^}]+)\}\s*\{(?P<target>[^}]+)\}',
            flags=re.MULTILINE
        )
        for bfn in self.bibalias_defs_search_files:
            with open(bfn) as ff:
                for m in rx_bibalias.finditer(ff.read()):
                    alias = m.group('alias')
                    target = m.group('target')
                    logger.debug("Found bibalias %s -> %s", alias, target)
                    self._bibaliases[alias] = target
        self._update_bibaliases()


    def specs(self, **kwargs):
        return dict(macros=[MacroSpec(self.bibaliascmd, '{{')])

    def fix_node(self, n, **kwargs):
        if n.isNodeType(LatexMacroNode):
            if n.macroname == self.bibaliascmd:
                if not n.nodeargd or not n.nodeargd.argnlist \
                   or len(n.nodeargd.argnlist) != 2:
                    logger.warning(r"No arguments or invalid arguments to \bibalias "
                                   "command: %s",
                                   n.to_latex())
                    return None

                alias = self.preprocess_arg_latex(n, 0).strip()
                target = self.preprocess_arg_latex(n, 1).strip()
                logger.debug("Defined bibalias %s -> %s", alias, target)
                self._bibaliases[alias] = target
                self._update_bibaliases()
                return [] # remove bibalias command from input

            if n.macroname in self.cite_macros:
                if n.nodeargd is None or n.nodeargd.argspec is None \
                   or n.nodeargd.argnlist is None:
                    logger.warning(r"Ignoring invalid citation command: %s", n.to_latex())
                    return None

                citargno = n.nodeargd.argspec.find('{')
                ncitarg = n.nodeargd.argnlist[citargno]
                citargnew = self._replace_aliases(
                    self._preprocess_citation_string(ncitarg)
                )

                s = '\\'+n.macroname \
                    + ''.join(self.preprocess_latex(n.nodeargd.argnlist[:citargno])) \
                    + '{'+citargnew+'}' \
                    + ''.join(self.preprocess_latex(n.nodeargd.argnlist[citargno+1:]))

                #print("*** replaced in cite cmd: ", s)

                return s
                

        return None

    def _update_bibaliases(self):
        self._rx_pattern = re.compile(
            r"^(" +
            r"|".join( re.escape(k) for k in sorted(self._bibaliases, key=len, reverse=True) )
            + r")$"
        )

    def _preprocess_citation_string(self, s):
        s = self.preprocess_contents_latex(s)
        # remove all comments here
        s = re.sub(r'[%].*\n\s*', '', s)
        return s

    def _replace_aliases(self, s):
        # use multiple string replacements --> apparently we need a regex.
        # Cf. https://stackoverflow.com/a/36620263/1694896
        #print("*** rx_pattern = ", self._rx_pattern.pattern, "; aliases = ",
        #      self._bibaliases)
        s2 = ",".join(
            self._rx_pattern.sub(lambda m: self._bibaliases[m.group()], citk.strip())
            for citk in s.split(",")
        )
        #logger.debug("bibalias: Replaced ‘%s’ -> ‘%s’", s, s2)
        return s2
