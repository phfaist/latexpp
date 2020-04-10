
import unittest

import helpers

from latexpp.fixes.pkg import cleveref

class TestApplyAliases(unittest.TestCase):

    maxDiff = None

    def test_simple(self):
        
        latex = r"""
\documentclass[11pt]{article}

\usepackage{amsthm}
\newtheorem{lemma}{Lemma}

\usepackage{hyperref}
\usepackage{cleveref}

\begin{document}
A reference to \cref{lemma:test}. \Cref{lemma:test2} on
 \cpageref{lemma:test2} is nice, too.

Here is a lemma:
\begin{lemma}
  \label{lemma:test}
  Test lemma. 
\end{lemma}
And here is another lemma:
\begin{lemma}
  \label{lemma:test2}
  Another test lemma.
\end{lemma}
\end{document}
"""

        lpp = helpers.MockLPP()
        fix = cleveref.ResolveCleverefs()
        fix._get_auxfile_contents = lambda: r"""
\relax 
\providecommand\hyper@newdestlabel[2]{}
\providecommand\HyperFirstAtBeginDocument{\AtBeginDocument}
\HyperFirstAtBeginDocument{\ifx\hyper@anchor\@undefined
\global\let\oldcontentsline\contentsline
\gdef\contentsline#1#2#3#4{\oldcontentsline{#1}{#2}{#3}}
\global\let\oldnewlabel\newlabel
\gdef\newlabel#1#2{\newlabelxx{#1}#2}
\gdef\newlabelxx#1#2#3#4#5#6{\oldnewlabel{#1}{{#2}{#3}}}
\AtEndDocument{\ifx\hyper@anchor\@undefined
\let\contentsline\oldcontentsline
\let\newlabel\oldnewlabel
\fi}
\fi}
\global\let\hyper@last\relax 
\gdef\HyperFirstAtBeginDocument#1{#1}
\providecommand\HyField@AuxAddToFields[1]{}
\providecommand\HyField@AuxAddToCoFields[2]{}
\newlabel{lemma:test}{{1}{1}{}{lemma.1}{}}
\newlabel{lemma:test@cref}{{[lemma][1][]1}{1}}
\newlabel{lemma:test2}{{2}{1}{}{lemma.2}{}}
\newlabel{lemma:test2@cref}{{[lemma][2][]2}{1}}
"""
        lpp.install_fix( fix )

        self.assertEqual(
            lpp.execute(latex),
            # NOTE: KEEP \protect in output, because the substitution might
            # happen somewhere fragile.
            r"""
\documentclass[11pt]{article}

\usepackage{amsthm}
\newtheorem{lemma}{Lemma}

\usepackage{hyperref}
\usepackage{cleveref}

\begin{document}
A reference to lemma\protect \nobreakspace  1. Lemma\protect \nobreakspace  2 on
 page\protect \nobreakspace  1 is nice, too.

Here is a lemma:
\begin{lemma}
  \label{lemma:test}
  Test lemma. 
\end{lemma}
And here is another lemma:
\begin{lemma}
  \label{lemma:test2}
  Another test lemma.
\end{lemma}
\end{document}
"""
        )




if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    helpers.test_main()
