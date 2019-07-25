import re
import os
import os.path
import logging

logger = logging.getLogger(__name__)

from pylatexenc.macrospec import MacroSpec
from pylatexenc.latexwalker import LatexMacroNode


class CopyBblFixes(object):
    def __init__(self, bblname=None, outbblname=None):
        self.bblname = bblname
        self.outbblname = outbblname

    def fix_node(self, n, lpp):
        if n.isNodeType(LatexMacroNode) and n.macroname == 'bibliography':
            # check modif time wrt main tex file
            if self.bblname:
                bblname = self.bblname
            else:
                bblname = re.sub('(\.(la)?tex)$', '', lpp.main_doc_fname) + '.bbl'
                #print('lpp.main_doc_fname = ', lpp.main_doc_fname, '  --> bblname =', bblname)
            if self.outbblname:
                outbblname = self.outbblname
            else:
                outbblname = re.sub('(\.(la)?tex)$', '', lpp.main_doc_output_fname) + '.bbl'

            if os.path.getmtime(bblname) < os.path.getmtime(lpp.main_doc_fname):
                logger.warning("BBL file %s might be out-of-date, main tex file %s is more recent",
                               bblname, lpp.main_doc_fname)
            # logger.debug("Copying bbl file %s -> %s", bblname,
            #              os.path.join(lpp.output_dir, outbblname))
            lpp.copy_file(bblname, outbblname)
            #shutil.copy2(bblname, os.path.join(lpp.output_dir, outbblname))
            return r'\input{%s}'%(outbblname)

        return None


class ApplyAliasesFixes(object):
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

        # right away, populate bib aliases with search through given tex files.
        # Hmmm, should we use a latexwalker here in any way? ...?  Not sure it's
        # worth it
        rx_bibalias = re.compile(r'\\'+self.bibaliascmd+'\{(?P<alias>[^}]+)\}\{(?P<target>[^}]+)\}')
        for bfn in bibalias_defs_search_files:
            with open(bfn) as ff:
                for m in rx_bibalias.finditer(ff.read()):
                    alias = m.group('alias')
                    target = m.group('target')
                    logger.debug("Found bibalias %s -> %s", alias, target)
                    self._bibaliases[alias] = target
        self._update_bibaliases()


    def specs(self):
        return dict(macros=[MacroSpec(self.bibaliascmd, '{{')])

    def fix_node(self, n, lpp):
        if n.isNodeType(LatexMacroNode):
            if n.macroname == self.bibaliascmd:
                if not n.nodeargd or not n.nodeargd.argnlist or len(n.nodeargd.argnlist) != 2:
                    logger.warning(r"No arguments or invalid arguments to \bibalias command: %s",
                                   n.latex_verbatim())
                    return None

                alias = n.nodeargd.argnlist[0].latex_verbatim().strip()
                target = n.nodeargd.argnlist[1].latex_verbatim().strip()
                logger.debug("Defined bibalias %s -> %s", alias, target)
                self._bibaliases[alias] = target
                self._update_bibaliases()
                return '' # remove bibalias command from input

            if n.macroname in self.cite_macros:
                if n.nodeargd is None or n.nodeargd.argspec is None or n.nodeargd.argnlist is None:
                    logger.warning(r"Ignoring invalid citation command: %s", n.latex_verbatim())
                    return None
                citargno = n.nodeargd.argspec.find('{')
                ncitarg = n.nodeargd.argnlist[citargno]
                citargnew = self._replace_aliases( lpp.latexpp_group_contents(ncitarg) )

                return '\\'+n.macroname \
                    + lpp.fmt_arglist(n.nodeargd.argspec[:citargno], n.nodeargd.argnlist[:citargno]) \
                    + '{'+citargnew+'}' \
                    + lpp.fmt_arglist(n.nodeargd.argspec[citargno+1:], n.nodeargd.argnlist[citargno+1:])
                

        return None

    def _update_bibaliases(self):
        self._rx_pattern = re.compile(
            "|".join( re.escape(k) for k in sorted(self._bibaliases, key=len, reverse=True) )
        )

    def _replace_aliases(self, s):
        # use multiple string replacements --> apparently we need a regex.
        # Cf. https://stackoverflow.com/a/36620263/1694896
        return self._rx_pattern.sub(lambda m: self._bibaliases[m.group(0)], s)
