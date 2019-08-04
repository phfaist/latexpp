
import unittest

import helpers

from latexpp.fixes import comments

class TestRemoveComments(unittest.TestCase):

    def test_simple(self):
        
        latex = r"""Line with % comment here

% line comment on its own
% and a second line

Also a \itshape% comment after a macro
% and also a second line
some italic text."""

        lpp = helpers.MockLPP()
        lpp.install_fix( comments.RemoveComments() )

        self.assertEqual(
            lpp.execute(latex),
            r"""Line with %

%
%

Also a \itshape%
%
some italic text."""
        )

    def test_simple_2(self):
        
        latex = r"""Line with % comment here
some text.
% line comment on its own
% and a second line

Also a \itshape% comment after a macro
% and also a second line
some italic text."""

        lpp = helpers.MockLPP()
        lpp.install_fix( comments.RemoveComments(leave_percent=False) )

        self.assertEqual(
            lpp.execute(latex),
            r"""Line with some text.


Also a \itshape some italic text."""
        )





if __name__ == '__main__':
    helpers.test_main()
