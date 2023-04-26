
import unittest

import helpers

from latexpp.fixes.pkg import phfqit

class TestExpandMacros(unittest.TestCase):

    def test_simple(self):
        
        latex = r"""
\begin{document}
Ket $\ket\phistate$, bra $\bra\phistate$,
projector $\proj\phistate$,
and a fraction $\frac\phistate 2$.
\begin{gather}
  \Hmax{\hat\rho} = \ldots \\
  \Hmax[\epsilon]{\hat\rho} = \ldots \\
  \Hmin{\hat\sigma} = \ldots \\
  \Hmin[\epsilon']{\hat\sigma} = \ldots
\end{gather}
\end{document}
"""

        lpp = helpers.MockLPP()
        lpp.install_fix(
            phfqit.ExpandMacros(**{
                'ops': {
                    'eig': 'eig',
                    'Proj': 'Proj',
                },
                
                # for kets and bras
                'subst_space': {
                    'phfqitKetsBarSpace': r'\hspace*{0.2ex}',
                    'phfqitKetsRLAngleSpace': r'\hspace*{-0.25ex}',
                },

                'subst': {
                    'phistate': r'\hat\phi',
                    
                    # these macros need to go here and not in 'ExpandQitObjects'
                    # because of their non-standard argument structure
                    'Hmax': {
                        'qitargspec': '[{',
                        'repl': '{S}_{0}^{%(1)s}({%(2)s})',
                    },
                    'Hmin': {
                        'qitargspec': '[{',
                        'repl': r'{S}_{\infty}^{%(1)s}({%(2)s})',
                    },
                },
            })
        )

        result = lpp.execute(latex)

        self.assertEqual(
            result,
            r"""
\begin{document}
Ket $\lvert {\hat\phi}\rangle $, bra $\langle {\hat\phi}\rvert $,
projector $\lvert {\hat\phi}\rangle \hspace*{-0.25ex}\langle{\hat\phi}\rvert $,
and a fraction $\frac{\hat\phi}2$.
\begin{gather}
  {S}_{0}^{}({\hat\rho}) = \ldots \\
  {S}_{0}^{\epsilon}({\hat\rho}) = \ldots \\
  {S}_{\infty}^{}({\hat\sigma}) = \ldots \\
  {S}_{\infty}^{\epsilon'}({\hat\sigma}) = \ldots
\end{gather}
\end{document}
"""
        )



if __name__ == '__main__':
    helpers.test_main()
