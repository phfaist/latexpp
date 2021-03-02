
import unittest

import helpers

from latexpp.fixes import labels

class TestExpandRefs(unittest.TestCase):

    maxDiff = None

    def test_simple(self):

        lpp = helpers.MockLPP()
        lpp.install_fix( labels.RenameLabels() )

        self.assertEqual(
            lpp.execute(r"""\documentclass{article}
\begin{document}
Here is equation~\eqref{eq:funny-equation}:
\begin{align}
  a + b = c\ .
  \label{eq:funny-equation}
\end{align}
And here is the glorious~\cref{thm:that-arse-of-a-theorem}.
\begin{theorem}
  \label{thm:that-arse-of-a-theorem}
  Theorem statement here.
\end{theorem}
Multiple labels appear here
as~\cref{thm:that-arse-of-a-theorem,eq:funny-equation,eq:unknown}.
\end{document}
"""),
            r"""\documentclass{article}
\begin{document}
Here is equation~\eqref{eq:ce3135e517010c8e}:
\begin{align}
  a + b = c\ .
  \label{eq:ce3135e517010c8e}
\end{align}
And here is the glorious~\cref{thm:a94d9b09fe949376}.
\begin{theorem}
  \label{thm:a94d9b09fe949376}
  Theorem statement here.
\end{theorem}
Multiple labels appear here
as~\cref{thm:a94d9b09fe949376,eq:ce3135e517010c8e,eq:unknown}.
\end{document}
"""
        )





if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    helpers.test_main()
