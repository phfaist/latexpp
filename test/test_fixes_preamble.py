
import unittest

import helpers

from latexpp.fixes import preamble

class TestAddPreamble(unittest.TestCase):

    def test_simple(self):
        
        lpp = helpers.MockLPP()
        lpp.install_fix( preamble.AddPreamble(preamble=r"""
% use this package:
\usepackage{mycoolpackage}

% also keep these definitions:
\newcommand\hello[2][world]{Hello #1. #2}
""") )

        self.assertEqual(
            lpp.execute(r"""
\documentclass{article}

\usepackage{amsmath}

\begin{document}
Hello world.
\end{document}
"""),
            r"""
\documentclass{article}

\usepackage{amsmath}


%%%

% use this package:
\usepackage{mycoolpackage}

% also keep these definitions:
\newcommand\hello[2][world]{Hello #1. #2}

%%%
\begin{document}
Hello world.
\end{document}
"""
        )






if __name__ == '__main__':
    helpers.test_main()
