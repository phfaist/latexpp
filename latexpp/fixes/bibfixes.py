import re
import shutil
import logging

logger = logging.getLogger(__name__)

from pylatexenc.latexwalker import LatexCommentNode


class FixInputBbl(object):
    def __init__(self, bblname='main', outbblname='main.bbl'):
        self.bblname = bblname
        self.outbblname = outbblname

    def fix_node(self, n, lpp):
        if n.isNodeType(LatexMacroNode) and n.macroname == 'bibliography':
            # check modif time wrt main tex file
            if os.path.getmtime(self.bblname) < os.path.getmtime(lpp.main_doc_fname):
                logger.warning("BBL file %s might be out-of-date, main tex file %s is more recent",
                               self.bblname, lpp.main_doc_fname)
            shutil.copy2(self.bblname, os.path.join(lpp.output_dir, self.outbblname))
            return r'\input{%s}'%(self.bblname)

        return None


class FixBibaliases(object):
    def __init__(self, bibaliascmd='bibalias', bibalias_defs_search_files=None):
        self.bibaliascmd = bibaliascmd
        self.bibalias_defs_search_files = bibalias_defs_search_files

        # which argument has the keys is obtained from the argspec as the first
        # mandatory argument
        self.cite_macros = set('cite', 'citet', 'citep', 'citealt', 'citealp',
                               'citeauthor', 'citefullauthor', 'citeyear', 'citeyearpar',
                               'Citet', 'Citep', 'Citealt', 'Citealp', 'Citeauthor',
                               'citenum',)

        self._bibaliases = {}

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
                citargnew = self._replace_aliases( lpp.latexpp(ncitarg) )

                return n.macroname \
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
