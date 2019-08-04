
import unittest

import helpers

from latexpp.fixes import deps

class TestCopyFiles(unittest.TestCase):

    def test_simple(self):
        
        lpp = helpers.MockLPP()
        lpp.install_fix( deps.CopyFiles(['a.sty', 'b.clo', 'fig/myfig.jpg']) )

        lpp.execute("")

        self.assertEqual(
            lpp.copied_files,
            [
                ('a.sty', '/TESTOUT/a.sty'),
                ('b.clo', '/TESTOUT/b.clo'),
                ('fig/myfig.jpg', '/TESTOUT/fig/myfig.jpg'),
            ]
        )



if __name__ == '__main__':
    helpers.test_main()
