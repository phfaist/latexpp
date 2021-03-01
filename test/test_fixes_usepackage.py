
import unittest

import helpers

from latexpp.fixes import usepackage

class TestRemovePkgs(unittest.TestCase):

    def test_simple(self):
        
        lpp = helpers.MockLPP()
        lpp.install_fix( usepackage.RemovePkgs(['phfparen', 'mymacros']) )

        self.assertEqual(
            lpp.execute(r"""
\documentclass{article}

\usepackage{amsmath}
\usepackage{phfparen}
\usepackage[someoptions,moreoptions]{mymacros}%

\begin{document}
Hello world.
\end{document}
"""),
            r"""
\documentclass{article}

\usepackage{amsmath}

%

\begin{document}
Hello world.
\end{document}
"""
        )


class TestCopyLocalPkgs(unittest.TestCase):

    def test_simple(self):
        
        mock_files = {
            # list of files that "exist"
            "mymacros.sty": "%test",
            "cleveref.sty": "%test",
        }
        usepackage.os_path = helpers.FakeOsPath(list(mock_files.keys()))

        lpp = helpers.MockLPP(mock_files)
        lpp.install_fix( usepackage.CopyLocalPkgs() )

        lpp.execute(r"""
\documentclass{article}

\usepackage{amsmath}
\usepackage{phfparen}
\usepackage[someoptions,moreoptions]{mymacros}%
\usepackage{cleveref}

\begin{document}
Hello world.
\end{document}
""")
        self.assertEqual(
            lpp.copied_files,
            [
                ('mymacros.sty', '/TESTOUT/mymacros.sty'),
                ('cleveref.sty', '/TESTOUT/cleveref.sty'),
            ]
        )







if __name__ == '__main__':
    helpers.test_main()
