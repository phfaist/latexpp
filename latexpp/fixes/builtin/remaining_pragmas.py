import logging

logger = logging.getLogger(__name__)

#from pylatexenc import latexwalker

from latexpp.pragma_fix import PragmaFix


class ReportRemainingPragmas(PragmaFix):
    
    def fix_pragma_scope(self, nodelist, jstart, jend, instruction, args):
        n = nodelist[jstart]
        ne = nodelist[jend-1]
        logger.warning(
            "Found unconsumed pragma ‘%s’, did you forget to invoke a fix? "
            "on lines %d--%d (?)",
            n.comment,
            n.parsing_state.lpp_latex_walker.pos_to_lineno_colno(n.pos)[0],
            ne.parsing_state.lpp_latex_walker.pos_to_lineno_colno(ne.pos)[0]
        )

    def fix_pragma_simple(self, nodelist, j, instruction, args):
        n = nodelist[j]
        logger.warning(
            "Found unconsumed pragma ‘%s’, did you forget to invoke a fix? "
            "on line %d (?)",
            n.comment,
            n.parsing_state.lpp_latex_walker.pos_to_lineno_colno(n.pos)[0]
        )

