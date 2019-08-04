
import os.path
import unittest

import helpers

from latexpp.fixes import macro_subst


class TestSubst(unittest.TestCase):

    def test_simple_1(self):

        lpp = helpers.MockLPP()
        lpp.install_fix( macro_subst.Subst(
            macros={
                'abc': r'\textbf{ABC}',
                'xyz': dict(argspec='*[{', repl=r'\chapter%(1)s[{Opt title: %(2)s}]{Title: %(3)s}')
            },
            environments={
                'equation*': r'\[%(body)s\]'
            }
        ) )

        self.assertEqual(
            lpp.execute(r"""
Hello guys.  Just testin': \abc.

\xyz*{Yo}

\begin{equation*}
  \alpha = \beta
\end{equation*}

\xyz[Hey]{Ya}
"""),
            r"""
Hello guys.  Just testin': \textbf{ABC}.

\chapter*[{Opt title: }]{Title: Yo}

\[
  \alpha = \beta
\]

\chapter[{Opt title: Hey}]{Title: Ya}
"""
        )




if __name__ == '__main__':
    helpers.test_main()
