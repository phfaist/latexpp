
import unittest

import helpers

from latexpp.fixes import ref


hyperref_aux_preamble = r"""\relax 
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
"""


class TestExpandRefs(unittest.TestCase):

    maxDiff = None

    def test_flags_ref_types(self):

        fix = ref.ExpandRefs(only_ref_types='ref')
        self.assertEqual(fix.ref_types, ['ref'])
        fix = ref.ExpandRefs(only_ref_types='cleveref')
        self.assertEqual(fix.ref_types, ['cleveref'])
        fix = ref.ExpandRefs(only_ref_types=['ref', 'ams-eqref'])
        self.assertEqual(fix.ref_types, ['ref', 'ams-eqref'])
        fix = ref.ExpandRefs(only_ref_types=set(['ref', 'ams-eqref']))
        self.assertEqual(set(fix.ref_types), set(['ref', 'ams-eqref']))

    def test_simple_ref(self):
        
        latex = r"""
\documentclass[11pt]{article}

\usepackage{amsthm}
\newtheorem{lemma}{Lemma}

\begin{document}
Equation~(\ref{eq:test}) on page~\pageref{eq:test} reads:
\begin{equation}
  \label{eq:test}
  a + b = c\ .
\end{equation}
\end{document}
"""

        lpp = helpers.MockLPP()
        fix = ref.ExpandRefs(only_ref_types='ref', debug_latex_output=True)
        fix._get_auxfile_contents = lambda: r"""
\relax 
\newlabel{eq:test}{{1}{1}}
"""
        lpp.install_fix( fix )

        # NOTE: KEEP \protect's in output, because the substitution might happen
        # somewhere fragile.
        self.assertEqual(
            lpp.execute(latex),
            r"""
\documentclass[11pt]{article}

\usepackage{amsthm}
\newtheorem{lemma}{Lemma}

\begin{document}
Equation~(1) on page~1 reads:
\begin{equation}
  \label{eq:test}
  a + b = c\ .
\end{equation}
\end{document}
"""
        )

    def test_simple_ref_with_hyperref(self):
        
        latex = r"""
\documentclass[11pt]{article}

\usepackage{amsthm}
\newtheorem{lemma}{Lemma}

\usepackage{hyperref}

\begin{document}
Equation~(\ref{eq:test}) [Eq.~(\ref*{eq:test}) without link]:
\begin{equation}
  \label{eq:test}
  a + b = c\ .
\end{equation}
\end{document}
"""

        lpp = helpers.MockLPP()
        fix = ref.ExpandRefs(only_ref_types='ref', debug_latex_output=True)
        fix._get_auxfile_contents = lambda: hyperref_aux_preamble + r"""
\newlabel{eq:test}{{1}{1}{}{equation.0.1}{}}
"""
        lpp.install_fix( fix )

        # NOTE: KEEP \protect's in output, because the substitution might happen
        # somewhere fragile.
        self.assertEqual(
            lpp.execute(latex),
            r"""
\documentclass[11pt]{article}

\usepackage{amsthm}
\newtheorem{lemma}{Lemma}

\usepackage{hyperref}

\begin{document}
Equation~(\protect \hyperref [eq:test]{1}) [Eq.~(1) without link]:
\begin{equation}
  \label{eq:test}
  a + b = c\ .
\end{equation}
\end{document}
"""
        )

    def test_simple_ref_with_hyperref_nolink(self):
        
        latex = r"""
\documentclass[11pt]{article}

\usepackage{amsthm}
\newtheorem{lemma}{Lemma}

\usepackage{hyperref}

\begin{document}
Equation~(\ref{eq:test}) [Eq.~(\ref*{eq:test}) without link]:
\begin{equation}
  \label{eq:test}
  a + b = c\ .
\end{equation}
\end{document}
"""

        lpp = helpers.MockLPP()
        fix = ref.ExpandRefs(only_ref_types='ref', make_hyperlinks=False, debug_latex_output=True)
        fix._get_auxfile_contents = lambda: hyperref_aux_preamble + r"""
\newlabel{eq:test}{{1}{1}{}{equation.0.1}{}}
"""
        lpp.install_fix( fix )

        # NOTE: KEEP \protect's in output, because the substitution might happen
        # somewhere fragile.
        self.assertEqual(
            lpp.execute(latex),
            r"""
\documentclass[11pt]{article}

\usepackage{amsthm}
\newtheorem{lemma}{Lemma}

\usepackage{hyperref}

\begin{document}
Equation~(1) [Eq.~(1) without link]:
\begin{equation}
  \label{eq:test}
  a + b = c\ .
\end{equation}
\end{document}
"""
        )
        

    def test_simple_eqref(self):
        
        latex = r"""
\documentclass[11pt]{article}

\usepackage{amsmath}
\usepackage{amsthm}
\newtheorem{lemma}{Lemma}

\begin{document}
Equation~\eqref{eq:test} reads:
\begin{equation}
  \label{eq:test}
  a + b = c\ .
\end{equation}
\end{document}
"""

        lpp = helpers.MockLPP()
        fix = ref.ExpandRefs(only_ref_types='ams-eqref', debug_latex_output=True)
        fix._get_auxfile_contents = lambda: r"""
\relax 
\newlabel{eq:test}{{1}{1}}
"""
        lpp.install_fix( fix )

        # NOTE: KEEP \protect's in output, because the substitution might happen
        # somewhere fragile.
        self.assertEqual(
            lpp.execute(latex),
            r"""
\documentclass[11pt]{article}

\usepackage{amsmath}
\usepackage{amsthm}
\newtheorem{lemma}{Lemma}

\begin{document}
Equation~\protect \textup  {\mathsurround \z@ \protect \normalfont  (\ignorespaces 1\unskip \@@italiccorr )} reads:
\begin{equation}
  \label{eq:test}
  a + b = c\ .
\end{equation}
\end{document}
"""
        )

    def test_simple_eqref_with_hyperref(self):
        
        latex = r"""
\documentclass[11pt]{article}

\usepackage{amsmath}
\usepackage{amsthm}
\newtheorem{lemma}{Lemma}

\usepackage{hyperref}

\begin{document}
Equation~\eqref{eq:test}:
\begin{equation}
  \label{eq:test}
  a + b = c\ .
\end{equation}
\end{document}
"""

        lpp = helpers.MockLPP()
        fix = ref.ExpandRefs(only_ref_types='ams-eqref', debug_latex_output=True)
        fix._get_auxfile_contents = lambda: hyperref_aux_preamble + r"""
\newlabel{eq:test}{{1}{1}{}{equation.0.1}{}}
"""
        lpp.install_fix( fix )

        # NOTE: KEEP \protect's in output, because the substitution might happen
        # somewhere fragile.
        self.assertEqual(
            lpp.execute(latex),
            r"""
\documentclass[11pt]{article}

\usepackage{amsmath}
\usepackage{amsthm}
\newtheorem{lemma}{Lemma}

\usepackage{hyperref}

\begin{document}
Equation~\protect \textup  {\mathsurround \z@ \protect \normalfont  (\ignorespaces \protect \hyperref [eq:test]{1}\unskip \@@italiccorr )}:
\begin{equation}
  \label{eq:test}
  a + b = c\ .
\end{equation}
\end{document}
"""
        )
        

        
    def test_simple_cref(self):
        
        latex = r"""
\documentclass[11pt]{article}

\usepackage{amsthm}
\newtheorem{lemma}{Lemma}

\usepackage{hyperref}
\usepackage{cleveref}

\begin{document}
A reference to \cref{lemma:test}. \Cref{lemma:test2} on
 \cpageref{lemma:test2} is nice, too. \Cpageref{lemma:test2}
is what that was.

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
        fix = ref.ExpandRefs(debug_latex_output=True)
        fix._get_auxfile_contents = lambda: hyperref_aux_preamble + r"""
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


