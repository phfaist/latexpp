
import unittest

import helpers

from latexpp.fixes import newcommand


class TestExpand(unittest.TestCase):

    maxDiff = None

    def test_simple(self):
        
        latex = r"""
\documentclass[11pt]{article}

\newcommand{\a}{Albert Einstein}
\newcommand\max[1]{Max #1}

\begin{document}
\a{} and \max{Planck} both thought a lot about quantum mechanics.
\end{document}
"""

        lpp = helpers.MockLPP()
        fix = newcommand.Expand()
        lpp.install_fix( fix )

        self.assertEqual(
            lpp.execute(latex),
            r"""
\documentclass[11pt]{article}

\newcommand{\a}{Albert Einstein}
\newcommand\max[1]{Max #1}

\begin{document}
Albert Einstein{} and Max Planck both thought a lot about quantum mechanics.
\end{document}
"""
        )

    def test_noleave(self):
        
        latex = r"""
\documentclass[11pt]{article}

\newcommand{\a}{Albert Einstein}
\newcommand\max[1]{Max #1}
\renewcommand\thepage{\roman{page}}

\begin{document}
\a{} and \max{Planck} both thought a lot about quantum mechanics.
\end{document}
"""

        lpp = helpers.MockLPP()
        fix = newcommand.Expand(leave_newcommand=False)
        lpp.install_fix( fix )

        self.assertEqual(
            lpp.execute(latex),
            r"""
\documentclass[11pt]{article}



\renewcommand\thepage{\roman{page}}

\begin{document}
Albert Einstein{} and Max Planck both thought a lot about quantum mechanics.
\end{document}
"""
        )


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    helpers.test_main()
