
import os.path
import unittest

import helpers

from latexpp.fixes import figures


class TestCopyAndRenameFigs(unittest.TestCase):

    def test_simple_1(self):

        figures.os_path = helpers.FakeOsPath([
            # list of files that "exist"
            'fig/intro.png',
            'my_diagram.jpg',
            'v088338-1993.out.eps',
            'fignew/results schematic.pdf',
            'fignew/results schematic 2.jpg'
        ])
        
        lpp = helpers.MockLPP()
        lpp.install_fix( figures.CopyAndRenameFigs() )

        self.assertEqual(
            lpp.execute(r"""
                \includegraphics[width=\textwidth]{fig/intro}
                \includegraphics[width=\textwidth]{my_diagram.jpg}
                \includegraphics{fignew/results schematic}
                \includegraphics{v088338-1993.out}
            """),
            r"""
                \includegraphics[width=\textwidth]{fig-01.png}
                \includegraphics[width=\textwidth]{fig-02.jpg}
                \includegraphics{fig-03.pdf}
                \includegraphics{fig-04.eps}
            """
        )

        self.assertEqual(
            lpp.copied_files,
            [
                ('fig/intro.png', '/TESTOUT/fig-01.png'),
                ('my_diagram.jpg', '/TESTOUT/fig-02.jpg'),
                ('fignew/results schematic.pdf', '/TESTOUT/fig-03.pdf'),
                ('v088338-1993.out.eps', '/TESTOUT/fig-04.eps'),
            ]
        )

    def test_simple_2(self):

        figures.os_path = helpers.FakeOsPath([
            # list of files that "exist"
            'fig/intro.png',
            'my_diagram.jpg',
            'v088338-1993.out.eps',
            'fignew/results schematic.pdf',
            'fignew/results schematic 2.jpg'
        ])
            
        
        lpp = helpers.MockLPP()
        lpp.install_fix( figures.CopyAndRenameFigs(
            start_fig_counter=9,
            fig_rename='fig/{fig_counter}/{orig_fig_basename}{fig_ext}',
            
        ) )

        self.assertEqual(
            lpp.execute(r"""
                \includegraphics[width=\textwidth]{fig/intro}
                \includegraphics[width=\textwidth]{my_diagram.jpg}
                \includegraphics{fignew/results schematic}
                \includegraphics{v088338-1993.out}
            """),
            r"""
                \includegraphics[width=\textwidth]{fig/9/intro.png}
                \includegraphics[width=\textwidth]{fig/10/my_diagram.jpg}
                \includegraphics{fig/11/results schematic.pdf}
                \includegraphics{fig/12/v088338-1993.out.eps}
            """
        )

        self.assertEqual(
            lpp.copied_files,
            [
                ('fig/intro.png', '/TESTOUT/fig/9/intro.png'),
                ('my_diagram.jpg', '/TESTOUT/fig/10/my_diagram.jpg'),
                ('fignew/results schematic.pdf', '/TESTOUT/fig/11/results schematic.pdf'),
                ('v088338-1993.out.eps', '/TESTOUT/fig/12/v088338-1993.out.eps'),
            ]
        )



if __name__ == '__main__':
    helpers.test_main()