\begin{document}
A reference to lemma\protect \nobreakspace  \protect \hyperlink {lemma.1}{1}. Lemma\protect \nobreakspace  \protect \hyperlink {lemma.2}{2} on
 page\protect \nobreakspace  \protect \hyperlink {lemma.2}{1} is nice, too. Page\protect \nobreakspace  \protect \hyperlink {lemma.2}{1}
is what that was.

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

    def test_simple_cref_nolink(self):
        
        latex = r"""
\documentclass[11pt]{article}

\usepackage{amsthm}
\newtheorem{lemma}{Lemma}

\usepackage{hyperref}
\usepackage{cleveref}

\begin{document}
A reference to \cref{lemma:test}. \Cref{lemma:test2} on
 \cpageref{lemma:test2} is nice, too. \Cpageref{lemma:test2}
is what that was.

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
        fix = ref.ExpandRefs(make_hyperlinks=False, debug_latex_output=True)
        fix._get_auxfile_contents = lambda: hyperref_aux_preamble + r"""
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


\begin{document}
A reference to lemma\protect \nobreakspace  1. Lemma\protect \nobreakspace  2 on
 page\protect \nobreakspace  1 is nice, too. Page\protect \nobreakspace  1
is what that was.

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


    def test_simple_cref_nohyperrefloaded(self):
        
        latex = r"""
\documentclass[11pt]{article}

\usepackage{amsthm}
\newtheorem{lemma}{Lemma}

\usepackage{cleveref}

\begin{document}
A reference to \cref{lemma:test}. \Cref{lemma:test2} on
 \cpageref{lemma:test2} is nice, too. \Cpageref{lemma:test2}
is what that was.

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
        fix = ref.ExpandRefs(make_hyperlinks=True, debug_latex_output=True)
        fix._get_auxfile_contents = lambda: r"""
