
import logging

logger = logging.getLogger(__name__)

from pylatexenc.macrospec import SpecialsSpec, ParsedMacroArgs, MacroStandardArgsParser
from pylatexenc import latexwalker

from latexpp.fixes import BaseFix



class Expand(BaseFix):
    """
    Expand theorem definitions to remove {phfthm} package dependency.
    """
    def __init__(self,
                 deftheorems=['theorem', 'lemma', 'proposition', 'corollary'],
                 proofenvs=dict(proof='proof'),
                 ref_type=r'\cref{%s}', proof_of_name='Proof of %s'):
        super().__init__()

        self.deftheorems = deftheorems
        self.proofenvs = dict(proofenvs)
        self.ref_type = ref_type
        self.proof_of_name = proof_of_name

    def add_preamble(self):

        p = [ ]
        if isinstance(self.deftheorems, str):
            # raw preamble
            p.append(self.deftheorems)
        else:
            p.append(r"\usepackage{amsthm}")
            for t in self.deftheorems:
                p.append( r"\newtheorem{%s}{%s}"%(t, t.capitalize()) )
        return "\n".join(p)
        

    def fix_node(self, n, **kwargs):

        if n.isNodeType(latexwalker.LatexMacroNode) and n.macroname == 'noproofref':
            return ''
        
        if n.isNodeType(latexwalker.LatexEnvironmentNode) and n.environmentname in self.proofenvs:
            proofenv = self.proofenvs[n.environmentname]
            if n.nodeargd.argnlist[0] is not None: # optional argument to proof
                if n.nodeargd.argnlist[0].isNodeType(latexwalker.LatexGroupNode):
                    optargstr = self.nodelist_to_latex(n.nodeargd.argnlist[0].nodelist).strip()
                    if optargstr.startswith('*'):
                        # have \begin{proof}[*thm:label] ... \end{proof}
                        # replace with \begin{proof}[Proof of <ref>] ... \end{proof}
                        reflbl = optargstr[1:]
                        return r'\begin{%s}['%(proofenv) \
                            + self.proof_of_name%(self.ref_type%(reflbl)) + ']' \
                            + self.nodelist_to_latex(n.nodelist) + r'\end{%s}'%(proofenv)

        return None
