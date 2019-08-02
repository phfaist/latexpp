import re
import os
import os.path
import logging

logger = logging.getLogger(__name__)

from latexpp.fixes import BaseFix


class CopyFiles(BaseFix):
    """
    Copies the given files to the output directory.  Use this for dependencies
    that aren't obvious, like a custom LaTeX class.

    For packages, you can use
    :py:class:`latexpp.fixes.usepackage.CopyLocalPkgs`.  For figures, consider
    using :py:class:`latexpp.fixes.figures.CopyAndRenameFigs`.

    Arguments:
    
    - `files`: a list of files to include in the output directory.  The files
      are not renamed.

    .. warning::

       Subdirectories are not honored.  TODO: fix this.
    """

    def __init__(self, files=[]):
        self.files = files

    def initialize(self, lpp, **kwargs):

        for fn in self.files:
            lpp.copy_file(fn)

