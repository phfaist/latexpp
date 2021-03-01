
import unittest

import helpers

from latexpp.fixes import ifsimple

class TestApplyIf(unittest.TestCase):

    def test_iftrue(self):
        
        lpp = helpers.MockLPP()
        lpp.install_fix(ifsimple.ApplyIf())

        self.assertEqual(
            lpp.execute(r"""
\iftrue TRUE\fi
"""),
            r"""
TRUE"""
        )

    def test_iftrue_else(self):
        
        lpp = helpers.MockLPP()
        lpp.install_fix(ifsimple.ApplyIf())

        self.assertEqual(
            lpp.execute(r"""
\iftrue TRUE\else FALSE\fi
"""),
            r"""
TRUE"""
        )

    def test_iffalse(self):
        
        lpp = helpers.MockLPP()
        lpp.install_fix(ifsimple.ApplyIf())

        self.assertEqual(
            lpp.execute(r"""
\iffalse TRUE\fi
"""),
            r"""
"""
        )

    def test_iffalse_else(self):
        
        lpp = helpers.MockLPP()
        lpp.install_fix(ifsimple.ApplyIf())

        self.assertEqual(
            lpp.execute(r"""
\iffalse TRUE\else FALSE\fi
"""),
            r"""
FALSE"""
        )


    def test_nested_ifs_1(self):
        
        lpp = helpers.MockLPP()
        lpp.install_fix(ifsimple.ApplyIf())

        self.assertEqual(
            lpp.execute(r"""
\iftrue
  \iffalse
    A-A
  \else
    A-B
    \iffalse\else
      A-B-A
    \fi
  \fi
\fi
"""),
            r"""
A-B
    A-B-A
    """
        )



    def test_newif(self):
        
        lpp = helpers.MockLPP()
        lpp.install_fix(ifsimple.ApplyIf())

        self.assertEqual(
            lpp.execute(r"""
\newif\ifA
\Atrue
\newif\ifB
\ifB
  \Afalse
\else
  \ifA A is TRUE!\fi
\fi
"""),
                        r"""
A is TRUE!"""
        )


    def test_in_groups_and_environments(self):
        
        lpp = helpers.MockLPP()
        lpp.install_fix(ifsimple.ApplyIf())

        self.assertEqual(
            lpp.execute(r"""
\newif\ifA
\Atrue
\newif\ifB
\begin{document}
\ifB
  \Afalse
\else
  \textbf{\ifA A is TRUE!\fi}
\fi
\end{document}
"""),
                        r"""
\begin{document}
\textbf{A is TRUE!}
\end{document}
"""
        )





if __name__ == '__main__':
    helpers.test_main()
