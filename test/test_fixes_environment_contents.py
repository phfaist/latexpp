
import unittest

import helpers

from latexpp.fixes import environment_contents

class TestInsertPrePost(unittest.TestCase):

    def test_post_contents(self):
        
        lpp = helpers.MockLPP()
        lpp.install_fix(
            environment_contents.InsertPrePost(
                environmentnames=['proof','myproof'],
                post_contents=r'\qed',
            )
        )

        self.assertEqual(
            lpp.execute(r"""
\documentclass{article}
\begin{document}
Hello world.
\begin{proof}
  Proof of this and that.
\end{proof}
\end{document}
"""),
            r"""
\documentclass{article}
\begin{document}
Hello world.
\begin{proof}
  Proof of this and that.
\qed\end{proof}
\end{document}
"""
        )

    def test_pre_contents(self):
        
        lpp = helpers.MockLPP()
        lpp.install_fix(
            environment_contents.InsertPrePost(
                environmentnames=['proof','myproof'],
                pre_contents='\n'+r'(proof \textbf{starts} here)',
            )
        )

        self.assertEqual(
            lpp.execute(r"""
\documentclass{article}
\begin{document}
Hello world.
\begin{proof}
  Proof of this and that.
\end{proof}
\end{document}
"""),
            r"""
\documentclass{article}
\begin{document}
Hello world.
\begin{proof}
(proof \textbf{starts} here)
  Proof of this and that.
\end{proof}
\end{document}
"""
        )






if __name__ == '__main__':
    helpers.test_main()
