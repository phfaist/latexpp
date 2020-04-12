
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
        fix = newcommand.Expand(leave_newcommand=True)
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


    def test_newcommand_cmds(self):
        latex = r"""
\documentclass[11pt]{article}

\newcommand{\a}{Albert Einstein}
\renewcommand\thepage{$-$ \roman{page} $-$}
\providecommand\max[1]{Max #1}

\begin{document}
\a{} and \max{Planck} both thought a lot about quantum mechanics.
\end{document}
"""

        lpp = helpers.MockLPP()
        fix = newcommand.Expand(newcommand_cmds=['newcommand', 'providecommand'],
                                leave_newcommand=False)
        lpp.install_fix( fix )

        self.assertEqual(
            lpp.execute(latex),
            r"""
\documentclass[11pt]{article}


\renewcommand\thepage{$-$ \roman{page} $-$}


\begin{document}
Albert Einstein{} and Max Planck both thought a lot about quantum mechanics.
\end{document}
"""
        )



    def test_macro_blacklist(self):
        latex = r"""
\documentclass[11pt]{article}

\newcommand{\a}{Albert Einstein}
\providecommand\b{Bbbb}
\newcommand\max[1]{Max #1}
\renewcommand\thepage{\roman{page}}

\begin{document}
\a{} and \max{Planck} both thought a lot about quantum mechanics. Some B's: \b.
\end{document}
"""

        lpp = helpers.MockLPP()
        fix = newcommand.Expand(leave_newcommand=False, macro_blacklist_patterns=[r'^b$', r'^the'])
        lpp.install_fix( fix )

        self.assertEqual(
            lpp.execute(latex),
            r"""
\documentclass[11pt]{article}


\providecommand\b{Bbbb}

\renewcommand\thepage{\roman{page}}

\begin{document}
Albert Einstein{} and Max Planck both thought a lot about quantum mechanics. Some B's: \b.
\end{document}
"""
        )



    def test_newenvironment(self):
        latex = r"""
\documentclass[11pt]{article}

\newcommand\Albert{Albert E.}
\newenvironment{testenviron}[2][x]{\texttt{testenviron<#1>{#2}}}{\texttt{endtestenviron}}

\begin{document}
Hello.
\begin{testenviron}\textasciitilde
Environment \textbf{body}, with an equation:
\begin{equation}
   x = y + z\ .
\end{equation}
(Not by \Albert.)
\end{testenviron}
\end{document}
"""

        lpp = helpers.MockLPP()
        fix = newcommand.Expand(newcommand_cmds=['newenvironment'])
        lpp.install_fix( fix )

        self.assertEqual(
            lpp.execute(latex),
            r"""
\documentclass[11pt]{article}

\newcommand\Albert{Albert E.}


\begin{document}
Hello.
{\texttt{testenviron<x>{\textasciitilde
}}Environment \textbf{body}, with an equation:
\begin{equation}
   x = y + z\ .
\end{equation}
(Not by \Albert.)
\texttt{endtestenviron}}
\end{document}
"""
        )

    def test_environment_blacklist(self):
        latex = r"""
\documentclass[11pt]{article}

\newenvironment{testenviron}[2][x]{\texttt{testenviron<#1>{#2}}}{\texttt{endtestenviron}}
\newenvironment{minienviron}{begin}{end}

\begin{document}
Hello.
\begin{testenviron}{Z}
Environment \textbf{body}, with an inner environment:
\begin{minienviron}
Hi!
\end{minienviron}
\end{testenviron}
\end{document}
"""

        lpp = helpers.MockLPP()
        fix = newcommand.Expand(environment_blacklist_patterns=[r'm([a-z])n\1'])
        lpp.install_fix( fix )

        self.assertEqual(
            lpp.execute(latex),
            r"""
\documentclass[11pt]{article}


\newenvironment{minienviron}{begin}{end}

\begin{document}
Hello.
{\texttt{testenviron<x>{Z}}
Environment \textbf{body}, with an inner environment:
\begin{minienviron}
Hi!
\end{minienviron}
\texttt{endtestenviron}}
\end{document}
"""
        )


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    helpers.test_main()
