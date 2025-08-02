
import unittest

import helpers

from latexpp.fixes import labels

class TestRenameLabels(unittest.TestCase):

    maxDiff = None

    def test_simple(self):

        lpp = helpers.MockLPP()
        lpp.install_fix( labels.RenameLabels(use_hash_length=16,
                                             use_hash_encoding='hex') )

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


    def test_cpageref(self):

        lpp = helpers.MockLPP()
        lpp.install_fix( labels.RenameLabels(use_hash_length=16,
                                             use_hash_encoding='hex') )

        self.assertEqual(
            lpp.execute(r"""\documentclass{article}
\begin{document}
Here is equation~\eqref{eq:funny-equation}:
\begin{align}
  a + b = c\ .
  \label{eq:funny-equation}
\end{align}
And here is the glorious~\cpageref{thm:that-arse-of-a-theorem}.
\begin{theorem}
  \label{thm:that-arse-of-a-theorem}
  Theorem statement here.
\end{theorem}
Multiple labels appear here
as~\cpageref{thm:that-arse-of-a-theorem,eq:funny-equation,eq:unknown}.
\end{document}
"""),
            r"""\documentclass{article}
\begin{document}
Here is equation~\eqref{eq:ce3135e517010c8e}:
\begin{align}
  a + b = c\ .
  \label{eq:ce3135e517010c8e}
\end{align}
And here is the glorious~\cpageref{thm:a94d9b09fe949376}.
\begin{theorem}
  \label{thm:a94d9b09fe949376}
  Theorem statement here.
\end{theorem}
Multiple labels appear here
as~\cpageref{thm:a94d9b09fe949376,eq:ce3135e517010c8e,eq:unknown}.
\end{document}
"""
        )


    def test_proof_ref(self):

        lpp = helpers.MockLPP()
        lpp.install_fix( labels.RenameLabels(
            use_hash_length=16,
            use_hash_encoding='hex',
            label_rename_fmt='L.%(hash)s',
            hack_phfthm_proofs=True,
        ) )

        self.assertEqual(
            lpp.execute(r"""\documentclass{article}
\begin{document}
\begin{theorem}
  \label{thm:that-arse-of-a-theorem}
  Theorem statement here.
\end{theorem}
The proof of \cref{thm:that-arse-of-a-theorem} is on
page \cpageref{proof:thm:that-arse-of-a-theorem}.
\begin{proof}[*thm:that-arse-of-a-theorem]
  Proof here.
\end{proof}
\end{document}
"""),
            r"""\documentclass{article}
\begin{document}
\begin{theorem}
  \label{L.a94d9b09fe949376}
  Theorem statement here.
\end{theorem}
The proof of \cref{L.a94d9b09fe949376} is on
page \cpageref{proof:L.a94d9b09fe949376}.
\begin{proof}[*L.a94d9b09fe949376]
  Proof here.
\end{proof}
\end{document}
"""
        )



if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    helpers.test_main()
