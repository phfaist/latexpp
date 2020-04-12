
import unittest

import helpers

from latexpp.fixes import bib

class TestApplyAliases(unittest.TestCase):

    def test_simple(self):
        
        latex = r"""
\bibalias{alias1}{target1}
\bibalias{alias2}{target2}
\begin{document}
Some text~\cite{alias1,target3} and see also~\citep{alias2}.
\bibliography{mybib1,bib2}
\end{document}
"""

        lpp = helpers.MockLPP( mock_files={
            'TESTDOC.bbl': r"\relax\bibdata{XYZ}\bibcite{mybib1}{24}" # etc. this is random stuff here
})
        lpp.install_fix( bib.CopyAndInputBbl() )
        lpp.install_fix( bib.ApplyAliases() )

        self.assertEqual(
            lpp.execute(latex),
            r"""


\begin{document}
Some text~\cite{target1,target3} and see also~\citep{target2}.
\input{TESTMAIN.bbl}
\end{document}
"""
        )

        self.assertEqual(lpp.copied_files, [('TESTDOC.bbl', '/TESTOUT/TESTMAIN.bbl')])




if __name__ == '__main__':
    helpers.test_main()