\newlabel{lemma:test}{{1}{1}}
\newlabel{lemma:test@cref}{{[lemma][1][]1}{1}}
\newlabel{lemma:test2}{{2}{1}}
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



\begin{document}
A reference to lemma\protect \nobreakspace  1. Lemma\protect \nobreakspace  2 on
 page\protect \nobreakspace  1 is nice, too. Page\protect \nobreakspace  1
is what that was.

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


    def test_simple_crefrange(self):
        
        latex = r"""
\documentclass[11pt]{article}

\usepackage{amsthm}
\newtheorem{lemma}{Lemma}

\usepackage{hyperref}
\usepackage{cleveref}

\begin{document}
Ranges should work, too, like this:
\crefrange{lemma:test}{lemma:test2} on
\cpagerefrange{lemma:test}{lemma:test2}, as well as their
capitalized versions: \Crefrange{lemma:test}{lemma:test2};
\Cpagerefrange{lemma:test}{lemma:test2}.

Here is a lemma:
\begin{lemma}
  \label{lemma:test}
  Test lemma. 
\end{lemma}
Here is an equation
\begin{equation}
  \label{eq:hello}
  a + b = c \ .
\end{equation}
And here is another lemma:
\begin{lemma}
  \label{lemma:test2}
  Another test lemma.
\end{lemma}
\end{document}
"""

        lpp = helpers.MockLPP()
        fix = ref.ExpandRefs(debug_latex_output=True)
        fix._get_auxfile_contents = lambda: hyperref_aux_preamble + r"""
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


\begin{document}
Ranges should work, too, like this:
lemmas\protect \nobreakspace  \protect \hyperlink {lemma.1}{1} to\protect \nobreakspace  \protect \hyperlink {lemma.2}{2} on
pages\protect \nobreakspace  \protect \hyperlink {lemma.1}{1} to\protect \nobreakspace  \protect \hyperlink {lemma.2}{1}, as well as their
capitalized versions: Lemmas\protect \nobreakspace  \protect \hyperlink {lemma.1}{1} to\protect \nobreakspace  \protect \hyperlink {lemma.2}{2};
Pages\protect \nobreakspace  \protect \hyperlink {lemma.1}{1} to\protect \nobreakspace  \protect \hyperlink {lemma.2}{1}.

Here is a lemma:
\begin{lemma}
  \label{lemma:test}
  Test lemma. 
\end{lemma}
Here is an equation
\begin{equation}
  \label{eq:hello}
  a + b = c \ .
\end{equation}
And here is another lemma:
\begin{lemma}
  \label{lemma:test2}
  Another test lemma.
\end{lemma}
\end{document}
"""
        )

    def test_simple_crefrange_nolink(self):
        
        latex = r"""
\documentclass[11pt]{article}

\usepackage{amsthm}
\newtheorem{lemma}{Lemma}

\usepackage{hyperref}
\usepackage{cleveref}

\begin{document}
Ranges should work, too, like this:
\crefrange{lemma:test}{lemma:test2} on
\cpagerefrange{lemma:test}{lemma:test2}, as well as their
capitalized versions: \Crefrange{lemma:test}{lemma:test2};
\Cpagerefrange{lemma:test}{lemma:test2}.

Here is a lemma:
\begin{lemma}
  \label{lemma:test}
  Test lemma. 
\end{lemma}
Here is an equation
\begin{equation}
  \label{eq:hello}
  a + b = c \ .
\end{equation}
And here is another lemma:
\begin{lemma}
  \label{lemma:test2}
  Another test lemma.
\end{lemma}
\end{document}
"""

        lpp = helpers.MockLPP()
        fix = ref.ExpandRefs(make_hyperlinks=False, debug_latex_output=True)
        fix._get_auxfile_contents = lambda: hyperref_aux_preamble + r"""
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


\begin{document}
Ranges should work, too, like this:
lemmas\protect \nobreakspace  1 to\protect \nobreakspace  2 on
pages\protect \nobreakspace  1 to\protect \nobreakspace  1, as well as their
capitalized versions: Lemmas\protect \nobreakspace  1 to\protect \nobreakspace  2;
Pages\protect \nobreakspace  1 to\protect \nobreakspace  1.

Here is a lemma:
\begin{lemma}
  \label{lemma:test}
  Test lemma. 
\end{lemma}
Here is an equation
\begin{equation}
  \label{eq:hello}
  a + b = c \ .
\end{equation}
And here is another lemma:
\begin{lemma}
  \label{lemma:test2}
  Another test lemma.
\end{lemma}
\end{document}
"""
        )


    def test_simple_namecref(self):
        
        latex = r"""
\documentclass[11pt]{article}

\usepackage{amsthm}
\newtheorem{lemma}{Lemma}

\usepackage{hyperref}
\usepackage{cleveref}

\begin{document}

The proof of the \namecref{lemma:test2} is easy.
\nameCrefs{lemma:test2} like these are simple to prove.
``\nameCref{eq:hello}'' should work too (we'll add more
\namecrefs{eq:hello} in the future), and so should
``\lcnamecref{eq:hello}'' and ``\lcnamecrefs{eq:hello}.''

Here is a lemma:
\begin{lemma}
  \label{lemma:test}
  Test lemma. 
\end{lemma}
Here is an equation
\begin{equation}
  \label{eq:hello}
  a + b = c \ .
\end{equation}
And here is another lemma:
\begin{lemma}
  \label{lemma:test2}
  Another test lemma.
\end{lemma}
\end{document}
"""

        lpp = helpers.MockLPP()
        fix = ref.ExpandRefs(only_ref_types=('cleveref',), debug_latex_output=True)
        fix._get_auxfile_contents = lambda: hyperref_aux_preamble + r"""
\newlabel{lemma:test}{{1}{1}{}{lemma.1}{}}
\newlabel{lemma:test@cref}{{[lemma][1][]1}{1}}
\newlabel{eq:hello}{{1}{1}{}{equation.0.1}{}}
\newlabel{eq:hello@cref}{{[equation][1][]1}{1}}
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


\begin{document}

The proof of the lemma is easy.
Lemmas like these are simple to prove.
``Equation'' should work too (we'll add more
eqs. in the future), and so should
``\protect \MakeLowercase Equation'' and ``\protect \MakeLowercase Equations.''

Here is a lemma:
\begin{lemma}
  \label{lemma:test}
  Test lemma. 
\end{lemma}
Here is an equation
\begin{equation}
  \label{eq:hello}
  a + b = c \ .
\end{equation}
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
