
import unittest

import helpers

from latexpp.fixes import input

class TestEvalInput(unittest.TestCase):

    def test_simple(self):
        
        input.os_path = helpers.FakeOsPath([
            # list of files that "exist"
            'chapter1.tex',
            'chapter2.latex',
        ])

        ei = input.EvalInput()

        ei._read_file_contents = lambda fn: {
            'chapter1.tex': r"""
\chapter[first]{Chapter uno}
This is the \emph{contents} of ``Chapter 1.''
""",
            'chapter2.latex': r"""\chapter{The second of chapters}
Here is the \textbf{contents} of ``Chapter 2!''
""",
        }.get(fn)

        lpp = helpers.MockLPP()
        lpp.install_fix( ei )

        self.assertEqual(
            lpp.execute(r"""
Hello, this might be an introduction:
\[ a + b = c\ . \]

\input{chapter1.tex}

\include{chapter2}
"""),
            r"""
Hello, this might be an introduction:
\[ a + b = c\ . \]


\chapter[first]{Chapter uno}
This is the \emph{contents} of ``Chapter 1.''


\clearpage
\chapter{The second of chapters}
Here is the \textbf{contents} of ``Chapter 2!''

"""
        )

        self.assertEqual(
            lpp.copied_files,
            [ ]
        )



class TestCopyInputDeps(unittest.TestCase):

    def test_simple(self):
        
        input.os_path = helpers.FakeOsPath([
            # list of files that "exist"
            'chapter1.tex',
            'chapter2.latex',
        ])

        mock_files = {
            'chapter1.tex': r"""
\chapter[first]{Chapter uno}
This is the \emph{contents} of ``Chapter 1.''
""",
            'chapter2.latex': r"""\chapter{The second of chapters}
Here is the \textbf{contents} of ``Chapter 2!''
""",
        }

        lpp = helpers.MockLPP(mock_files=mock_files)
        lpp.install_fix( input.CopyInputDeps() )

        self.assertEqual(
            lpp.execute(r"""
Hello, this might be an introduction:
\[ a + b = c\ . \]

\input{chapter1.tex}

\include{chapter2}
"""),
            r"""
Hello, this might be an introduction:
\[ a + b = c\ . \]

\input{chapter1.tex}

\include{chapter2}
"""
        ) # no change

        self.assertEqual(
            lpp.wrote_executed_files,
            mock_files
        )



if __name__ == '__main__':
    helpers.test_main()
