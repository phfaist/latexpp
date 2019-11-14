
import unittest

import helpers

from latexpp.fixes import comments

class TestRemoveComments(unittest.TestCase):

    def test_simple_1(self):
        
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

Also a \itshape%
some italic text."""
        )

    def test_simple_1b(self):
        
        # test that collapsing comments do respect the post-space of the last
        # comment

        latex = r"""Line with % comment here

\begin{stuff}
    % line comment on its own
  % and a second line
  stuff...
\end{stuff}

Also a \itshape% comment after a macro
% and also a second line
some italic text."""

        lpp = helpers.MockLPP()
        lpp.install_fix( comments.RemoveComments() )

        self.assertEqual(
            lpp.execute(latex),
            r"""Line with %

\begin{stuff}
    %
  stuff...
\end{stuff}

Also a \itshape%
some italic text."""
        )

    def test_leave_percent(self):
        
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

    def test_no_collapse(self):
        
        latex = r"""Line with % comment here

\begin{stuff}
    % line comment on its own
  % and a second line
  stuff...
\end{stuff}

Also a \itshape% comment after a macro
% and also a second line
some italic text."""

        lpp = helpers.MockLPP()
        lpp.install_fix( comments.RemoveComments(collapse=False) )

        self.assertEqual(
            lpp.execute(latex),
            r"""Line with %

\begin{stuff}
    %
  %
  stuff...
\end{stuff}

Also a \itshape%
%
some italic text."""
        )





if __name__ == '__main__':
    helpers.test_main()
